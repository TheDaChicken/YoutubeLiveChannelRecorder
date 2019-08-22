import json
from threading import Thread
from time import sleep

from websocket import create_connection

from . import find_client_id
from ..template.template_channelClass import ChannelInfo_template
from ..utils.web import download_website
from ..log import YoutubeReply, info


class ChannelInfoTwitch(ChannelInfo_template):
    platform = 'TWITCH'

    def __init__(self, channel_name, SharedVariables=None, cachedDataHandler=None, queue_holder=None):
        # TWITCH ONLY GOES BY CHANNEL NAME. NOT CHANNEL ID.
        self.channel_name = channel_name
        super().__init__(None, SharedVariables, cachedDataHandler, queue_holder)

    def loadVideoData(self):
        website_string = download_website('https://www.twitch.tv/{0}'.format(self.channel_name))
        if website_string is None:
            return [False, "Failed getting Twitch Data from the internet! "
                           "This means there is no good internet available!"]
        if website_string == 404:
            return [False, "Failed getting Twitch Data! \"{0}\" doesn't exist as a channel name!".format(
                self.channel_id)]
        url_referer = 'https://www.twitch.tv/{0}'.format(self.channel_name)
        # website_dict = download_json('https://static.twitchcdn.net/config/manifest.json?v=1', headers={
        #     'DNT': 1, 'Referer': url_referer, 'Sec-Fetch-Mode': 'cors'})
        self.channel_name = 'asdasfdgkhnckmpretl[n ;'
        ok, reply = find_client_id(website_string, url_referer)
        if not ok:
            return [False, reply]
        # from . import client_id
        return [True, "OK"]

    def start_heartbeat_loop(self):
        def printReply():
            while ws.connected:
                result = ws.recv()
                YoutubeReply(result)

        def pingThread():
            while ws.connected:
                send(json.dumps({'type': 'PING'}))
                sleep(10)

        def send(object_):
            ws.send(object_)
            info(object_)

        ws = create_connection("wss://pubsub-edge.twitch.tv/v1", headers={'Origin': 'http://www.twitch.tv',
                                                                          'Sec-WebSocket-Extensions':
                                                                              'permessage-deflate; client_max_window_bits'})

        x = Thread(target=printReply)
        x.start()

        x = Thread(target=pingThread)
        x.start()