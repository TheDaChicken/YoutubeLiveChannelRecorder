import logging
import tempfile
from logging.handlers import QueueHandler
from multiprocessing import Process
from multiprocessing import Queue
from os import stat
from threading import Thread

import gevent
from colorlog import ColoredFormatter, StreamHandler

ENCODER = 5
logging.addLevelName(ENCODER, 'ENCODER')


def encoder(self, message, *args, **kws):
    self.log(ENCODER, message, *args, **kws)


logging.Logger.encoder = encoder


def initialize_logger(name=None, string_io=None):
    # %(log_color)s[%(levelname)s] (%(name)s) %(white)s%(message)s%(reset)s
    handler = StreamHandler()
    color_formatter = ColoredFormatter(
        '%(log_color)s[%(levelname)s] (%(name)s) %(reset)s%(message)s%(reset)s',
        log_colors={
            'INFO': 'bold_green',
            'WARNING': 'bold_cyan',
            'ERROR': 'bold_red',
            'CRITICAL': 'bold_yellow',
            'DEBUG': 'bold_red',
            "ENCODER": "bold_green",
        })
    handler.setFormatter(color_formatter)

    logger = get_logger(name)
    logger.addHandler(handler)
    if string_io:
        ch = logging.StreamHandler(string_io)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger


class LoggingBackend:
    temp = None

    def __init__(self):
        self.create_new_temp()  # creates new temp to hold some of the logs
        self.clients = list()

    def register(self, client):
        self.clients.append(client)

    def load_temp(self, client):
        self.temp.seek(0)
        for message in self.temp.readlines():
            message = message.strip()
            self.send(client, message.decode('utf-8'))

    def send(self, client, data: str):
        """Send given data to the registered client.
        Automatically discards invalid connections."""
        try:
            client.send(data)
        except Exception:
            self.clients.remove(client)

    def create_new_temp(self):
        if self.temp:
            self.temp.close()  # deletes
        self.temp = tempfile.TemporaryFile()  # holds like some of the logger

    def broadcast(self, message: str):
        self.temp.write(("%s\n" % message).encode('utf-8'))
        if self.temp.truncate() > 1000000:
            get_logger().critical("Clearing Temp File with Logs.")
            self.create_new_temp()
        for client in self.clients:
            Thread(target=self.send, args=[client, message]).start()


class LoggerListener:
    def __init__(self, queue: Queue, listRecords: list):
        self.queue = queue
        self.listRecords = listRecords

    @staticmethod
    def listener_process(queue: Queue, listRecords: list):
        initialize_logger()
        while True:
            try:
                record = queue.get(timeout=1)
            except Exception:
                pass
            except KeyboardInterrupt:
                break
            else:
                logger = get_logger(record.name)
                logger.handle(record)  # No level or filter logic applied - just do it!
                if listRecords is not None:
                    listRecords.append(record)  # moves to the main thread for websocket

    def start(self):
        listener = Process(
            target=self.listener_process, args=(self.queue, self.listRecords,), name="Logger Listener")
        listener.start()


def initialize_worker_logger(queue, log_level=None, name=None):
    h = QueueHandler(queue)
    root = get_logger(name)
    root.addHandler(h)
    root.setLevel(log_level)
    return root


def is_logger_initalized(name=None):
    logger = get_logger(name)
    if len(logger.handlers) == 0:
        return False
    return True


def get_logger(name=None):
    return logging.getLogger(name)
