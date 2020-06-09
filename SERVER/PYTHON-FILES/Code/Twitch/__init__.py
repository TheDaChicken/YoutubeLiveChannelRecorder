# from Code import GlobalVariables
import traceback
from random import randint
from typing import Union, List
from urllib.parse import urlencode

from Code.log import warning, verbose, crash_warning, reply
from Code.utils.other import try_get, get_format_from_data
from Code.Templates.ChannelObject import TemplateChannel
from Code.utils.web import download_website
from Code.utils.parser import parse_json
from Code.Twitch.utils import TwitchPubSubEdgeWebSocket, find_client_id
from Code.utils.m3u8 import HLS


class ChannelObject(TemplateChannel):
    viewers = None
    TwitchWebSocket = None
    platform_name = "TWITCH"
    channel_id = None
    broadcast_id = None
    video_id = "UNKNOWN"

    stop_websockets = None
    access_token = None

    _API_START_PATH = 'https://api.twitch.tv'
    _USHER_START_PATH = 'https://usher.ttvnw.net'

    def __init__(self, channel_name, SettingDict, SharedCookieDict=None, cachedDataHandler=None,
                 queue_holder=None, globalVariables=None):
        """

        :type channel_name: str
        :type cachedDataHandler: CacheDataHandler
        :type SharedCookieDict: dict
        :type globalVariables: GlobalVariables
        """
        self.channel_name = channel_name
        super().__init__(channel_name, SettingDict, SharedCookieDict, cachedDataHandler, queue_holder, globalVariables)

    def __callAPI__(self, path):
        url_referer = 'https://www.twitch.tv/{0}'.format(self.channel_name)
        download_object = download_website('{0}/{1}'.format(self._API_START_PATH, path), headers={
            'DNT': '1', 'Referer': url_referer, 'Sec-Fetch-Mode': 'cors',
            'Client-ID': self.globalVariables.get("client_id")}, CookieDict=self.sharedCookieDict)
        return download_object.parse_json()

    def close(self):
        super().close()
        if self.TwitchWebSocket is not None:
            self.TwitchWebSocket.terminate()

    def loadVideoData(self):
        url = "https://www.twitch.tv/{0}".format(self.channel_name)
        download_object = download_website(url, CookieDict=self.sharedCookieDict)
        if download_object.status_code == 404:
            return [False, "Failed getting Twitch Data! \"{0}\" doesn't exist as a channel name!".format(
                self.channel_name)]
        if download_object.text is None:
            return [False, "Failed getting Youtube Data from the internet! "
                           "This means there is no good internet available!"]
        if self.globalVariables.get("client_id") is None:
            verbose("Getting Client ID. [TWITCH]")
            okay, client_id = find_client_id(download_object.text)
            if okay is False:
                warning(client_id)
            self.globalVariables.set("client_id", client_id)
        verbose('Getting Channel ID. [TWITCH]')

        self.access_token = self.__callAPI__('api/channels/{0}/access_token?{1}&oauth_token'.format(
            self.channel_name, urlencode({'need_https': 'true', 'platform': 'web',
                                          'player_backend': 'mediaplayer',
                                          'player_type': 'site'})))

        token = parse_json(self.access_token['token'])
        self.channel_id = try_get(token, lambda x: x['channel_id'])

        # website_dict = self.__callAPI__('kraken/channels/{0}'.format(
        #     self.channel_name))
        # self.channel_image = try_get(website_dict, lambda x: x['logo'])
        # self.channel_id = try_get(website_dict, lambda x: x['_id'], int)

        self.live_streaming, hls = self.getTwitchStreamInfo()

        if hls is not None:
            self.StreamFormat = get_format_from_data(
                hls, self.cachedDataHandler.getValue('recordingResolution'))

        if not self.channel_id:
            return [False, "Unable to find Channel ID."]
        return [True, "OK"]

    def getTwitchStreamInfo(self) -> List[Union[bool, HLS]]:
        arguments = {
            'allow_source': 'true',
            'allow_spectre': 'true',
            'p': randint(1000000, 10000000),
            'sig': self.access_token['sig'].encode('utf-8'),
            'supported_codecs': 'avc1',
            'token': self.access_token['token'].encode('utf-8'),
            'cdm': 'wv',
        }
        manifest_url = '{0}/api/channel/hls/{1}.m3u8?{2}'.format(self._USHER_START_PATH, self.channel_name,
                                                                 urlencode(arguments))
        download_object = download_website(manifest_url, CookieDict=self.sharedCookieDict, headers={
            'Accept': 'application/x-mpegURL, application/vnd.apple.mpegurl, application/json, text/plain'
        })
        if download_object.status_code == 404:
            # TRANSCODE DOESNT EXIST. THAT IS NORMAL. SO NOT LIVE
            return [False, None]
        elif download_object.response_headers['Content-Type'] == "application/vnd.apple.mpegurl":
            return [True, download_object.parse_m3u8_formats()]
        print("Unable To Handle Status: {0} For Twitch.".format(download_object.status_code))
        return [False, None]

    def on_message(self, reply_: dict):
        if reply_:
            reply('FROM TWITCH -> {0}'.format(reply_))
            message_type = try_get(reply_, lambda x: x['type'], str) or ''
            message_data = parse_json(try_get(reply_, lambda x: x['data']['message'], str)) or {}
            if "MESSAGE" in message_type:
                data_message_type = try_get(message_data, lambda x: x['type']) or ''
                if 'stream-up' in data_message_type:
                    self.live_streaming = True
                    self.broadcast_id = try_get(message_data, lambda x: x['data']['broadcast_id'], int)
                    self.live_streaming, hls = self.getTwitchStreamInfo()
                    if hls is not None:
                        self.StreamFormat = get_format_from_data(
                            hls, self.cachedDataHandler.getValue('recordingResolution'))
                        self.start_recording(self.StreamFormat)
                if 'stream-down' in data_message_type:
                    self.live_streaming = False
                    self.stop_recording()
                if 'viewcount' in data_message_type:
                    self.viewers = try_get(
                        message_data, lambda x: x['viewers'], int)
            if "RESPONSE" in message_type:
                pass

    def channel_thread(self):
        # enableDVR = arguments.get("enableDVR")

        try:
            if self.live_streaming is True:
                self.start_recording(self.StreamFormat)

            if self.stop_websockets is False:
                exit()

            self.TwitchWebSocket = TwitchPubSubEdgeWebSocket(['video-playback-by-id.{0}'.format(self.channel_id)], self.on_message)
            self.TwitchWebSocket.create_forever_connection()

            # REGISTER FOR VIDEO PLAYBACK MESSAGES
            # self.TwitchWebSocket.registerListen('video-playback-by-id.{0}'.format(self.channel_id))
        except Exception:
            self.crashed_traceback = traceback.format_exc()
            crash_warning("{0}:\n{1}".format(self.channel_name, traceback.format_exc()))


