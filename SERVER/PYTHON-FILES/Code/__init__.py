import os
from multiprocessing import Process, Value
from multiprocessing.managers import BaseManager, Namespace
from threading import Thread
from time import sleep

from .youtube.channelClass import ChannelInfo
from .utils.web import download_website

from .log import warning, verbose, stopped

"""
:type channel_main_array: array
"""

UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
            'Chrome/74.0.3729.169 Safari/537.36'

# Probably not the right type of class to put this stuff but I mean, there is public functions and variables in here.

channel_main_array = []
ServerClass = None

baseManager = None  # type: BaseManager
settings = None  # type: Namespace


def setup_manager():
    global baseManager
    global settings
    BaseManager.register('HandlerChannelInfo', HandlerChannelInfo)
    baseManager = BaseManager()
    baseManager.start()
    settings = Namespace()
    settings.DebugMode = False


class HandlerChannelInfo(ChannelInfo):
    """

    This is a way of sharing variables from MultiThreading Process.
    I couldn't find anything online, so what am I going to do?

    """

    def __init__(self, channel_id, SettingsManager):
        super().__init__(channel_id, SettingsManager)

    def get(self, variable_name):
        return getattr(self, variable_name)

    def list(self):
        return self.__dict__


def run_channel(channel_id, returnMessage=False):
    channel_holder_class = baseManager.HandlerChannelInfo(channel_id, settings)
    ok_bool, error_message = channel_holder_class.loadYoutubeData()
    if ok_bool:
        del ok_bool
        del error_message
        channel_holder_class.registerCloseEvent()
        check_streaming_channel_thread = Process(target=channel_holder_class.start_heartbeat_loop,
                                                 name="{0} - Heartbeat Thread".format(
                                                     channel_holder_class.get("channel_name")))
        # check_streaming_channel_thread.daemon = True  # needed control+C to work.
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
    return [False, ""]


def upload_test_run(channel_id, returnMessage=False):
    # TODO UPDATE.
    channel_holder_class = ChannelInfo(channel_id)
    ok_bool, error_message = channel_holder_class.loadYoutubeData()
    if ok_bool:
        del ok_bool
        del error_message

        if not channel_holder_class.is_live():
            del channel_holder_class
            return [False, "Channel is not live streaming! The channel needs to be live streaming!"]

        channel_holder_class.registerCloseEvent()
        check_streaming_channel_thread = Thread(target=channel_holder_class.start_heartbeat_loop,
                                                name=channel_holder_class.channel_name, args=(True,))
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
    download_website("https://www.youtube.com/logout")
    sleep(1)
    if is_google_account_login_in() is True:
        return [False, "Failed to logout. :/"]
    return [True, "OK"]


def is_google_account_login_in():
    try:
        from http.cookiejar import LWPCookieJar, LoadError
    except ImportError:
        LoadError = None
        LWPCookieJar = None
        stopped("Unsupported version of Python. You need Version 3 :<")

    cj = LWPCookieJar(filename="cookies.txt")
    if os.path.isfile("cookies.txt"):
        try:
            cj.load()
        except Exception as e:
            warning("Unable to access cookies.")
            warning("Error: " + str(e))
            return False

    cookie = [cookies for cookies in cj if 'SSID' in cookies.name]
    if cookie is None or len(cookie) is 0:
        return False
    return True


def check_internet():
    verbose("Checking Internet Connection.")
    youtube = download_website("https://www.youtube.com")
    return youtube is not None


def enable_debug():
    global settings
    settings.DebugMode = True


def setupStreamsFolder():
    # RecordedStreams
    recorded_streams_dir = os.path.join(os.getcwd(), "RecordedStreams")
    if os.path.exists(recorded_streams_dir) is False:
        os.mkdir(recorded_streams_dir)
