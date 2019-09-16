import os
from multiprocessing import Process
from multiprocessing.managers import BaseManager, Namespace
from threading import Thread

from .youtubeAPI.uploadQueue import uploadQueue, QueueHandler
from .youtube.channelClass import ChannelInfo
from .twitch.channelClass import ChannelInfoTwitch
from .utils.web import download_website, __build__cookies
from .dataHandler import CacheDataHandler
from .log import verbose

UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
            'Chrome/75.0.3770.100 Safari/537.36'

# Probably not the right type of class to put this stuff but I mean, there is public functions and variables in here.

channel_main_array = []
ServerClass = None

baseManagerChannelInfo = None  # type: BaseManager
baseManagerDataHandler = None  # type: BaseManager

shareable_variables = None  # type: Namespace
cached_data_handler = None  # type: CacheDataHandler
queue_holder = None
uploadThread = None


def setupSharedVariables():
    global baseManagerChannelInfo
    global baseManagerDataHandler
    global shareable_variables
    global cached_data_handler
    global queue_holder

    BaseManager.register('ChannelInfo', ChannelInfo)
    BaseManager.register('ChannelInfoTwitch', ChannelInfoTwitch)
    BaseManager.register('CacheDataHandler', CacheDataHandler)
    BaseManager.register('QueueHandler', QueueHandler)

    # Regular Shared Variables
    shareable_variables = Namespace()
    shareable_variables.DebugMode = False

    # start baseManager for channelInfo.
    baseManagerChannelInfo = BaseManager()
    baseManagerChannelInfo.start()

    # Cache Data File. (Data Cache is in a class)
    baseManagerDataHandler = BaseManager()
    baseManagerDataHandler.start()
    cached_data_handler = baseManagerDataHandler.CacheDataHandler()

    # Global Queue Holder.
    queue_holder = baseManagerDataHandler.QueueHandler()

    # Cache Cookies in shareable_variables. (Cookies are cached in a list)
    # Cannot make into global class due to problems.
    from .utils.web import __build__cookies
    cookieHandler = __build__cookies()
    cookies_ = cookieHandler.get_cookie_list()
    if cookies_:
        shareable_variables.CachedCookieList = cookies_


class HandlerChannelList:
    list_ = []

    def add(self, object_):
        self.list_.append(object_)

    def remove(self, object_):
        self.list_.remove(object_)


def run_channel(channel_identifier, platform='YOUTUBE', startup=False, addToData=False):
    """
    :param channel_identifier: Different per platform. Youtube is Channel_id, Twitch is channel_name. :P
    :type channel_identifier: str
    :param platform: What platform to run.
    :param startup: If running in main __main__.py script.
    :param addToData: Add to data file, if channel runs correctly.
    """
    if 'YOUTUBE' in platform:
        channel_holder_class = baseManagerChannelInfo.ChannelInfo(channel_identifier, shareable_variables,
                                                                  cached_data_handler, queue_holder)
    if 'TWITCH' in platform:
        channel_holder_class = baseManagerChannelInfo.ChannelInfoTwitch(channel_identifier, shareable_variables,
                                                                        cached_data_handler, queue_holder)
    if channel_holder_class:
        ok_bool, error_message = channel_holder_class.loadVideoData()
        if ok_bool:
            del ok_bool
            del error_message
            channel_holder_class.registerCloseEvent()
            channel_name = channel_holder_class.get("channel_name")
            check_streaming_channel_thread = Process(target=channel_holder_class.channel_thread,
                                                     name="{0} - Channel Process".format(channel_name))
            check_streaming_channel_thread.start()
            channel_main_array.append(
                {'class': channel_holder_class, 'thread_class': check_streaming_channel_thread})
            if addToData:
                cached_data_handler.addValueList('channels_{0}'.format(platform), channel_identifier)
            return [True, "OK"]
        else:
            if startup:
                channel_main_array.append(
                    {'class': channel_holder_class, "error": error_message, 'thread_class': None})
            return [False, error_message]
    return [False, "UNKNOWN PLATFORM GIVEN TO RUN_CHANNEL."]


