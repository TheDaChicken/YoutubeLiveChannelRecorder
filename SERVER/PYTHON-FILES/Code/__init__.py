import os
from multiprocessing import Process
from multiprocessing.managers import BaseManager, Namespace

from .youtube.channelClass import ChannelInfo
from .utils.web import download_website, __build__cookies
from .dataHandler import CacheDataHandler
from .log import warning, verbose

"""
:type channel_main_array: array
"""

UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
            'Chrome/75.0.3770.100 Safari/537.36'

# Probably not the right type of class to put this stuff but I mean, there is public functions and variables in here.

channel_main_array = []
ServerClass = None

baseManagerChannelInfo = None  # type: BaseManager
baseManagerDataHandler = None  # type: BaseManager

shareable_variables = None  # type: Namespace
cached_data_handler = None  # type: CacheDataHandler


def setupSharedVariables():
    global baseManagerChannelInfo
    global baseManagerDataHandler
    global shareable_variables
    global cached_data_handler

    BaseManager.register('HandlerChannelInfo', HandlerChannelInfo)
    BaseManager.register('CacheDataHandler', CacheDataHandler)

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

    # Cache Cookies in shareable_variables. (Cookies are cached in a list)
    # Cannot make into global class due to problems.
    from .utils.web import __build__cookies
    cookieHandler = __build__cookies()
    cookies_ = cookieHandler.get_cookie_list()
    if cookies_:
        shareable_variables.CachedCookieList = cookies_


class HandlerChannelInfo(ChannelInfo):
    """

    This is a way of sharing variables from MultiThreading Process.
    I couldn't find anything online, so what am I going to do?

    """

    def __init__(self, channel_id, SharedVariables, cachedDataHandler=None):
        super().__init__(channel_id, SharedVariables, cachedDataHandler)

    def get(self, variable_name):
        return getattr(self, variable_name)

    def set(self, variable_name, value):
        return setattr(self, variable_name, value)

    def list(self):
        return self.__dict__


def run_channel(channel_id, startup=False):
    channel_holder_class = baseManagerChannelInfo.HandlerChannelInfo(channel_id, shareable_variables,
                                                                     cachedDataHandler=cached_data_handler)
    ok_bool, error_message = channel_holder_class.loadYoutubeData()
    if ok_bool:
        del ok_bool
        del error_message
        channel_holder_class.registerCloseEvent()
        # check_streaming_channel_thread.daemon = True  # needed control+C to work.
        channel_name = channel_holder_class.get("channel_name")
        check_streaming_channel_thread = Process(target=channel_holder_class.start_heartbeat_loop,
                                                 name="{0} - Heartbeat Thread".format(channel_name))
        check_streaming_channel_thread.start()
        channel_main_array.append({'class': channel_holder_class, 'thread_class': check_streaming_channel_thread})
        return [True, "OK"]
    else:
        if startup:
            channel_main_array.append({'class': channel_holder_class, "error": error_message, 'thread_class': None})
        return [False, error_message]


def upload_test_run(channel_id, returnMessage=False):
    # TODO UPDATE.
    channel_holder_class = baseManagerChannelInfo.HandlerChannelInfo(channel_id, shareable_variables)
    ok_bool, error_message = channel_holder_class.loadYoutubeData()
    if ok_bool:
        del ok_bool
        del error_message

        if not channel_holder_class.is_live():
            del channel_holder_class
            return [False, "Channel is not live streaming! The channel needs to be live streaming!"]

        channel_holder_class.registerCloseEvent()
        channel_name = channel_holder_class.get("channel_name")
        check_streaming_channel_thread = Process(target=channel_holder_class.start_heartbeat_loop,
                                                 name="{0} - Heartbeat Thread".format(channel_name), args=(True,))
        check_streaming_channel_thread.daemon = True  # needed control+C to work.
        check_streaming_channel_thread.start()
        channel_main_array.append({'class': channel_holder_class, 'thread_class': check_streaming_channel_thread})
        if returnMessage is True:
            return [True, "OK"]
    else:
        if returnMessage is True:
            return [False, error_message]
        else:
            warning(error_message)
            channel_main_array.append({'class': channel_holder_class, "error": error_message})
    return channel_holder_class


# VERY BETA
def google_account_login(username, password):
    from .GoogleLogin import login
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
