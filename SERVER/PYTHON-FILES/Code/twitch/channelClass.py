import os
import traceback
from datetime import datetime
from json import dumps
from random import choice, randint
from string import ascii_uppercase
from threading import Thread
from time import sleep

from websocket import create_connection

from . import find_client_id
from ..log import verbose, reply, TwitchSent, warning, stopped, crash_warning, info
from ..template.template_channelClass import ChannelInfo_template
from ..utils.other import try_get, get_format_from_data
from ..utils.parser import parse_json
from ..utils.windowsNotification import show_windows_toast_notification
from ..encoder import Encoder
from ..utils.web import download_website, download_json, download_m3u8_formats

try:
    from urllib.parse import urlencode
except ImportError:
    urlencode = None
    stopped("Unsupported version of Python. You need Version 3 :<")


class ChannelInfoTwitch(ChannelInfo_template):
    _API_START_PATH = 'https://api.twitch.tv'
    _USHER_START_PATH = 'https://usher.ttvnw.net'

    platform = 'TWITCH'

    # VIDEO DATA
    broadcast_id = None
    live_streaming = None

    # RECORDING.
    EncoderClass = Encoder()

    # HOLDING TWITCH'S WEBSOCKET
    ws = None

    def __init__(self, channel_name, SharedVariables=None, cachedDataHandler=None, queue_holder=None):
        # TWITCH ONLY GOES BY CHANNEL NAME. NOT CHANNEL ID.
        self.channel_name = channel_name
        super().__init__(None, SharedVariables, cachedDataHandler, queue_holder)

    def __callAPI__(self, path):
        url_referer = 'https://www.twitch.tv/{0}'.format(self.channel_name)
        from . import client_id
        website_dict = download_json('{0}/{1}'.format(self._API_START_PATH, path), headers={
            'DNT': 1, 'Referer': url_referer, 'Sec-Fetch-Mode': 'cors', 'Client-ID': client_id})
        return website_dict

    def loadVideoData(self):
        website_string = download_website('https://www.twitch.tv/{0}'.format(self.channel_name))
        if website_string is None:
            return [False, "Failed getting Twitch Data from the internet! "
                           "This means there is no good internet available!"]
        if website_string == 404:
            return [False, "Failed getting Twitch Data! \"{0}\" doesn't exist as a channel name!".format(
                self.channel_name)]
        url_referer = 'https://www.twitch.tv/{0}'.format(self.channel_name)

        verbose("Getting Client ID. [TWITCH]")
        ok, reply_ = find_client_id(website_string, url_referer)
        if not ok:
            return [False, reply_]
        verbose('Getting Channel ID. [TWITCH]')
        website_dict = self.__callAPI__('kraken/channels/{0}'.format(
            self.channel_name))
        self.channel_id = str(try_get(website_dict, lambda x: x['_id'], int))
        # TURNING INTO STR MAKES FLASK NOT STOP WORKING
        if not self.channel_id:
            return [False, "Unable to find Channel ID."]

        return [True, "OK"]

    def channel_thread(self):
        try:
            def createConnection():
                from .. import UserAgent
                headers = {
                    'Origin': 'http://www.twitch.tv',
                    'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
                    'User-Agent': UserAgent}

                ws = create_connection("wss://pubsub-edge.twitch.tv/v1", headers=headers)
                while not ws.connected:
                    pass
                sleep(2)
                return ws

            def send(object_):
                # DUMPS IS JSON.DUMPS. OOF
                dump_ = dumps(object_)
                try:
                    self.ws.send(dump_)
                except Exception:
                    pass
                TwitchSent(dump_)

            def pingThread():
                while self.ws.connected:
                    send({'type': 'PING'})
                    sleep(240)

            def registerListen(topic_name):
                send({'data': {'topics': [topic_name]}, 'nonce': ''.join(choice(ascii_uppercase) for i in range(30)),
                      'type': 'LISTEN'})

            def firstCheckLive():
                formats = self.getTwitchStreamInfo()
                if formats == 404:
                    # TRANSCODE DOESNT EXIST. THAT IS NORMAL. SO NOT LIVE
                    return False
                if type(formats) is dict:
                    verbose('Getting Broadcast ID. [TWITCH]')
                    streams = self.__callAPI__('kraken/streams/{0}'.format(self.channel_name))
                    if type(streams) is int:
                        warning("Twitch replied: {0}".format(str(streams)))
                    if streams:
                        self.broadcast_id = try_get(streams, lambda x: x['stream']['_id'], int)
                    self.StreamInfo = formats
                    return True
                else:
                    if type(formats) is int:
                        warning('Twitch replied Status Code: {0}'.format(str(formats)))
                    else:
                        warning("Formats returned: {0}".format(str(formats)))
                return False

            def start_recording(StreamInfo):
                self.recording_status = "Starting Recording."

                filename = self.create_filename(self.broadcast_id)
                self.video_location = os.path.join("RecordedStreams", '{0}.mp4'.format(filename))

                ok = self.EncoderClass.start_recording(StreamInfo['HLSStreamURL'], self.video_location)
                if not ok:
                    self.recording_status = "Failed To Start Recording."
                    show_windows_toast_notification("Live Recording Notifications",
                                                    "Failed to start record for {0}".format(self.channel_name))
                if ok:
                    self.start_date = datetime.now()

                    self.recording_status = "Recording."

                    show_windows_toast_notification("Live Recording Notifications",
                                                    "{0} is live and is now recording. \nRecording at {1}".format(
                                                        self.channel_name, StreamInfo['stream_resolution']))

            def stop_recording():
                self.EncoderClass.stop_recording()

            self.ws = createConnection()

            x = Thread(target=pingThread)
            x.start()

            # REGISTER TO LISTEN FOR STREAM CHANGES.
            registerListen('stream-change-by-channel.{0}'.format(self.channel_id))

            self.live_streaming = firstCheckLive()
            if self.live_streaming:
                start_recording(self.StreamInfo)

            while True:
                if self.ws.connected:
                    result = self.ws.recv()
                    json = parse_json(result)
                    if json:
                        reply('FROM TWITCH -> {0}'.format(json))

                        message_type = try_get(json, lambda x: x['type'], str)
                        message_data_json = parse_json(try_get(json, lambda x: x['data']['message'], str))
                        # TODO ONLY HERE FOR TESTING.
                        if message_type:
                            if "MESSAGE" in message_type:
                                data_message_type = try_get(message_data_json, lambda x: x['type'])
                                if data_message_type:
                                    if 'stream_up' in data_message_type:
                                        self.live_streaming = True
                                        self.broadcast_id = try_get(
                                            message_data_json, lambda x: x['data']['broadcast_id'])
                                        start_recording(self.getTwitchStreamInfo())
                                    if 'stream_down' in data_message_type:
                                        self.live_streaming = False
                                        stop_recording()
                            if "RESPONSE" in message_type:
                                pass
        except Exception:
            self.crashed_traceback = traceback.format_exc()
            crash_warning("{0}:\n{1}".format(self.channel_name, traceback.format_exc()))

    def getTwitchStreamInfo(self):
        access_token = self.__callAPI__('api/channels/{0}/access_token?{1}&oauth_token'.format(
            self.channel_name, urlencode({'need_https': 'true', 'platform': 'web',
                                          'player_backend': 'mediaplayer', 'player_type': 'site'})))
        if access_token:
            arguments = {'allow_source': 'true', 'baking_bread': 'true',
                         'baking_brownies': 'false', 'baking_brownies_timeout': 1050,
                         'fast_bread': 'true',
                         'p': randint(1000000, 10000000), 'player_backend': 'mediaplayer',
                         'playlist_include_framerate': 'true', 'reassignments_supported': 'true',
                         'sig': access_token['sig'].encode('utf-8'),
                         'token': access_token['token'].encode('utf-8'),
                         'supported_codecs': 'avc1', 'cdm': 'wv'}
            manifest_url = '{0}/api/channel/hls/{1}.m3u8?{2}'.format(self._USHER_START_PATH, self.channel_name,
                                                                     urlencode(arguments))
            formats = download_m3u8_formats(manifest_url)
            if type(formats) is list:
                f = get_format_from_data(formats, self.cachedDataHandler.getValue('recordingResolution'))
                return {
                    'stream_resolution': '{0}x{1}'.format(str(f['width']), str(f['height'])),
                    'HLSManifestURL': manifest_url,
                    'HLSStreamURL': f['url'],
                    'title': 'WORKING PROGRESS',
                    'description': 'WORKING PROGRESS',
                }
            return formats
        warning("Unable to get access token.")
        return None

    def create_filename(self, broadcast_id):
        now = datetime.now()
        # Used to handle lots of names by creating new names and add numbers!
        amount = 1
        while True:
            if amount is 1:
                file_name = "{3} - '{4}' - {0}-{1}-{2}".format(now.month, now.day, now.year, self.channel_name,
                                                               broadcast_id)
            else:
                file_name = "{3} - '{4}' - {0}-{1}-{2}_{5}".format(now.month, now.day, now.year, self.channel_name,
                                                                   broadcast_id,
                                                                   amount)
            path = os.path.join("RecordedStreams", '{0}.mp4'.format(file_name))
            if not os.path.isfile(path):
                verbose("Found Good Filename.")
                return file_name
            amount += 1

    # USED FOR THE CLOSE EVENT AND STUFF.
    def stop_recording(self):
        if self.EncoderClass:
            self.EncoderClass.stop_recording()
        self.stop_heartbeat = True
        if self.ws is not None:
            if self.ws.connected:
                self.ws.close()
