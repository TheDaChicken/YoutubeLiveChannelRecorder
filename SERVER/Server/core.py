from datetime import datetime
from logging import LogRecord, Formatter
from multiprocessing import Process, Manager
from multiprocessing.managers import BaseManager
from multiprocessing import Queue
from threading import Thread
from time import sleep
from typing import List, Union, Type

from Server.channels.common import Channel
from Server.channels.youtube import YouTubeChannel
from Server.extra import GlobalHandler
from Server.logger import get_logger, initialize_worker_logger, LoggerListener, LoggingBackend
from Server.utils.webserver import SessionHandler


class ProcessHandler:
    channels_dict = {}

    start_time = None

    def __init__(self):
        self.register('GlobalHandler', GlobalHandler)
        self.register('Queue', Queue)

        self.platforms = []
        self.registered_channel_classes = {}

        # REGISTER CHANNELS
        self.register_channel(YouTubeChannel)

        # Channel Class
        self.baseManagerChannelInfo = BaseManager()
        self.baseManagerChannelInfo.start()

        # GlobalHandler
        self.baseManagerNormalHandlers = BaseManager()
        self.baseManagerNormalHandlers.start()
        self.queue = self.baseManagerNormalHandlers.Queue(-1)
        self.listLogs = None
        self.sessions = SessionHandler()
        self.loggingBackend = LoggingBackend()  # type: LoggingBackend
        self.globalHandler = self.baseManagerNormalHandlers.GlobalHandler()  # type: GlobalHandler

    @staticmethod
    def register(register_name, channel_object):
        BaseManager.register(register_name, channel_object)

    def register_channel(self, channel_class: Type[Channel]):
        platform_name = channel_class.platform
        self.platforms.append(platform_name.upper())
        self.registered_channel_classes[platform_name.upper()] = channel_class
        self.register('Channel{0}'.format(platform_name.upper()), channel_class)
        self.register('Channel{0}-DICT'.format(platform_name.upper()), channel_class.fromDICT)

    def run_channel(self, channel_identifier: str, platform='YOUTUBE',
                    startup=False, **kwargs) -> List[Union[bool, str]]:
        """ Runs the channel with the channel_identifier
        """
        channel_holder_class = self.create_proxy(channel_identifier, platform)
        if not channel_holder_class:
            return [False, ""]
        ok_bool, error_message = channel_holder_class.load_channel_data()
        if not ok_bool:
            if startup:
                self.channels_dict.update({
                    channel_identifier: {
                        'class': channel_holder_class,
                        'error': error_message,
                        'thread_class': None}
                })
            return [False, error_message]
        channel_holder_class.register_close_event()
        channel_thread = Process(
            target=channel_holder_class.channel_thread, name="{0} - Channel Process".format(
                channel_holder_class.get_information().get_channel_name()))
        channel_thread.start()
        self.channels_dict.update({
            channel_identifier: {
                'class': channel_holder_class,
                'thread_class': channel_thread}
        })
        return [True, "OK"]

    def run_channel_obj(self, channel_holder_class: Channel, platform='YOUTUBE',
                        startup=False):
        if not channel_holder_class:
            return [False, ""]
        channel_identifier = channel_holder_class.get_information().get_channel_identifier()
        ok_bool, error_message = channel_holder_class.load_channel_data()
        if not ok_bool:
            if startup:
                self.channels_dict.update({
                    channel_identifier: {
                        'class': channel_holder_class,
                        'error': error_message,
                        'thread_class': None}
                })
            return [False, error_message]
        channel_holder_class.register_close_event()
        channel_thread = Process(
            target=channel_holder_class.channel_thread, name="{0} - Channel Process".format(
                channel_holder_class.get_information().get_channel_name()))
        channel_thread.start()
        self.channels_dict.update({
            channel_identifier: {
                'class': channel_holder_class,
                'thread_class': channel_thread}
        })
        return [True, "OK"]

    def create_proxy(self, channel_identifier: str, platform='YOUTUBE') -> Channel:
        if not isinstance(channel_identifier, str):
            raise ValueError("channel_identifier is not a str!")
        result = hasattr(self.baseManagerChannelInfo, 'Channel{0}'.format(platform.upper()))
        if result is False:
            raise ValueError("No Platform Registered: {0}.".format(platform))
        channel_class = getattr(self.baseManagerChannelInfo, 'Channel{0}'.format(platform.upper()))(
            channel_identifier, self.globalHandler, self.queue)
        return channel_class

    def create_proxy_dict(self, values: dict, platform='YOUTUBE') -> Channel:
        result = hasattr(self.baseManagerChannelInfo, 'Channel{0}-DICT'.format(platform.upper()))
        if result is False:
            raise ValueError("No Platform Registered: {0}.".format(platform))
        channel_class = getattr(self.baseManagerChannelInfo, 'Channel{0}-DICT'.format(platform.upper()))(
            values, self.globalHandler, self.queue)
        return channel_class

    def create_safe_class(self, channel_identifier: str, platform="YOUTUBE") -> Channel:
        channel_obj = self.registered_channel_classes.get(platform.upper())
        if channel_obj is None:
            raise ValueError("No Platform Registered: {0}.".format(platform))
        return channel_obj(channel_identifier, self.globalHandler, self.queue)

    def load_channels(self):
        channels = self.globalHandler.get_cache_yml().get_cache(). \
                       get('Saved_Channels') or {**dict.fromkeys(self.platforms, {})}
        for platform in channels:
            channel_list = channels.get(platform)
            for channel_id in channel_list:
                ok, error_message = self.run_channel(channel_id, startup=True,
                                                     platform=platform)
                if not ok:
                    get_logger().warning(error_message)

    def search_channel(self, query: str, platform="YOUTUBE"):
        channel_obj = self.registered_channel_classes.get(platform.upper())
        if channel_obj is None:
            raise ValueError("No Platform Registered: {0}.".format(platform))
        if not hasattr(channel_obj, "search_channel"):
            raise ValueError("Platform doesn't support searching.")
        return channel_obj.search_channel(self.globalHandler, query)

    def server_started(self, port: int):
        get_logger().info("Starting server. Hosted on port: {0}!".format(port))
        self.start_time = datetime.now()

    def get_server_uptime(self):
        return self.start_time

    def set_log_level(self, log_level):
        """Sets Default Log Level
        """
        return self.globalHandler.set_log_level(log_level)

    def initialize_back_logger(self):
        def handle():
            formatter = Formatter("[%(levelname)s] (%(name)s) %(message)s")
            while True:
                if len(self.listLogs) > 0:
                    record = self.listLogs.pop(0)  # type: LogRecord
                    self.loggingBackend.broadcast(formatter.format(record))
                else:
                    sleep(0.1)

        self.listLogs = Manager().list()  # type: list
        thread = Thread(target=handle, name="Back Logger")
        thread.daemon = True
        thread.start()

    def initialize_logger_listener(self):
        # LOGGER LISTENER
        logger = LoggerListener(self.queue, self.listLogs)
        logger.start()

    def initialize_logger(self, name=None):
        return initialize_worker_logger(self.queue, self.globalHandler.get_log_level(), name=name)

    def get_channel_obj(self, channel_identifier) -> Channel:
        classes = self.channels_dict.get(channel_identifier)  # type: dict
        if classes is None:
            raise ValueError("Cannot find {0} channel object".format(channel_identifier))
        return classes.get("class")

    def get_channels(self) -> list:
        return list(map(lambda x: self.channels_dict[x].get("class"), self.channels_dict))
