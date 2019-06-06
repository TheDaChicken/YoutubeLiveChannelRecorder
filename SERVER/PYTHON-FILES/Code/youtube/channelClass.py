import atexit
import os
import re
from datetime import datetime
from threading import Thread
from time import sleep

from .heatbeat import is_live
from . import set_global_youtube_variables
from ..dataHandler import UploadThumbnail, get_upload_settings
from ..log import verbose, stopped, warning, info, note
from ..utils.web import download_website, download_image
from ..utils.youtube import get_yt_player_config
from .player import openStream
from .communityPosts import is_live_sponsor_only_streams


class ChannelInfo:
    """

    Class that holds channel information and functions related to the information.

    :type channel_id: str
    :type channel_name: str
    :type video_id: str
    :type title: str
    :type start_date: datetime.datetime
    :type thumbnail_url: str
    :type video_location: str
    :type thumbnail_location: str
    :type live_scheduled: bool
    :type live_scheduled_time: str
    :type EncoderClass: Encoder, None
    """

    # USED FOR SERVER VARIABLES

    # Quick Bool isLive
    live_streaming = None
    # Status on recording
    recording_status = None

    # USED TO STOP THREADS
    stop_thread = False

    # USED FOR YOUTUBE'S HEARTBEAT SYSTEM AND IS NOT A GLOBAL VALUE
    pollDelayMs = None
    sequence_number = 0
    broadcastId = None

    # Channel Data
    channel_id = None
    channel_name = None

    # User
    sponsor_on_channel = False

    # Data about the stream. (THIS IS USED TO SHOW THE VARIABLES IN THIS CLASS)
    video_id = None
    title = None
    description = None
    start_date = None
    privateStream = False
    sponsor_only_stream = False

    # USED FOR RECORDING
    EncoderClass = None

    # USED FOR UPLOADING
    video_location = None

    # THUMBNAIL
    thumbnail_location = None
    thumbnail_url = None

    # (USED FOR SERVER)
    TestUpload = False

    # Scheduled Live Stream.
    live_scheduled = False
    live_scheduled_time = None

    def __init__(self, channel_id):
        self.channel_id = channel_id

    # Loads the Youtube Channel Data.
    def loadYoutubeData(self):
        html = download_website("https://www.youtube.com/channel/" + self.channel_id + "/live")
        if html is None:
            return [False, "Failed getting Youtube Data from the internet! "
                           "This means there is no good internet available!"]
        if html == 404:
            return [False, "Failed getting Youtube Data! \"" +
                    self.channel_id + "\" doesn't exist as a channel id!"]
        if type(html) is int:
            warning("" + str(html))
        self.channel_name = self.get_channel_name(html_code=html)
        if self.channel_name is None:
            return [False, "Failed Getting " + self.channel_id + " channel_name."]
        self.video_id = self.get_video_id(html_code=html)
        if self.video_id is None:
            if self.privateStream is not True:
                return [False, "Unable to find video id. Both fallback login and fallback private "
                               "didn't currently work. Please report this!"]

        # ONLY WORKS IF LOGGED IN
        self.sponsor_on_channel = self.get_sponsor_channel(html_code=html)

        # Stuff for getting Youtube web stuff like Heartbeat.
        # Which is needed for checking if channel's are live.
        # (I wish don't have to put them here but it's in the video link so..)

        if not self.privateStream:
            set_global_youtube_variables(html_code=html)

        return [True, "OK"]

    # CLOSE EVENT
    def registerCloseEvent(self):
        atexit.register(self.close_recording)

    def close_recording(self):
        if self.EncoderClass is not None:
            self.EncoderClass.stop_recording()
            self.EncoderClass = None

    def get_channel_name(self, html_code=None):
        verbose("Getting Channel Name of " + self.channel_id + ".")
        if html_code is None:
            html_code = download_website("https://www.youtube.com/channel/" + self.channel_id + "/live")
            if html_code is None:
                return None
        yt_player_config = get_yt_player_config(html_code)
        if yt_player_config:
            if "live_playback" not in yt_player_config['args']:
                array = re.findall('property="og:title" content="(.+?)"', html_code)
                self.privateStream = True
                if array is None:
                    stopped("Failed to get author! This must be a bug in the code! Please Report!")
                if 'author' not in yt_player_config['args']:
                    warning("ERROR IN PRIVATE SAFEGUARD.")
                    return None
                warning(
                    yt_player_config['args']['author'] + " has the live stream "
                                                         "currently unlisted or private, or only for members. "
                                                         "Using safeguard. This may not be the best to leave on.\n")
                return array[0]
            return yt_player_config['args']['author']
        else:
            # PRIVATE LOGIN FALLBACK
            array = re.findall('property="og:title" content="(.+?)"', html_code)
            if array:
                return array[0]
            verbose("Website HTML: " + str(html_code))
            stopped("Failed getting Channel Name! Please report this!")
            return None

    def get_video_id(self, html_code=None):
        verbose("Getting Video ID.")
        if html_code is None:
            html_code = download_website("https://www.youtube.com/channel/" + self.channel_id + "/live")
            if html_code is None:
                return None
        html_code = str(html_code)
        # This is a good check to see if the channel live is private.
        yt_player_config = get_yt_player_config(html_code)
        if yt_player_config:
            if 'args' not in yt_player_config:
                warning("Something happened when finding the video-id. There is no args in yt_player_config!")
                return None
            if "live_playback" not in yt_player_config['args']:
                self.privateStream = True
                return None
            if 'video_id' not in yt_player_config['args']:
                warning("Something happened when finding the video-id. Unable to find video id in yt player config.")
                return None
            return yt_player_config['args']['video_id']
        else:
            # PRIVATE LOGIN FALLBACK
            array = re.findall('property="og:title" content="(.+?)"', html_code)
            if array:
                self.privateStream = True
                return None
            else:
                return None

    def get_sponsor_channel(self, html_code=None):
        from .. import is_google_account_login_in
        if is_google_account_login_in():
            verbose("Checking if account sponsored " + self.channel_name + ".")
            if html_code is None:
                html_code = download_website("https://www.youtube.com/channel/" + self.channel_id + "/live")
                if html_code is None:
                    return None
            html_code = str(html_code)
            array = re.findall('/channel/' + self.channel_id + '/membership', html_code)
            if array:
                return True
            return False
        return False

    def check_streaming_thread(self, TestUpload=False):
        self.TestUpload = TestUpload
        first_time = True
        while True:
            boolean_live = self.is_live(first_time=first_time)  # Checks if stream is live.
            self.live_streaming = boolean_live
            if not boolean_live:
                first_time = False
                if self.sponsor_on_channel:
                    verbose("Reading Community Posts on " + self.channel_name + ".")
                    # NOTE this edits THE video id when finds stream.
                    boolean_live = self.is_live_sponsor_only_streams()
                    if not boolean_live:
                        info(self.channel_name + "'s channel live streaming is currently private/unlisted!")
                        info("Checked Community Posts for any Sponsor Only live Streams. Didn't Find Anything!")
                        sleep(self.pollDelayMs / 1000)
                    if boolean_live:
                        self.sponsor_only_stream = True
                else:
                    if self.sponsor_only_stream:
                        self.sponsor_only_stream = False
                    if not self.privateStream:
                        info(self.channel_name + " is not live!")
                        sleep(self.pollDelayMs / 1000)
                    else:
                        info(self.channel_name + "'s channel live streaming is currently private/unlisted!")
                        sleep(self.pollDelayMs / 1000)
            if boolean_live:
                if first_time is True:
                    info(self.channel_name + " is already Live!")
                else:
                    info(self.channel_name + " is now Live!")
                fully_recorded = openStream(self, None, alreadyLIVE=first_time)
                if fully_recorded:
                    thread = Thread(target=self.start_upload, name=self.channel_name)
                    thread.daemon = True  # needed control+C to work.
                    thread.start()
                    if self.TestUpload:
                        thread.join()
                        stopped("Test upload completed!")  # Kinda of closes the whole Thread :P
                sleep(2.5)
            if boolean_live is None:
                warning("Internet Offline. :/")
                sleep(10)

    def is_live(self, first_time=False):
        return is_live(self, first_time=first_time)

    def is_live_sponsor_only_streams(self):
        return is_live_sponsor_only_streams(self)

    def create_filename(self, video_id):
        now = datetime.now()
        self.start_date = now
        # Used to handle lots of names by creating new names and add numbers!
        amount = 1
        while True:
            if amount is 1:
                file_name = "{3} - '{4}' - {0}-{1}-{2}".format(now.month, now.day, now.year, self.channel_name,
                                                               video_id)
            else:
                file_name = "{3} - '{4}' - {0}-{1}-{2}_{5}".format(now.month, now.day, now.year, self.channel_name,
                                                                   video_id,
                                                                   amount)
            path = os.path.join("RecordedStreams", file_name + '.mp4')
            if not os.path.isfile(path):
                verbose("Found Good Filename.")
                return file_name
            amount = amount + 1

    def download_thumbnail(self):
        info("Starting Download of Live Stream Thumbnail.")
        downloaded = download_image(self.thumbnail_url, self.thumbnail_location)
        if downloaded:
            info("Done Downloading Thumbnail!")
        else:
            info("Not able to download thumbnail!")

    # Uploading
    def start_upload(self):
        # Allows to get the most updated client without saving it, since it might change.
        from ..youtubeAPI import get_youtube_client, initialize_upload, upload_thumbnail
        youtube_client = get_youtube_client(ignoreConfig=self.TestUpload)
        if youtube_client is not None:
            verbose("Starting Upload Thread ...")
            note("Closing the python script stops the upload.")
            settings = get_upload_settings(self.channel_name)
            upload_video_id = initialize_upload(youtube_client, self.video_location,
                                                self._replace_variables(settings['title']),
                                                self._replace_variables('\n'.join(settings['description'])),
                                                self._replace_variables(settings['tags']),
                                                settings['CategoryID'], settings['privacyStatus'])
            if UploadThumbnail() is True:
                info("Uploading Thumbnail for " + self.channel_name)
                sleep(1.5)
                upload_thumbnail(youtube_client, upload_video_id,
                                 self.thumbnail_location)
                info("Thumbnail Done Uploading!")

    def _replace_variables(self, text):
        if text is None or text is False or text is True:
            return None
        if "%VIDEO_ID%" in text:
            text = text.replace("%VIDEO_ID%", self.video_id)
        if "%FILENAME%" in text:
            text = text.replace("%FILENAME%", self.video_location)
        if "%CHANNEL_ID%" in text:
            text = text.replace("%CHANNEL_ID%", self.channel_id)
        if "%CHANNEL_NAME%" in text:
            text = text.replace("%CHANNEL_NAME%", self.channel_name)
        if "%DATE_MONTH%" in text:
            now = self.start_date
            text = text.replace("%DATE_MONTH%", str(now.month))
        if "%DATE_DAY%" in text:
            now = self.start_date
            text = text.replace("%DATE_DAY%", str(now.day))
        if "%DATE_YEAR%" in text:
            now = self.start_date
            text = text.replace("%DATE_YEAR%", str(now.year))
        if "%DATE%" in text:
            now = self.start_date
            text = text.replace("%DATE%", "{0}-{1}-{2}".format(now.month, now.day, now.year))
        if "%TITLE%" in text:
            text = text.replace("%TITLE%", "{0}".format(self.title))
        if '%DESCRIPTION%' in text:
            text = text.replace("%DESCRIPTION%", "{0}".format(self.description))
        return text