def upload_test_run(channel_id, startup=False):
    channel_holder_class = baseManagerChannelInfo.ChannelInfo(channel_id, shareable_variables,
                                                              cached_data_handler, queue_holder)
    ok_bool, error_message = channel_holder_class.loadVideoData()
    if ok_bool:
        del ok_bool
        del error_message

        if not channel_holder_class.is_live():
            return [False, "Channel is not live streaming! The channel needs to be live streaming!"]

        channel_holder_class.registerCloseEvent()
        channel_name = channel_holder_class.get("channel_name")
        check_streaming_channel_thread = Process(target=channel_holder_class.channel_thread,
                                                 name="{0} - Channel Process".format(channel_name), args=(True,))
        check_streaming_channel_thread.start()
        channel_main_array.append(
            {'class': channel_holder_class, 'thread_class': check_streaming_channel_thread})
        return [True, "OK"]
    else:
        if startup:
            channel_main_array.append(
                {'class': channel_holder_class, "error": error_message, 'thread_class': None})
        return [False, error_message]


def run_channel_with_video_id(video_id, startup=False, addToData=False):
    channel_holder_class = baseManagerChannelInfo.ChannelInfo(None, shareable_variables,
                                                              cached_data_handler, queue_holder)
    ok_bool, error_message = channel_holder_class.loadVideoData(video_id=video_id)
    if ok_bool:
        del ok_bool
        del error_message
        channel_id = channel_holder_class.get('channel_id')

        channel_holder_class.registerCloseEvent()
        channel_name = channel_holder_class.get("channel_name")
        check_streaming_channel_thread = Process(target=channel_holder_class.channel_thread,
                                                 name="{0} - Channel Process".format(channel_name))
        check_streaming_channel_thread.start()
        channel_main_array.append(
            {'class': channel_holder_class, 'thread_class': check_streaming_channel_thread})
        if addToData:
            cached_data_handler.addValueList('channels_{0}'.format('YOUTUBE'), channel_id)
        return [True, "OK"]
    else:
        if startup:
            channel_main_array.append(
                {'class': channel_holder_class, "error": error_message, 'thread_class': None})
        return [False, error_message]


def run_server(port, cert=None, key=None):
    from .serverHandler import loadServer
    loadServer(
        cached_data_handler, port, cert=cert, key=key)


def run_youtube_queue_thread(skipValueCheck=False):
    global uploadThread
    if not uploadThread:
        if skipValueCheck or cached_data_handler.getValue('UploadLiveStreams'):
            uploadThread = Process(target=uploadQueue,
                                   name="Upload Thread.", args=(cached_data_handler, queue_holder,))
            uploadThread.start()
            return [True, "OK"]
    return [False, "Already started."]


def stop_youtube_queue_thread():
    global uploadThread
    if uploadThread:
        uploadThread.terminate()
        uploadThread.join()  # wait until done.
        # uploadThread.close() (ERROR IDK LOL)
        uploadThread = None
        return [True, "OK"]
    return [False, "Welp, already stopped."]


# VERY BETA
def google_account_login(username, password):
    from .youtube.login import login
    return login(username, password)


def google_account_logout():
    # STOP HEARTBEAT
    download_website("https://www.youtube.com/logout")
    if is_google_account_login_in() is True:
        return [False, "Failed to logout. :/"]
    return [True, "OK"]


def is_google_account_login_in():
    cj = __build__cookies()
    cookie = [cookies for cookies in cj if 'SSID' in cookies.name]
    if cookie is None or len(cookie) is 0:
        return False
    return True


def check_internet():
    verbose("Checking Internet Connection.")
    youtube = download_website("https://www.youtube.com")
    return youtube is not None


def enable_debug():
    global shareable_variables
    shareable_variables.DebugMode = True


def setupStreamsFolder():
    # RecordedStreams
    recorded_streams_dir = os.path.join(os.getcwd(), "RecordedStreams")
    if os.path.exists(recorded_streams_dir) is False:
        os.mkdir(recorded_streams_dir)