def searchChannels(search, CookieDict, globalVariables):
    """
    :type CookieDict: dict
    :type globalVariables: GlobalVariables
    """
    def formatChannel(channel):
        return {
            'channel_identifier': try_get(channel, lambda x: x['displayName'], str),
            'channel_name': try_get(channel, lambda x: x['displayName'], str),
            'channel_image': try_get(channel, lambda x: x['profileImageURL'], str),
            'follower_count': str(try_get(channel, lambda x: x['followers']['totalCount'], int)),
            'platform': 'TWITCH'
        }

    referer = 'https://www.twitch.tv/search?term={0}&type=channels'.format(search)
    client_id = globalVariables.get("client_id")
    if client_id is None:
        verbose("Getting Client ID. [TWITCH]")
        downloadOBJECT = download_website(referer, CookieDict=CookieDict)
        okay, client_id = find_client_id(downloadOBJECT.text)
        if okay is False:
            warning(client_id)
        globalVariables.set("client_id", client_id)
    data = [{
        "operationName": "SearchResultsPage_SearchResults",
        "variables": {"query":search,"options":{"targets":[{"index":"CHANNEL"}]}},
        "extensions":{"persistedQuery":{"version":1,"sha256Hash":
            '1d3ca64005f07f8e34a33677d119ba8601e7deac745ea127e67b7925535ed735'}}}]  # TODO: reverse the sha265Hash. :p
    downloadOBJECT = download_website('https://gql.twitch.tv/gql', RequestMethod='POST', data=data, headers={'Origin': 'https://www.twitch.tv', 'Referer':
        referer, 'Client-Id': client_id, 'Content-Length': '225'}, CookieDict=CookieDict)
    data = try_get(downloadOBJECT.parse_json(), lambda x: x[0]['data'], dict)
    items = try_get(data, lambda x: x['searchFor']['channels']['items'], list)
    channels = list(map(formatChannel, items))
    return [True, {'channels': channels}]
