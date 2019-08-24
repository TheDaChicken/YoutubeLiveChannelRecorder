import traceback
from json import dumps
from random import choice, randint
from string import ascii_uppercase
from threading import Thread
from time import sleep

from websocket import create_connection

from . import find_client_id
from ..log import verbose, reply, TwitchSent, warning, stopped, crash_warning
from ..template.template_channelClass import ChannelInfo_template
from ..utils.other import try_get, get_format_from_data
from ..utils.parser import parse_json
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

    def start_heartbeat_loop(self):
        try:
            def createConnection():
                from .. import UserAgent
                headers = {
                    'Origin': 'http://www.twitch.tv',
                    'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
                    'User-Agent': UserAgent}

                ws_ = create_connection("wss://pubsub-edge.twitch.tv/v1", headers=headers)
                while not ws_.connected:
                    pass
                sleep(2)
                return ws_

            def send(object_):
                # DUMPS IS JSON.DUMPS. OOF
                dump_ = dumps(object_)
                ws.send(dump_)
                TwitchSent(dump_)

            def pingThread():
                while ws.connected:
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
                    self.StreamInfo = formats
                    return True
                else:
                    if type(formats) is int:
                        warning('Twitch replied Status Code: {0}'.format(str(formats)))
                    else:
                        warning("Formats returned: {0}".format(str(formats)))
                return False

            ws = createConnection()

            x = Thread(target=pingThread)
            x.start()

            # REGISTER TO LISTEN FOR STREAM CHANGES.
            registerListen('stream-change-by-channel.{0}'.format(self.channel_id))

            self.live_streaming = firstCheckLive()
            if self.live_streaming:
                pass

            while True:
                if ws.connected:
                    result = ws.recv()
                    json = parse_json(result)

                    reply('FROM TWITCH -> {0}'.format(json))

                    message_type = try_get(json, lambda x: x['type'], str)
                    # TODO ONLY HERE FOR TESTING.
                    with open("test.txt", "a", encoding='utf-8') as myfile:
                        myfile.write("{0}\n".format(str(json)))
                    if message_type:
                        if "MESSAGE" in message_type:
                            data_message_type = try_get(json, lambda x: x['data']['message']['type'])
                            if 'stream_up' in data_message_type:
                                myfile.write("oh no not live\n")
                                self.live_streaming = True
                            if 'stream_down' in data_message_type:
                                myfile.write("oh no not live\n")
                                self.live_streaming = False
                        if "RESPONSE" in message_type:
                            pass
                    myfile.close()
                elif not ws.connected:
                    ws = createConnection()
                    if not ws.connected:
                        warning("Unable to connect to Twitch WEBSOCKET.")
        except Exception:
            self.crashed_traceback = traceback.format_exc()
            crash_warning("{0}:\n{1}".format(self.channel_name, traceback.format_exc()))

    def getTwitchStreamInfo(self):
        access_token = self.__callAPI__('api/channels/{0}/access_token?{1}&oauth_token'.format(
            self.channel_name, urlencode({'need_https': 'true', 'platform': 'web',
                                          'player_backend': 'mediaplayer', 'player_type': 'site'})))
        if access_token:
            arguments = {'allow_source': 'true', 'baking_bread': 'true',
                         'baking_brownies': 'true', 'baking_brownies_timeout': 1050,
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
                f = get_format_from_data(formats, self.cachedDataHandler.getValue('recordingHeight'))
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
