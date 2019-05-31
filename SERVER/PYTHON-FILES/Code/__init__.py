from threading import Thread
from time import sleep
from .youtube.channelClass import ChannelInfo
from .utils.web import download_website

from .log import warning, verbose

"""
:type channel_main_array: array
"""

UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
            'Chrome/73.0.3683.103 Safari/537.36'

# Probably not the right type of class to put this stuff but I mean, there is public functions and variables in here.

channel_main_array = []
ServerClass = None


def run_channel(channel_id, returnMessage=False):
    channel_holder_class = ChannelInfo(channel_id)
    ok_bool, error_message = channel_holder_class.loadYoutubeData()
    if ok_bool:
        del ok_bool
        del error_message
        channel_holder_class.registerCloseEvent()
        check_streaming_channel_thread = Thread(target=channel_holder_class.check_streaming_thread,
                                                name=channel_holder_class.channel_name + " - Checking Live Thread")
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


def upload_test_run(channel_id, returnMessage=False):
    channel_holder_class = ChannelInfo(channel_id)
    ok_bool, error_message = channel_holder_class.loadYoutubeData()
    if ok_bool:
        del ok_bool
        del error_message

        if not channel_holder_class.is_live():
            del channel_holder_class
            return [False, "Channel is not live streaming! The channel needs to be live streaming!"]

        channel_holder_class.registerCloseEvent()
        check_streaming_channel_thread = Thread(target=channel_holder_class.check_streaming_thread,
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


def is_google_account_login_in():
    from .utils.web import cj
    cookie = [cookies for cookies in cj if 'SSID' in cookies.name]
    if cookie is None:
        return False
    return True


def check_internet():
    verbose("Checking Internet Connection.")
    youtube = download_website("https://www.youtube.com")
    return youtube is not None
