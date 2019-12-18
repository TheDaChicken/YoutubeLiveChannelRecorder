from multiprocessing import Process
from multiprocessing.managers import BaseManager

from Code.utils.web import build_cookies
from Code.YouTube import ChannelObject as ChannelYouTube
from Code.Twitch import ChannelObject as ChannelTwitch
from Code.dataHandler import CacheDataHandler
from Code.log import warning
from Code.YouTubeAPI.uploadQueue import QueueHandler, runQueue
from Code.serverHandler import loadServer
from Code.utils.other import try_get
from Code.YouTubeAPI import YouTubeAPIHandler


class ProcessHandler:
    channels_dict = {}

    debug_mode = False
    serverPort = 31311
    enable_ffmpeg_logs = False

    # YouTube Queue Stuff
    YouTubeQueueThread = None

    def __init__(self):
        # Create Shared Variables
        BaseManager.register('CacheDataHandler', CacheDataHandler)
        BaseManager.register('ChannelYouTube', ChannelYouTube)
        BaseManager.register("ChannelTwitch", ChannelTwitch)
        BaseManager.register("Dict", dict)
        BaseManager.register("QueueHandler", QueueHandler)
        BaseManager.register("YouTubeAPIHandler", YouTubeAPIHandler)

        # Channel Class
        self.baseManagerChannelInfo = BaseManager()
        self.baseManagerChannelInfo.start()

        # Data Handler
        self.baseManagerNormalHandlers = BaseManager()
        self.baseManagerNormalHandlers.start()
        self.cachedDataHandler = self.baseManagerNormalHandlers.CacheDataHandler()

        # Global Queue Holder.
        self.queue_holder = self.baseManagerNormalHandlers.QueueHandler()

        # YouTube API Handler
        self.baseManagerAPIHandlers = BaseManager()
        self.baseManagerAPIHandlers.start()
        self.youtube_api_handler = self.baseManagerAPIHandlers.YouTubeAPIHandler(self.cachedDataHandler)

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
                self.shared_cookieDictHolder, self.cachedDataHandler, self.queue_holder)
        if 'TWITCH' in platform:
            channel_holder_class = self.baseManagerChannelInfo.ChannelTwitch(
                channel_identifier, {'debug_mode': self.debug_mode, 'ffmpeg_logs': self.enable_ffmpeg_logs},
                self.shared_cookieDictHolder, self.cachedDataHandler, self.queue_holder)
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

    def run_channel_with_video_id(self, video_id):
        """

        Runs a Channel Instance without a channel id. Uses a Video ID to get channel id etc

        """
        channel_holder_class = self.baseManagerChannelInfo.ChannelYouTube(
            None, {'debug_mode': self.debug_mode, 'ffmpeg_logs': self.enable_ffmpeg_logs},
            self.shared_cookieDictHolder, self.cachedDataHandler, self.queue_holder)
        ok_bool, error_message = channel_holder_class.loadVideoData(video_id=video_id)
        if ok_bool:
            channel_holder_class.registerCloseEvent()
            channel_id = channel_holder_class.get("channel_id")
            channel_name = channel_holder_class.get("channel_name")
            check_streaming_channel_thread = Process(target=channel_holder_class.channel_thread,
                                                     name="{0} - Channel Process".format(channel_name))
            check_streaming_channel_thread.start()
            self.channels_dict.update({
                channel_id: {
                    'class': channel_holder_class,
                    'thread_class': check_streaming_channel_thread}
            })
            return [True, "OK"]
        else:
            return [False, error_message]

    def upload_test_run(self, channel_id):
        channel_holder_class = self.baseManagerChannelInfo.ChannelYouTube(
            channel_id, {'testUpload': True, 'debug_mode': self.debug_mode, 'ffmpeg_logs': self.enable_ffmpeg_logs},
            self.shared_cookieDictHolder, self.cachedDataHandler, self.queue_holder)
        ok_bool, error_message = channel_holder_class.loadVideoData()
        if ok_bool:
            del ok_bool
            del error_message
            if not channel_holder_class.is_live():
                return [False, "Channel is not live streaming! The channel needs to be live streaming!"]

            channel_holder_class.registerCloseEvent()
            channel_name = channel_holder_class.get("channel_name")
            check_streaming_channel_thread = Process(target=channel_holder_class.channel_thread,
                                                     name="{0} - Channel Process".format(channel_name))
            check_streaming_channel_thread.start()
            self.channels_dict.update({
                channel_id: {
                    'class': channel_holder_class,
                    'thread_class': check_streaming_channel_thread}
            })
            return [True, "OK"]
        else:
            return [False, error_message]

    def loadChannels(self):
        youtube_channel_ids = self.cachedDataHandler.getValue('channels_YOUTUBE')
        if youtube_channel_ids:
            for channel_id in youtube_channel_ids:
                ok, error_message = self.run_channel(channel_id, startup=True)
                if not ok:
                    warning(error_message)

    def run_youtube_queue(self):
        if self.cachedDataHandler.getValue('UploadLiveStreams'):
            self.YouTubeQueueThread = Process(target=runQueue,
                                              name="YouTube Upload Queue",
                                              args=(self.youtube_api_handler, self.queue_holder,))
            self.YouTubeQueueThread.start()

    def run_server(self, cert=None, key=None):
        key = try_get(self.cachedDataHandler, lambda x: x.getValue('ssl_key'), str) if not None else key
        cert = try_get(self.cachedDataHandler, lambda x: x.getValue('ssl_cert'), str) if not None else cert

        loadServer(self, self.cachedDataHandler, self.serverPort, self.youtube_api_handler,
                   cert=cert, key=key)

    def is_google_account_login_in(self):
        cj = self.shared_cookieDictHolder.copy()
        cookie = [cookies for cookies in cj if 'SSID' in cookies]
        if cookie is None or len(cookie) is 0:
            return False
        return True

