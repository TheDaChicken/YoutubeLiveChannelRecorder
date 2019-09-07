import json
import os
import re
import traceback
from datetime import datetime
from multiprocessing.managers import Namespace
from threading import Thread
from time import sleep

from . import set_global_youtube_variables, generate_cpn
from .communityPosts import is_live_sponsor_only_streams
from .heatbeat import is_live
from ..log import verbose, stopped, warning, info, crash_warning
from ..template.template_channelClass import ChannelInfo_template
from ..utils.other import try_get, get_format_from_data, get_highest_thumbnail
from ..utils.parser import parse_json
from ..utils.web import download_website, download_image, download_m3u8_formats
from ..utils.windowsNotification import show_windows_toast_notification
from ..utils.youtube import get_yt_player_config, get_endpoint_type


class ChannelInfo(ChannelInfo_template):
    """

    Class that holds channel information and functions related to the information.

    # Stream Data.
    :type start_date: datetime.datetime
    :type description: str
    :type privateStream: bool
    :type sponsor_only_stream: bool

    # USED FOR HOLDING THUMBNAILS
    :type thumbnail_url: str
    :type thumbnail_location: str

    # USED IN HEARTBEAT TO BE SHOWN ON CLIENT.
    :type live_scheduled: bool
    :type live_scheduled_time: str

    # Server-type Variables
    :type live_streaming, bool
    :type recording_status: str
    :type SharedVariables: Namespace
    :type sharedCookies: Value

    # HEARTBEAT Variables
    :type pollDelayMs: int
    :type sequence_number: int
    :type broadcast_id: str
    :type last_heartbeat: datetime.datetime

    # USER ACCOUNT
    :type sponsor_on_channel: bool

    # PER-CHANNEL YOUTUBE VARIABLES
    :type cpn: str
    """

    # NEEDED FOR EVERY CHANNEL CLASS.
    platform = 'YOUTUBE'

    # USED FOR SERVER VARIABLES
    recording_status = None
    SharedVariables = False
    sharedCookies = False
    queue_holder = None

    # USED FOR YOUTUBE'S HEARTBEAT SYSTEM AND IS NOT A GLOBAL VALUE
    pollDelayMs = 8000
    sequence_number = 0
    broadcast_id = None
    last_heartbeat = None

    # User
    sponsor_on_channel = False

    # Data about the stream. (THIS IS USED TO SHOW THE VARIABLES IN THIS CLASS)
    video_id = None
    title = None
    description = None
    start_date = None
    privateStream = False
    sponsor_only_stream = False

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

    def loadVideoData(self, video_id=None):
        if video_id is not None:
            website_string = download_website("https://www.youtube.com/watch?v={0}".
                                              format(video_id), SharedVariables=self.SharedVariables)
            self.video_id = video_id
        else:
            website_string = download_website("https://www.youtube.com/channel/{0}/live".
                                              format(self.channel_id), SharedVariables=self.SharedVariables)
        if website_string is None:
            return [False, "Failed getting Youtube Data from the internet! "
                           "This means there is no good internet available!"]
        if website_string == 404:
            return [False, "Failed getting Youtube Data! \"{0}\" doesn't exist as a channel id!".format(
                self.channel_id)]

        endpoint_type = get_endpoint_type(website_string)
        if endpoint_type:
            if endpoint_type == 'browse':
                array = re.findall('property="og:title" content="(.+?)"', website_string)
                if array:
                    channel_name = array[0]
                    warning("{0} has the live stream "
                            "currently unlisted or private, or only for members. "
                            "Using safeguard. This may not be the best to leave on.\n".format(channel_name))
                    self.channel_name = channel_name
                    self.video_id = None
                    self.privateStream = True
            else:
                if not endpoint_type == 'watch':
                    warning("Unrecognized endpoint type. Endpoint Type: {0}.".format(endpoint_type))
                verbose("Getting Video ID.")
                yt_player_config = try_get(get_yt_player_config(website_string), lambda x: x['args'], dict)
                player_response = parse_json(try_get(yt_player_config, lambda x: x['player_response'], str))
                videoDetails = try_get(player_response, lambda x: x['videoDetails'], dict)
                if yt_player_config and videoDetails:
                    if "isLiveContent" in videoDetails and \
                            videoDetails['isLiveContent'] and \
                            ("isLive" in videoDetails or "isUpcoming" in videoDetails):
                        self.channel_name = try_get(videoDetails, lambda x: x['author'], str)
                        self.video_id = try_get(videoDetails, lambda x: x['videoId'], str)
                        self.privateStream = False
                        if not self.channel_id:
                            self.channel_id = try_get(videoDetails, lambda x: x['channelId'], str)
                    else:
                        return [False, "Found a stream, the stream seemed to be a non-live stream."]
                else:
                    return [False, "Unable to get yt player config, and videoDetails."]

                if not self.privateStream:
                    # TO AVOID REPEATING REQUESTS.
                    if player_response:
                        # playabilityStatus is legit heartbeat all over again..
                        playabilityStatus = try_get(player_response, lambda x: x['playabilityStatus'], dict)
                        status = try_get(playabilityStatus, lambda x: x['status'], str)
                        reason = try_get(playabilityStatus, lambda x: x['reason'], str)
                        if playabilityStatus and status:
                            if 'OK' in status:
                                if reason and 'ended' in reason:
                                    return [False, reason]
                                self.live_streaming = True  # UPDATE SERVER VARIABLE
                                streamingData = try_get(player_response, lambda x: x['streamingData'], dict)
                                if streamingData:
                                    if 'licenseInfos' in streamingData:
                                        licenseInfo = streamingData.get('licenseInfos')
                                        drmFamilies = map(lambda x: x.get('drmFamily'), licenseInfo)
                                        return [False, "This live stream contains DRM and cannot be recorded.\n"
                                                       "DRM Families: {0}".format(', '.join(drmFamilies))]
                                    manifest_url = str(
                                        try_get(streamingData, lambda x: x['hlsManifestUrl'], str))
                                    if not manifest_url:
                                        return [False, "Unable to find HLS Manifest URL."]
                                    formats = download_m3u8_formats(manifest_url)
                                    if formats is None or len(formats) is 0:
                                        return [False, "There were no formats found! Even when the streamer is live."]
                                    f = get_format_from_data(
                                        formats, self.cachedDataHandler.getValue('recordingResolution'))
                                    if not videoDetails:
                                        videoDetails = try_get(player_response, lambda x: x['videoDetails'], dict)
                                    thumbnails = try_get(videoDetails, lambda x: x['thumbnail']['thumbnails'], list)
                                    if thumbnails:
                                        self.thumbnail_url = get_highest_thumbnail(thumbnails)
                                    self.StreamInfo = {
                                        'stream_resolution': '{0}x{1}'.format(str(f['width']), str(f['height'])),
                                        'HLSManifestURL': manifest_url,
                                        'DashManifestURL': str(
                                            try_get(player_response, lambda x: x['streamingData']['dashManifestUrl'],
                                                    str)),
                                        'HLSStreamURL': f['url'],
                                        'title': try_get(videoDetails, lambda x: x['title'], str),
                                        'description': videoDetails['shortDescription'],
                                    }
                                else:
                                    return [False, "No StreamingData, YouTube bugged out!"]
                            if 'live_stream_offline' in status:
                                self.live_streaming = False  # UPDATE SERVER VARIABLE

        if not self.privateStream:
            set_global_youtube_variables(html_code=website_string)

        # ONLY WORKS IF LOGGED IN
        self.sponsor_on_channel = self.get_sponsor_channel(html_code=website_string)

        self.cpn = generate_cpn()
        return [True, "OK"]

    def updateVideoData(self):
        """

        This is used to grab video information from the YouTube Channel Live site, like video_id,
        to check if already live, and the stream url if already live.
        Everything else would use heartbeat and get video info url.

        :return: Nothing. It edits the class.
        """
        verbose("Getting New Video ID.")

        website_string = download_website("https://www.youtube.com/channel/{0}/live".
                                          format(self.channel_id), SharedVariables=self.SharedVariables)
        if website_string is None:
            return [False, "Failed getting Video Data from the internet! "
                           "This means there is no good internet available!"]
        if website_string == 404:
            return [False, "Failed getting Video Data! \""
                           "{0}\" doesn't exist as a channel id!".format(self.channel_id)]

        endpoint_type = get_endpoint_type(website_string)

        if endpoint_type:
            if endpoint_type == 'browse':
                self.privateStream = True
                self.video_id = None
            else:
                if not endpoint_type == 'watch':
                    warning("Unrecognized endpoint type. Endpoint Type: {0}.".format(endpoint_type))
                yt_player_config = try_get(get_yt_player_config(website_string), lambda x: x['args'], dict)
                player_response = parse_json(try_get(yt_player_config, lambda x: x['player_response'], str))
                videoDetails = try_get(player_response, lambda x: x['videoDetails'], dict)
                if yt_player_config and videoDetails:
                    if "isLiveContent" in videoDetails and \
                            videoDetails['isLiveContent'] and \
                            ("isLive" in videoDetails or "isUpcoming" in videoDetails):
                        self.video_id = try_get(videoDetails, lambda x: x['videoId'], str)
                        self.privateStream = False
                        if not self.video_id:
                            return [False, "Unable to find video id in the YouTube player config!"]
                    else:
                        return [False, "Found a stream, the stream seemed to be a non-live stream"]
                else:
                    self.privateStream = True

                if not self.privateStream:
                    # TO AVOID REPEATING REQUESTS.
                    if player_response:
                        # playabilityStatus is legit heartbeat all over again..
                        playabilityStatus = try_get(player_response, lambda x: x['playabilityStatus'], dict)
                        status = try_get(playabilityStatus, lambda x: x['status'], str)
                        reason = try_get(playabilityStatus, lambda x: x['reason'], str)
                        if playabilityStatus and status:
                            if 'OK' in status:
                                if reason and 'ended' in reason:
                                    return [False, reason]
                                streamingData = try_get(player_response, lambda x: x['streamingData'], dict)
                                if streamingData:
                                    if 'licenseInfos' in streamingData:
                                        licenseInfo = streamingData.get('licenseInfos')
                                        drmFamilies = map(lambda x: x.get('drmFamily'), licenseInfo)
                                        return [False, "This live stream contains DRM and cannot be recorded.\n"
                                                       "DRM Families: {0}".format(', '.join(drmFamilies))]
                                    manifest_url = str(
                                        try_get(streamingData, lambda x: x['hlsManifestUrl'], str))
                                    if not manifest_url:
                                        return [False, "Unable to find HLS Manifest URL."]
                                    formats = download_m3u8_formats(manifest_url)
                                    if formats is None or len(formats) is 0:
                                        return [False, "There were no formats found! Even when the streamer is live."]
                                    f = get_format_from_data(formats, None)
                                    if not videoDetails:
                                        videoDetails = try_get(player_response, lambda x: x['videoDetails'], dict)
                                    thumbnails = try_get(videoDetails, lambda x: x['thumbnail']['thumbnails'], list)
                                    if thumbnails:
                                        self.thumbnail_url = get_highest_thumbnail(thumbnails)
                                    self.StreamInfo = {
                                        'stream_resolution': '{0}x{1}'.format(str(f['width']), str(f['height'])),
                                        'HLSManifestURL': manifest_url,
                                        'DashManifestURL': str(
                                            try_get(player_response, lambda x: x['streamingData']['dashManifestUrl'],
                                                    str)),
                                        'HLSStreamURL': f['url'],
                                        'title': try_get(videoDetails, lambda x: x['title'], str),
                                        'description': videoDetails['shortDescription'],
                                    }
                                else:
                                    return [False, "No StreamingData, YouTube bugged out!"]

        return [True, "OK"]

    def close_recording(self):
        if self.EncoderClass is not None:
            self.EncoderClass.stop_recording()
            self.EncoderClass = None

    def get_sponsor_channel(self, html_code=None):
        from .. import is_google_account_login_in
        if is_google_account_login_in():
            verbose("Checking if account sponsored {0}.".format(self.channel_name))
            if html_code is None:
                html_code = download_website("https://www.youtube.com/channel/{0}/live".format(self.channel_id),
                                             SharedVariables=self.SharedVariables)
                if html_code is None:
                    return None
            html_code = str(html_code)
            array = re.findall('/channel/{0}/membership'.format(self.channel_id), html_code)
            if array:
                return True
            return False
        return False

    def add_video_temp_youtube_queue(self):
        # Adds to the temp upload list.
        if self.video_id in self.video_list:
            temp_dict = self.video_list.get(self.video_id)  # type: dict
            if 'file_location' in temp_dict:
                file_location = temp_dict['file_location']  # type: list
                file_location.append(self.video_location)
        else:
            temp_youtube_stream = self.StreamInfo.copy()
            temp_youtube_stream.update({
                'start_date': self.start_date
            })
            self.video_list.update({
                self.video_id: {
                    'video_id': self.video_id, 'video_data': temp_youtube_stream, 'channel_data': {
                        'channel_name': self.channel_name,
                        'channel_id': self.channel_id,
                    },
                    'file_location': [self.video_location, ],
                    'thumbnail_location': self.thumbnail_location}
            })
            del temp_youtube_stream

        # Write YouTube Stream info to json.
        with open("{3} - '{4}' - {0}-{1}-{2}.json".format(self.start_date.month, self.start_date.day,
                                                          self.start_date.year,
                                                          self.channel_name, self.video_id), 'w',
                  encoding='utf-8') as f:
            json.dump({
                'video_id': self.video_id, 'video_data': self.StreamInfo, 'channel_data': {
                    'channel_name': self.channel_name,
                    'channel_id': self.channel_id,
                },
            }, f, ensure_ascii=False, indent=4)

    def start_recording(self):
        def getYoutubeStreamInfo(recordingHeight=None):
            """

            Gets the stream info from channelClass.

            Looked at for reference:
            https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1675

            :type recordingHeight: str, int, None
            """
            try:
                from urllib.parse import urlencode, parse_qs
                from urllib.request import urlopen
            except ImportError:
                parse_qs = None  # Fixes a random PyCharm warning.
                urlencode = None
                stopped("Unsupported version of Python. You need Version 3 :<")

            url_arguments = {'html5': 1, 'video_id': self.video_id}
            from . import client_name, client_version, ps, sts, cbr, client_os, client_os_version
            if ps is not None:
                url_arguments.update({'ps': ps})
            url_arguments.update({'eurl': ''})
            url_arguments.update({'hl': 'en_US'})
            if sts is not None:
                url_arguments.update({'sts': sts})
            if client_name is not None:
                url_arguments.update({'c': client_name})
            if cbr is not None:
                url_arguments.update({'cbr': cbr})
            if client_version is not None:
                url_arguments.update({'cver': client_version})
            if client_os is not None:
                url_arguments.update({'cos': client_os})
            if client_os_version is not None:
                url_arguments.update({'cosver': client_os_version})
            if self.cpn is not None:
                url_arguments.update({'cpn': self.cpn})

            video_info_website = download_website(
                'https://www.youtube.com/get_video_info?{0}'.format(
                    urlencode(url_arguments)))
            if video_info_website is None:
                return video_info_website
            video_info = parse_qs(video_info_website)
            player_response = parse_json(try_get(video_info, lambda x: x['player_response'][0], str))
            video_details = try_get(player_response, lambda x: x['videoDetails'], dict)

            if player_response:
                if "streamingData" not in player_response:
                    warning("No StreamingData, Youtube bugged out!")
                    return None
                manifest_url = str(try_get(player_response, lambda x: x['streamingData']['hlsManifestUrl'], str))
                if not manifest_url:
                    warning("Unable to find HLS Manifest URL.")
                    return None
                formats = download_m3u8_formats(manifest_url)
                if formats is None or len(formats) is 0:
                    warning("There were no formats found! Even when the streamer is live.")
                    return None
                f = get_format_from_data(formats, recordingHeight)
                youtube_stream_info = {
                    'stream_resolution': '{0}x{1}'.format(str(f['width']), str(f['height'])),
                    'HLSManifestURL': manifest_url,
                    'DashManifestURL': str(
                        try_get(player_response, lambda x: x['streamingData']['dashManifestUrl'], str)),
                    'HLSStreamURL': f['url'],
                    'title': try_get(video_details, lambda x: x['title'], str),
                    'description': try_get(video_details, lambda x: x['shortDescription'], str),
                    'video_id': self.video_id
                }
                return youtube_stream_info
            return None

        if not self.StreamInfo:
            self.recording_status = "Getting Youtube Stream Info."
            self.StreamInfo = getYoutubeStreamInfo(
                recordingHeight=self.cachedDataHandler.getValue('recordingResolution'))

        if self.StreamInfo:
            self.recording_status = "Starting Recording."

            filename = self.create_filename(self.video_id)
            self.video_location = os.path.join("RecordedStreams", '{0}.mp4'.format(filename))

            ok_ = self.EncoderClass.start_recording(self.StreamInfo['HLSStreamURL'], self.video_location)
            if not ok_:
                self.recording_status = "Failed To Start Recording."
                show_windows_toast_notification("Live Recording Notifications",
                                                "Failed to start record for {0}".format(self.channel_name))
            if ok_:
                self.start_date = datetime.now()

                self.recording_status = "Recording."

                show_windows_toast_notification("Live Recording Notifications",
                                                "{0} is live and is now recording. \nRecording at {1}".format(
                                                    self.channel_name, self.StreamInfo['stream_resolution']))

                if self.cachedDataHandler:
                    if self.cachedDataHandler.getValue(
                            'DownloadThumbnail') is True and self.privateStream is not True:
                        thread = Thread(target=self.download_thumbnail, name=self.channel_name)
                        thread.daemon = True  # needed control+C to work.
                        thread.start()

                self.add_video_temp_youtube_queue()

                if self.TestUpload:
                    sleep(10)
                    self.EncoderClass.stop_recording()
                    return True

            return ok_
        else:
            self.recording_status = "Unable to get Youtube Stream Info."
            self.live_streaming = None
            warning("Unable to get Youtube Stream Info from this stream: ")
            warning("VIDEO ID: {0}".format(str(self.video_id)))
            warning("CHANNEL ID: {0}".format(str(self.channel_id)))
            return None

    def stop_recording(self):
        while True:
            if self.EncoderClass.last_frame_time:
                last_seconds = (datetime.now() - self.EncoderClass.last_frame_time).total_seconds()
                # IF BACK LIVE AGAIN IN THE MIDDLE OF WAITING FOR NON ACTIVITY.
                if self.live_streaming is True:
                    break
                if last_seconds > 10:
                    self.EncoderClass.stop_recording()
                    break
            sleep(1)

    def channel_thread(self, TestUpload=False):
        """

        Checks for streams, records them if live.
        Best under a thread to allow multiple channels.

        """

        if self.live_streaming:
            ok = self.start_recording()
            if ok:
                if TestUpload:
                    self.add_youtube_queue()
                    stopped("")

        alreadyChecked = True
        self.TestUpload = TestUpload

        # noinspection PyBroadException
        try:
            while self.stop_heartbeat is False:
                # LOOP
                self.live_streaming = self.is_live(alreadyChecked=alreadyChecked)

                # HEARTBEAT ERROR
                if self.live_streaming is 1:
                    # IF CRASHED.
                    info("Error on Heartbeat on {0}! Trying again ...".format(self.channel_name))
                    sleep(1)

                # INTERNET OFFLiNE.
                if self.live_streaming is None:
                    warning("INTERNET OFFLINE")
                    sleep(2.4)

                # FALSE
                if self.live_streaming is False:
                    if self.EncoderClass.running is True:
                        x = Thread(target=self.stop_recording)
                        x.daemon = False
                        x.start()

                    if self.sponsor_on_channel:
                        verbose("Reading Community Posts on {0}.".format(self.channel_name))
                        # NOTE this edits THE video id when finds stream.
                        self.live_streaming = self.is_live_sponsor_only_streams()
                        if not self.live_streaming:
                            if self.live_streaming is None:
                                warning("INTERNET OFFLINE")
                                sleep(2.52)
                            else:
                                info("{0}'s channel live streaming is currently private/unlisted!".format(
                                    self.channel_name))
                                info("Checked Community Posts for any Sponsor Only live Streams. Didn't Find "
                                     "Anything!")
                                sleep(self.pollDelayMs / 1000)
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

                # LIVE
                if self.live_streaming is True:
                    if not self.EncoderClass.running:
                        x = Thread(target=self.start_recording)
                        x.daemon = False
                        x.start()
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
        return boolean_live

    def is_live_sponsor_only_streams(self):
        boolean_live = is_live_sponsor_only_streams(self, SharedVariables=self.SharedVariables)
        self.live_streaming = boolean_live  # UPDATE SERVER VARIABLE
        return boolean_live

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
            path = os.path.join("RecordedStreams", '{0}.mp4'.format(file_name))
            if not os.path.isfile(path):
                verbose("Found Good Filename.")
                return file_name
            amount += 1

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
