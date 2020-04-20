import re
from json import dumps
from random import choice, randint
from string import ascii_uppercase
from time import sleep

from websocket import create_connection

from Code.utils.other import try_get
from Code.utils.web import UserAgent
from Code.log import TwitchSent, warning
from Code.utils.parser import parse_json


class TwitchPubSubEdgeWebSocket:
    """
    Twitch's pubsub-edge websocket: wss://pubsub-edge.twitch.tv/v1

    """

    @staticmethod
    def create_connection():
        headers = {
            'Origin': 'http://www.twitch.tv',
            'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
            'Upgrade': 'websocket',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'User-Agent': UserAgent}

        ws = create_connection("wss://pubsub-edge.twitch.tv/v1", headers=headers)
        while not ws.connected:
            pass
        sleep(2)
        return ws

    def __init__(self):
        self.ws = self.create_connection()

    def send(self, object_):
        # DUMPS IS JSON.DUMPS. OOF
        try:
            dump_ = dumps(object_)
            self.ws.send(dump_)
            TwitchSent(dump_)
        except Exception:
            pass

    def ping(self):
        self.send({'type': 'PING'})

    def registerListen(self, topic_name):
        self.send({
            'data': {'topics': [topic_name]},
            'nonce': ''.join(choice(ascii_uppercase) for i in range(30)),
            'type': 'LISTEN'
        })

    def recv(self):
        try:
            result = self.ws.recv()
        except TimeoutError:
            warning("Lost connection of Twitch Websocket! [CONNECTION TIMED OUT]")
            sleep(1)
            self.create_connection()
            return None
        except Exception:
            return None
        json = parse_json(result)
        return json


def find_client_id(website_string):
    client_id = try_get(re.findall(r'\"Client-ID\":\"(.+?)\".', website_string), lambda x: x[0], str)
    if client_id is None:
        return [False, "Unable to find client id."]
    return [True, client_id]
