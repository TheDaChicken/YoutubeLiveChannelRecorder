import atexit
import os
import re
import traceback
from datetime import datetime
from multiprocessing.managers import Namespace
from threading import Thread
from time import sleep

from .heatbeat import is_live
from . import set_global_youtube_variables, generate_cpn
from ..log import verbose, stopped, warning, info, note, crash_warning, error_warning
from ..utils.other import try_get, get_format_from_data, get_highest_thumbnail, getTimeZone
from ..utils.parser import parse_json
from ..utils.web import download_website, download_image, download_m3u8_formats
from ..utils.youtube import get_yt_player_config, get_endpoint_type
from .player import openStream, getYoutubeStreamInfo
from .communityPosts import is_live_sponsor_only_streams


class ChannelInfo:
    """

    Class that holds channel information and functions related to the information.

    # Channel Data
    :type channel_id: str
    :type channel_name: str

    # Stream Data.
    :type video_id: str, None
    :type title: str
    :type start_date: datetime.datetime
    :type description: str
    :type privateStream: bool
    :type sponsor_only_stream: bool
    :type YoutubeStream: dict, None

    # USED FOR RECORDING.
    :type EncoderClass: Encoder

    # USED FOR HOLDING THUMBNAILS
    :type thumbnail_url: str
    :type thumbnail_location: str

    # USED FOR UPLOADING.
    :type video_location: str

    # USED IN HEARTBEAT TO BE SHOWN ON CLIENT.
    :type live_scheduled: bool
    :type live_scheduled_time: str

    # Server-type Variables
    :type live_streaming, bool
    :type recording_status: str
    :type stop_heartbeat: bool
    :type SharedVariables: Namespace
    :type sharedCookies: Value
    :type crashed_traceback: str

    # HEARTBEAT Variables
    :type pollDelayMs: int
    :type sequence_number: int
    :type broadcastId: str
    :type last_heartbeat: datetime.datetime

    # USER ACCOUNT
    :type sponsor_on_channel: bool

    # PER-CHANNEL YOUTUBE VARIABLES
    :type cpn: str
    """

    # USED FOR SERVER VARIABLES
    live_streaming = None
    recording_status = None
    stop_heartbeat = False
    SharedVariables = False
    sharedCookies = False
    crashed_traceback = None

    # USED FOR YOUTUBE'S HEARTBEAT SYSTEM AND IS NOT A GLOBAL VALUE
    pollDelayMs = 8000
    sequence_number = 0
    broadcastId = None
    last_heartbeat = None

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
    YoutubeStream = None  # DICT THAT HOLDS STREAM URLS

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

    # PER-CHANNEL YOUTUBE VARIABLES
    cpn = None

    def __init__(self, channel_id, SharedVariables=None, cachedDataHandler=None):
        self.cachedDataHandler = cachedDataHandler
        self.channel_id = channel_id
        self.SharedVariables = SharedVariables

    def loadYoutubeData(self):
        html = download_website("https://www.youtube.com/channel/{0}/live".
                                format(self.channel_id), SharedVariables=self.SharedVariables)
        if html is None:
            return [False, "Failed getting Youtube Data from the internet! "
                           "This means there is no good internet available!"]
        if html == 404:
            return [False, "Failed getting Youtube Data! \"{0}\" doesn't exist as a channel id!".format(
                self.channel_id)]
        yt_player_config = try_get(get_yt_player_config(html), lambda x: x['args'], dict)
        ok, message = self.loadChannelData(html_code=html, yt_player_config=yt_player_config)
        if not ok:
            return [ok, message]
        ok, message = self.loadVideoData(html=html, yt_player_config=yt_player_config)
        if not self.privateStream:
            set_global_youtube_variables(html_code=html)

        # ONLY WORKS IF LOGGED IN
        self.sponsor_on_channel = self.get_sponsor_channel(html_code=html)

        self.cpn = generate_cpn()
        return [ok, message]

    # Loads the Youtube Channel Data.
    def loadChannelData(self, html_code=None, yt_player_config=None):
        if not html_code and not yt_player_config:
            html_code = download_website("https://www.youtube.com/channel/{0}/live".
                                         format(self.channel_id), SharedVariables=self.SharedVariables)
            if html_code is None:
                return [False, "Failed getting Channel Data from the internet! "
                               "This means there is no good internet available!"]
            if html_code == 404:
                return [False, "Failed getting Channel Data! \"" +
                        self.channel_id + "\" doesn't exist as a channel id!"]
        if type(html_code) is int:
            warning("" + str(html_code))
        verbose("Getting Channel Name of " + self.channel_id + ".")
        endpoint_type = get_endpoint_type(html_code)
        if endpoint_type:
            if endpoint_type == 'browse':
                array = re.findall('property="og:title" content="(.+?)"', html_code)
                if array:
                    channel_name = array[0]
                    warning(
                        channel_name + " has the live stream "
                                       "currently unlisted or private, or only for members. "
                                       "Using safeguard. This may not be the best to leave on.\n")
                    self.channel_name = channel_name
            elif endpoint_type == 'watch':
                if not yt_player_config:
                    yt_player_config = try_get(get_yt_player_config(html_code), lambda x: x['args'], dict)
                if yt_player_config:
                    if "is_live_destination" in yt_player_config:
                        self.channel_name = yt_player_config['author']
                    else:
                        warning("Found a stream, the stream seemed to be a non-live stream.")
                else:
                    stopped("Unable to get yt player config.")
            else:
                warning("Unrecognized endpoint type. Endpoint Type: {0}".format(endpoint_type))
                if not yt_player_config:
                    yt_player_config = try_get(get_yt_player_config(html_code), lambda x: x['args'], dict)
                if yt_player_config:
                    if "is_live_destination" in yt_player_config:
                        return yt_player_config['author']
                    else:
                        warning("Found a stream, the stream seemed to be a non-live stream.")
                else:
                    stopped("Unable to get yt player config.")

        if self.channel_name is None:
            return [False, "Failed Getting " + self.channel_id + " channel_name."]
        return [True, "OK"]

    def loadVideoData(self, html=None, yt_player_config=None):
        """

        This is used to grab video information from the YouTube Channel Live site, like video_id,
        to check if already live, and the stream url if already live.
        Everything else would use heartbeat and get video info url.

        :return: Nothing. It edits the class.
        """
        verbose("Getting Video ID.")
        if not html:
            html = download_website("https://www.youtube.com/channel/{0}/live".
                                    format(self.channel_id), SharedVariables=self.SharedVariables)
            if html is None:
                return [False, "Failed getting Video Data from the internet! "
                               "This means there is no good internet available!"]
            if html == 404:
                return [False, "Failed getting Video Data! \""
                               "{0}\" doesn't exist as a channel id!".format(self.channel_id)]
        if not yt_player_config:
            yt_player_config = try_get(get_yt_player_config(html), lambda x: x['args'], dict)
        if yt_player_config:
            if "is_live_destination" in yt_player_config:
                self.video_id = try_get(yt_player_config, lambda x: x['video_id'], str)
                self.privateStream = False
                if not self.video_id:
                    return [False, "Unable to find video id in the YouTube player config!"]
            else:
                self.video_id = None
                self.privateStream = True
        else:
            self.privateStream = True

        if not self.privateStream:
            # TO AVOID REPEATING REQUESTS.
            player_response = parse_json(try_get(yt_player_config, lambda x: x['player_response'], str))
            if player_response:
                # playabilityStatus is legit heartbeat all over again..
                playabilityStatus = try_get(player_response, lambda x: x['playabilityStatus'], dict)
                if playabilityStatus:
                    if "OK" in playabilityStatus['status']:
                        if "streamingData" not in player_response:
                            return [False, "No StreamingData, Youtube bugged out!"]
                        manifest_url = str(
                            try_get(player_response, lambda x: x['streamingData']['hlsManifestUrl'], str))
                        if not manifest_url:
                            return [False, "Unable to find HLS Manifest URL."]
                        formats = download_m3u8_formats(manifest_url)
                        if formats is None or len(formats) is 0:
                            return [False, "There were no formats found! Even when the streamer is live."]
                        f = get_format_from_data(formats, None)
                        videoDetails = try_get(player_response, lambda x: x['videoDetails'], dict)
                        thumbnails = try_get(videoDetails, lambda x: x['thumbnail']['thumbnails'], list)
                        if thumbnails:
                            self.thumbnail_url = get_highest_thumbnail(thumbnails)
                        self.YoutubeStream = {
                            'stream_resolution': '' + str(f['width']) + 'x' + str(f['height']),
                            'url': f['url'],
                            'title': videoDetails['title'],
                            'description': videoDetails['shortDescription'],
                        }

        return [True, "OK"]

    # CLOSE EVENT
    def registerCloseEvent(self):
        atexit.register(self.close_recording)

    def close(self):
        self.close_recording()
        self.stop_heartbeat = True

    def close_recording(self):
        if self.EncoderClass is not None:
            self.EncoderClass.stop_recording()
            self.EncoderClass = None

    def get_sponsor_channel(self, html_code=None):
        from .. import is_google_account_login_in
        if is_google_account_login_in():
            verbose("Checking if account sponsored " + self.channel_name + ".")
            if html_code is None:
                html_code = download_website("https://www.youtube.com/channel/" + self.channel_id + "/live",
                                             SharedVariables=self.SharedVariables)
                if html_code is None:
                    return None
            html_code = str(html_code)
            array = re.findall('/channel/' + self.channel_id + '/membership', html_code)
            if array:
                return True
            return False
        return False

    def start_heartbeat_loop(self, TestUpload=False):
        """

        Checks for streams, records them if live.
        Best under a thread to allow multiple channels.

        """
        alreadyChecked = True
        self.TestUpload = TestUpload
        # noinspection PyBroadException
        try:
            while self.stop_heartbeat is False:
                # LOOP
                boolean_live = self.is_live(alreadyChecked=alreadyChecked)
                if boolean_live is 1:
                    # IF CRASHED.
                    info("Error on Heartbeat on {0}! Trying again ...".format(self.channel_name))
                    sleep(1)
                if not boolean_live:
                    # HEARTBEAT INTERNET OFFLINE.
                    if boolean_live is None:
                        warning("INTERNET OFFLINE")
                        sleep(2.4)
                    elif self.sponsor_on_channel:
                        verbose("Reading Community Posts on {0}.".format(self.channel_name))
                        # NOTE this edits THE video id when finds stream.
                        boolean_found = self.is_live_sponsor_only_streams()
                        if not boolean_found:
                            if boolean_found is None:
                                warning("INTERNET OFFLINE")
                                sleep(2.52)
                            else:
                                info("{0}'s channel live streaming is currently private/unlisted!".format(
                                    self.channel_name))
                                info("Checked Community Posts for any Sponsor Only live Streams. Didn't Find "
                                     "Anything!")
                                sleep(self.pollDelayMs / 1000)
                        if boolean_found:
                            self.sequence_number = 0
                            boolean_live = self.is_live(alreadyChecked=alreadyChecked)
                            self.sponsor_only_stream = True
                    else:
                        if self.sponsor_only_stream is True:
                            self.sponsor_only_stream = False
                        if not self.privateStream:
                            info("{0} is not live!".format(self.channel_name))
                            sleep(self.pollDelayMs / 1000)
                        else:
                            info("{0}'s channel live streaming is currently private/unlisted!".format(
                                self.channel_name))
                            sleep(self.pollDelayMs / 1000)
                if boolean_live:
                    self.recording_status = "Getting Youtube Stream Info."
                    if self.YoutubeStream is None:
                        self.YoutubeStream = self.getYoutubeStreamInfo(recordingHeight=None)
                    if self.YoutubeStream is not None:
                        fully_recorded = self.openStream(self.YoutubeStream, sharedDataHandler=self.cachedDataHandler)
                        self.YoutubeStream = None
                        if fully_recorded:
                            thread = Thread(target=self.start_upload, name=self.channel_name)
                            thread.daemon = True  # needed control+C to work.
                            thread.start()
                            if self.TestUpload:
                                thread.join()
                                stopped("Test upload completed!")  # Kinda of closes the whole Thread :P
                        sleep(2.5)
                    else:
                        self.recording_status = "Unable to get Youtube Stream Info."
                        self.live_streaming = None
                        warning("Unable to get Youtube Stream Info from this stream: ")
                        warning("VIDEO ID: " + self.video_id)
                        warning("CHANNEL ID: " + self.channel_id)
                    sleep(self.pollDelayMs / 1000)
                if alreadyChecked:
                    alreadyChecked = False
                # REPEAT (END OF LOOP)
        except Exception:
            self.crashed_traceback = traceback.format_exc()
            crash_warning("{0}:\n{1}".format(self.channel_name, traceback.format_exc()))

    def is_live(self, alreadyChecked=False):
        if self.SharedVariables:
            if self.SharedVariables.DebugMode:
                self.last_heartbeat = datetime.now()
        boolean_live = is_live(self, alreadyChecked=alreadyChecked, SharedVariables=self.SharedVariables)
        self.live_streaming = boolean_live  # UPDATE SERVER VARIABLE
        return boolean_live

    def is_live_sponsor_only_streams(self):
        boolean_live = is_live_sponsor_only_streams(self, SharedVariables=self.SharedVariables)
        self.live_streaming = boolean_live  # UPDATE SERVER VARIABLE
        return boolean_live

    def openStream(self, YoutubeStream, sharedDataHandler=None):
        return openStream(self, YoutubeStream, sharedDataHandler)

    def getYoutubeStreamInfo(self, recordingHeight=None):
        return getYoutubeStreamInfo(self, recordingHeight=recordingHeight)

    def create_filename(self, video_id):
        now = datetime.now()
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
        if self.thumbnail_url:
            was_able = download_image(self.thumbnail_url, self.thumbnail_location)
        else:
            was_able = False
        if was_able:
            info("Done Downloading Thumbnail!")
        else:
            info("Not able to download thumbnail!")

    # Uploading
    def start_upload(self):
        def get_upload_settings(channel_name):
            upload_settings = self.cachedDataHandler.getValue('UploadSettings')
            if channel_name in upload_settings:
                return upload_settings[channel_name]
            return upload_settings[None]
        # Allows to get the most updated client without saving it, since it might change.
        from ..youtubeAPI import get_youtube_api_credentials, initialize_upload, upload_thumbnail
        youtube_client = get_youtube_api_credentials(self.cachedDataHandler)
        if youtube_client:
            verbose("Starting Upload Thread ...")
            note("Closing the python script stops the upload.")
            settings = get_upload_settings(self.channel_name)
            try:
                upload_video_id = initialize_upload(youtube_client, self.video_location,
                                                    self._replace_variables(settings['title']),
                                                    self._replace_variables('\n'.join(settings['description'])),
                                                    self._replace_variables(settings['tags']),
                                                    settings['CategoryID'], settings['privacyStatus'])
                sleep(3)
                if self.cachedDataHandler.getValue('UploadThumbnail') is True:
                    info("Uploading Thumbnail for {0}".format(self.channel_name))
                    upload_thumbnail(youtube_client, upload_video_id,
                                     self.thumbnail_location)
                    info("Thumbnail Done Uploading!")
            except Exception:
                error_warning(traceback.format_exc())
                warning("Unable to upload stream to Youtube.")

    def _replace_variables(self, text):
        class DataDict(dict):
            """
                Taken from and
                have been edited: https://stackoverflow.com/a/11023271
            """

            def __missing__(self, key):
                return ''

        if text is None or text is False or text is True:
            return None
        now = self.start_date
        timezone = getTimeZone()
        text = text.format(
            **DataDict(VIDEO_ID=self.video_id,
                       FILENAME=self.video_location,
                       CHANNEL_ID=self.channel_id,
                       CHANNEL_NAME=self.channel_name,
                       START_DATE_MONTH=str(now.month),
                       START_DATE_DAY=str(now.day),
                       START_DATE_YEAR=str(now.year),
                       START_DATE="{0}/{1}/{2}".format(now.month, now.day, now.year),
                       START_TIME=str(now.strftime("%I:%M %p")),
                       TIMEZONE=timezone if timezone is not None else '',
                       TITLE=self.title,
                       DESCRIPTION=self.description
                       ))

        return text
