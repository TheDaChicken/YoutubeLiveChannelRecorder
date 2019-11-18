from multiprocessing import Process
from multiprocessing.managers import BaseManager

from Code.utils.web import build_cookies
from Code.YouTube import ChannelObject as ChannelYouTube
from Code.Twitch import ChannelObject as ChannelTwitch
from Code.dataHandler import CacheDataHandler
from Code.log import warning
from Code.YouTubeAPI.uploadQueue import QueueHandler, uploadQueue


class ThreadHandler:
    channels_dict = {}

    debug_mode = False
    serverPort = 31311
    enable_ffmpeg_logs = False

    def __init__(self):
        # Create Shared Variables
        BaseManager.register('CacheDataHandler', CacheDataHandler)
        BaseManager.register('ChannelYouTube', ChannelYouTube)
        BaseManager.register("ChannelTwitch", ChannelTwitch)
        BaseManager.register("Dict", dict)
        BaseManager.register("QueueHandler", QueueHandler)

        # Channel Class
        self.baseManagerChannelInfo = BaseManager()
        self.baseManagerChannelInfo.start()

        # Data Handler
        self.baseManagerDataHandlers = BaseManager()
        self.baseManagerDataHandlers.start()
        self.cachedDataHandler = self.baseManagerDataHandlers.CacheDataHandler()

        # Global Queue Holder.
        self.queue_holder = self.baseManagerDataHandlers.QueueHandler()

        # Cookies
        self.baseManagerCookieDictHolder = BaseManager()
        self.baseManagerCookieDictHolder.start()
        cookieHandler = build_cookies()
        cookieHandler.load()
        cookies_ = cookieHandler.get_cookie_list()  # type: dict
        self.shared_cookieDictHolder = self.baseManagerCookieDictHolder.Dict(cookies_)  # type: dict

    def run_channel(self, channel_identifier, platform='YOUTUBE', startup=False):
        if 'YOUTUBE' in platform:
            channel_holder_class = self.baseManagerChannelInfo.ChannelYouTube(
                channel_identifier, {'debug_mode': self.debug_mode, 'ffmpeg_logs': self.enable_ffmpeg_logs},
                self.shared_cookieDictHolder, self.cachedDataHandler)
        if 'TWITCH' in platform:
            channel_holder_class = self.baseManagerChannelInfo.ChannelTwitch(
                channel_identifier, {'debug_mode': self.debug_mode, 'ffmpeg_logs': self.enable_ffmpeg_logs},
                self.shared_cookieDictHolder, self.cachedDataHandler)
        if channel_holder_class:
            ok_bool, error_message = channel_holder_class.loadVideoData()
            if ok_bool:
                channel_holder_class.registerCloseEvent()
                channel_name = channel_holder_class.get("channel_name")
                check_streaming_channel_thread = Process(target=channel_holder_class.channel_thread,
                                                         name="{0} - Channel Process".format(channel_name))
                check_streaming_channel_thread.start()
                self.channels_dict.update({
                    channel_identifier: {
                        'class': channel_holder_class,
                        'thread_class': check_streaming_channel_thread}
                })
                return [True, "OK"]
            else:
                if startup:
                    self.channels_dict.update({
                        channel_identifier: {
                            'class': channel_holder_class,
                            'error': error_message,
                            'thread_class': None}
                    })
                return [False, error_message]
        return [False, "UNKNOWN PLATFORM GIVEN TO RUN_CHANNEL."]

    def loadChannels(self):
        youtube_channel_ids = self.cachedDataHandler.getValue('channels_YOUTUBE')
        if youtube_channel_ids:
            for channel_id in youtube_channel_ids:
                ok, error_message = self.run_channel(channel_id, startup=True)
                if not ok:
                    warning(error_message)

    def run_youtube_queue(self):
        if self.cachedDataHandler.getValue('UploadLiveStreams'):
            check_streaming_channel_thread = Process(target=uploadQueue,
                                                     name="YouTube Upload Queue",
                                                     args=(self.cachedDataHandler, self.queue_holder,))
            check_streaming_channel_thread.start()
