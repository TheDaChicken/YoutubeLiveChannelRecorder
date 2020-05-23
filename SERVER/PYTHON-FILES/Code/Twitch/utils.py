import re
import sys
import traceback
from json import dumps
from random import choice, randint
from string import ascii_uppercase
from threading import Thread
from time import sleep

from websocket import create_connection, WebSocketApp, enableTrace, _logging

from Code.utils.other import try_get
from Code.utils.web import UserAgent
from Code.log import TwitchSent, warning
from Code.utils.parser import parse_json

class CustomWebSocketApp(WebSocketApp):
    def _callback(self, callback, *args):
        if callback:
            try:
                callback(self, *args)

            except Exception as e:
                _logging.error("error from callback {}: {}".format(callback, e))
                if _logging.isEnabledForDebug():
                    _, _, tb = sys.exc_info()
                    traceback.print_tb(tb)


class TwitchPubSubEdgeWebSocket:
    """
    Twitch's pubsub-edge websocket: wss://pubsub-edge.twitch.tv/v1

    """

    registers = None
    on_message_ = None
    ws = None

    def __init__(self, registers: list, on_message_):
        self.registers = registers
        self.on_message_ = on_message_

    def on_message(self, ws, message):
        self.on_message_(parse_json(message))

    def on_error(self, ws, error):
        # print(error)
        pass

    def terminate(self):
        self.ws.close()

    def on_close(self, ws: CustomWebSocketApp):
        warning("[TWITCH] Websocket Connection Closed..")

    def on_open(self, ws):
        def run(*args):
            while True:
                self.ping(ws)
                sleep(240)

        for reg in self.registers:
            self.registerListen(ws, reg)
        thread = Thread(target=run)
        thread.daemon = True
        thread.start()

    def create_forever_connection(self):
        headers = {
            'Origin': 'http://www.twitch.tv',
            'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
            'Upgrade': 'websocket',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'User-Agent': UserAgent}
        # enableTrace(True)
        self.ws = CustomWebSocketApp("wss://pubsub-edge.twitch.tv/v1",
                                on_message=self.on_message,
                                on_error=self.on_error,
                                on_close=self.on_close, header=headers, on_open=self.on_open)
        # ws.on_open = self.on_open
        while True:
            self.ws.run_forever()
            warning("[TWITCH] Reconnecting Websocket in 5 seconds....")
            sleep(5)

    def send(self, ws, object_: dict):
        # DUMPS IS JSON.DUMPS. OOF
        try:
            dump_ = dumps(object_)
            ws.send(dump_)
            TwitchSent(dump_)
        except Exception:
            pass

    def ping(self, ws):
        self.send(ws, {'type': 'PING'})

    def registerListen(self, ws, topic_name):
        self.send(ws, {
            'data': {'topics': [topic_name]},
            'nonce': ''.join(choice(ascii_uppercase) for i in range(30)),
            'type': 'LISTEN'
        })


def find_client_id(website_string):
    client_id = try_get(re.findall(r'\"Client-ID\":\"(.+?)\".', website_string), lambda x: x[0], str)
    if client_id is None:
        return [False, "Unable to find client id."]
    return [True, client_id]
