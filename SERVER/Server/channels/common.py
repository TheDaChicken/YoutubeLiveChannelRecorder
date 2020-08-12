import atexit
import json
from abc import ABC, abstractmethod
from datetime import datetime
from multiprocessing import Queue
from os.path import join
from typing import Union, List
from urllib.parse import urlencode, parse_qs

from Server.definitions import RECORDING_FOLDER
from Server.encoder import FFmpegRecording
from Server.extra import GlobalHandler, DataHandler
from Server.utils.m3u8 import Media
from Server.utils.other import get_time_zone, handle_dup_filenames, mkdir_ignore_exists, try_get, get_utc_offset, \
    str_to_int
from Server.utils.parser import parse_json
from Server.utils.path import check_path_creatable, is_pathname_valid
from Server.utils.web import Response, UserAgent, CustomResponse
from Server.logger import get_logger, is_logger_initalized, initialize_worker_logger


class ChannelVideoInformation(ABC):
    """
    Default Functions Needed
    """

    @abstractmethod
    def get_start_date(self) -> datetime:
        pass

    @abstractmethod
    def get_title(self):
        pass

    @abstractmethod
    def get_live_status(self):
        pass


class ChannelBasicInformation(ABC):
    @abstractmethod
    def get_channel_name(self) -> str or None:
        pass

    @abstractmethod
    def get_best_name(self):
        pass

    @abstractmethod
    def get_channel_identifier(self) -> str or None:
        pass

    @abstractmethod
    def get_platform(self) -> str:
        pass

    @abstractmethod
    def get_channel_image(self) -> str:
        pass


class ChannelInformation(ChannelBasicInformation, ABC):
    """
    Default Functions Needed
    """

    @abstractmethod
    def get_video_information(self) -> ChannelVideoInformation:
        pass


def replace_variables(string: str, channel_info: ChannelInformation, **kwargs) -> str:
    class DataDict(dict):
        """
            Taken from and
            have been edited: https://stackoverflow.com/a/11023271
        """

        def __missing__(self, key):
            get_logger().warning(
                "No variable named \"{0}\". "
                "Replacing nothing as a save guard.".format(key))
            return ''

        def __getitem__(self, key):
            val = dict.__getitem__(self, key)
            if val is None:
                get_logger().warning(
                    "No variable named \"{0}\" in this current case. "
                    "Replacing nothing as a save guard.".format(key))
                return ''
            return val

    video_info = channel_info.get_video_information()
    start = video_info.get_start_date()
    timezone = get_time_zone()

    return string % DataDict(
        VIDEO_ID=video_info.get_video_id(),
        CHANNEL_ID=channel_info.get_channel_identifier(),
        CHANNEL_NAME=channel_info.get_channel_name(),
        DATE_MONTH=str(start.month) if start is not None else None,
        DATE_DAY=str(start.day) if start is not None else None,
        DATE_YEAR=str(start.year) if start is not None else None,
        FULL_DATE=start.strftime("%x") if start is not None else None,
        DATE_MINUS=start.strftime("%m-%d-%Y") if start is not None else None,
        TIME_12HOUR=start.strftime("%I:%M %p") if start is not None else None,
        TIME_24HOUR=start.strftime("%H:%M %p") if start is not None else None,
        TIMEZONE_NAME=start.strftime("%Z") if start is not None else None,
        TIMEZONE_FULL_NAME=timezone if timezone is not None else '[UNKNOWN]',
        EXTENSION=kwargs.get("extension"),
    )


class Channel(ABC):
    """Channel Class

    Base of all channel classes.

    """
    platform = "UNDEFINED"

    channel_identifier = None

    # 2 -> Live
    # 1 -> No Live
    # 0 -> Unable to get Stream Information or NO DATA
    # -1 -> Error
    live_status = None  # type: int

    # Video Information
    start_date = None
    video_media = None

    # VIDEO INFORMATION
    title = None

    # ENCODER ETC
    encoder_class = None  # type: FFmpeg

    def __init__(self, channel_identifier: str, global_handler: GlobalHandler, queue: Queue):
        # HANDLE LOGGER
        if is_logger_initalized() is False:
            initialize_worker_logger(queue, global_handler.get_log_level())
        self.channel_identifier = channel_identifier
        self.global_handler = global_handler
        self.encoder_class = FFmpegRecording()

    @classmethod
    def fromDICT(cls, values: dict, global_handler: GlobalHandler, queue):  # just in case
        if not ("channel_identifier" in values):
            raise ValueError("values doesn't contain \"channel_identifier\".")
        obj = cls(values.get("channel_identifier"), global_handler, queue)
        list(map(obj.__setattr__, values))
        return obj

    def createDICT(self) -> dict:
        dict_ = self.__dict__
        del dict_["global_handler"]  # don't need it. remove it
        del dict_["encoder_class"]  # don't need it. remove it
        return dict_

    def _get_hls_format_(self, manifest_url) -> Media or None:
        download_object = self.request(manifest_url)
        hls = download_object.m3u8()
        if len(hls) == 0:
            self.get_logger().critical("Unable to Parse M3U8 MANIFEST.")
            return None
        return hls.get_best_format(
            self.get_cache_yml().get_cache().get("RecordingResolution"))

    def start_recording(self, media: Media, **kwargs):
        self.start_date = datetime.now()
        recording_settings = self.get_cache_yml().get_value("RecordingSettings") or {}
        config_file_name = self.get_cache_yml().get_value(
            "FileNameFormat", (recording_settings, "recording_settings"))
        recording_path = self.get_cache_yml().get_value(
            "RecordingPath", (recording_settings, "recording_settings")) or RECORDING_FOLDER
        file_name = replace_variables(config_file_name, self.get_information(), extension='mp4')
        path_name = handle_dup_filenames(join(recording_path, file_name))
        if not check_path_creatable(recording_path) or not is_pathname_valid(path_name):
            self.get_logger().critical("Recording Path \"{0}\" is not valid.".format(recording_path))
            return False
        mkdir_ignore_exists(recording_path)
        url = "{0}?{1}".format(media.url, urlencode(kwargs)) if len(kwargs) != 0 else media.url
        if self.encoder_class.start_recording(url, path_name, headers={'User-Agent': UserAgent},
                                              input_format=media.format_name):
            return True
        self.get_logger().critical("Failed to start recording.")
        return False

    """
        Shorten As Functions
    """

    def get_logger(self):
        return get_logger(self.get_information().get_best_name())

    def get_cache_yml(self) -> DataHandler:
        return self.global_handler.get_cache_yml()

    def request(self, *args, **kwargs) -> CustomResponse:
        return self.global_handler.request(*args, **kwargs)

    """
        Abstract Methods
        Overridden in Channel's Classes
    """

    @abstractmethod
    def load_channel_data(self) -> List[Union[bool, str]]:
        pass

    @abstractmethod
    def channel_thread(self):
        pass

    @abstractmethod
    def get_information(self) -> ChannelInformation:
        pass

    def add_youtube_queue(self):
        pass

    def register_close_event(self):
        atexit.register(self.close)

    @abstractmethod
    def close(self):
        pass


class YouTubeBase(Channel, ABC):
    """
    Since YouTube Class is such a big class. Here is me putting some of the functions etc in common.py
    These Functions etc are used more than once.
    """

    # Channel
    channel_name = None  # type: str
    channel_image = None  # type: str

    # Video Information
    video_id = None
    description = None
    private_live = None
    thumbnail_url = None
    dvr_enabled = None
    heartbeat_class = None  # type: YouTubeBase.Heartbeat

    # YouTube
    youtube_api_key = None  # type: str

    # YouTube's heartbeat
    poll_delay_ms = 8000
    sequence_number = None
    broadcast_id = None
    player_context_params = None  # type: str

    live_scheduled = None  # type: bool
    scheduled_start_time = None

    # global variables
    variables = {}

    # PLAYBACK ID
    cpn = None

    """
        Only Class Functions
    """

    def _get_youtube_headers(self, time_zone=None, utc_off=None):
        time_zone = time_zone or get_time_zone() or 'America/Los_Angeles'
        utc_off = utc_off or get_utc_offset()
        return {
            "X-YouTube-Device": self.variables.get("device"),
            "X-YouTube-Page-Label": self.variables.get("page_build_label"),
            "X-YouTube-Variants-Checksum": self.variables.get("variants_checksum"),
            "X-YouTube-Page-CL": str(self.variables.get("page_cl")), "X-YouTube-Utc-Offset": str(utc_off),
            "X-YouTube-Client-Name": str(self.variables.get("client_name")) or "1",
            "X-YouTube-Client-Version": self.variables.get("client_version"),
            "X-YouTube-Time-Zone": time_zone, "X-Goog-Visitor-Id": self.variables.get("visitor_id") or '',
            "Accept": "/*/",
            "Origin": "https://www.youtube.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": "https://www.youtube.com/channel/{0}/live".format(self.channel_identifier),
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US",
            # ONLY FOR LOGGED-IN IN USERS
            # "Authorization": "(NULL)",
            # "X-YouTube-Identity-Toekn": self.variables.get("identity_token"),
            # "X-Goog-AuthUser": "0",
            # "x-origin": "https://www.youtube.com",
            # "X-Client-Data": "(NULL)",
        }

    def _get_video_info(self):
        """
        Looked at for reference:
        https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1675
        """
        url_arguments = {'html5': 1, 'video_id': self.video_id}
        if self.variables.get("ps") is not None:
            url_arguments.update({'ps': self.variables.get("ps")})
        url_arguments.update({'eurl': ''})
        url_arguments.update({'hl': 'en_US'})
        url_arguments.update({'c': "WEB"})
        if self.variables.get("cbr") is not None:
            url_arguments.update({'cbr': self.variables.get("cbr")})
        if self.variables.get("client_version") is not None:
            url_arguments.update({'cver': self.variables.get("client_version")})
        if self.variables.get("client_os") is not None:
            url_arguments.update({'cos': self.variables.get("client_os")})
        if self.variables.get("client_os_version") is not None:
            url_arguments.update({'cosver', self.variables.get("client_os_version")})
        url_arguments.update({'cpn': self.cpn})

        download_class = self.request(
            'https://www.youtube.com/get_video_info?{0}'.format(
                urlencode(url_arguments)), headers=self._get_youtube_headers())
        video_info_website = download_class.text

        video_info = parse_qs(video_info_website)
        player_response = parse_json(try_get(video_info, lambda x: x['player_response'][0], str)) or {}
        return self._parse_player_response(player_response)

    def _parse_player_response(self, player_response: dict):
        # TODO I DUNNO TO CHOOSE EITHER VIDEO OBJECT OR WHAT
        streaming_data = try_get(player_response, lambda x: x['streamingData'], dict)
        if streaming_data is None:
            return [False, "No StreamingData, Youtube bugged out!"]
        if 'licenseInfos' in streaming_data:
            license_info = streaming_data.get('licenseInfos')
            drm_families = map(lambda x: x.get('drmFamily'), license_info)
            return [False, "This live stream contains DRM and cannot be recorded.\n"
                           "DRM Families: {0}".format(', '.join(drm_families))]
        video_details = try_get(player_response, lambda x: x['videoDetails'], dict)
        manifest_url = str(try_get(player_response, lambda x: x['streamingData']['hlsManifestUrl'], str))
        if not manifest_url:
            return [False, "Unable to find HLS Manifest URL."]
        self.title = try_get(video_details, lambda x: x['title'], str)
        self.description = try_get(video_details, lambda x: x['shortDescription'], str)
        self.dvr_enabled = try_get(video_details, lambda x: x['isLiveDvrEnabled'], bool)
        return [True, self._get_hls_format_(manifest_url)]

    class Heartbeat:
        """
        Holds information from YouTube's Heartbeat
        """

        def __init__(self, code=None, status=None, reason=None, live_scheduled=False, scheduled_time=None,
                     stream_over=False):
            self.status_code = code
            self.status = status
            self.reason = reason
            self.live_scheduled = live_scheduled
            self.scheduled_time = scheduled_time
            self.stream_over = stream_over
            self.heartbeat_time = datetime.now()

        def get_status_code(self) -> int or None:
            return self.status_code

        def get_status(self) -> str or None:
            return self.status

        def get_reason(self) -> str or None:
            return self.reason

        def is_live_scheduled(self) -> bool:
            return self.live_scheduled

        def get_live_scheduled_time(self) -> datetime:
            """
            Linux Epoch (From Heartbeat) -> datetime
            """
            if self.scheduled_time is None:
                return None
            return datetime.fromtimestamp(self.scheduled_time)

        def is_stream_over(self) -> bool:
            return self.stream_over

        def get_heartbeat_time(self):
            return self.heartbeat_time

    class PrivateStream:
        def __init__(self):
            pass

    def _post_heartbeat(self, sequence_number=0) -> Heartbeat:
        time_zone = get_time_zone() or 'America/Los_Angeles'
        utc_off = get_utc_offset()

        post_data = json.dumps({
            'videoId': self.video_id, 'sequenceNumber': sequence_number,
            'context': {
                'user': {},
                'request': {
                    "consistencyTokenJars": [],
                    "internalExperimentFlags": [],
                },
                'client': {
                    'utcOffsetMinutes': utc_off,
                    'experimentIds': self.variables.get("experiment_ids") or [],
                    'deviceMake': "www",
                    'deviceModel': 'www',
                    'browserName': "Chrome", 'browserVersion': "83.0.4103.116",
                    "osName": "Windows", "osVersion": "10.0",
                    "clientName": "WEB", "clientVersion":
                        self.variables.get("client_version") or '2.20200626.03.00',
                    # DEFAULT VALUES IF BROKEN AFTER THE OR*
                    "hl": "en",
                    "gl": "US",
                    "timeZone": time_zone,
                },
                'activePlayers': [
                    {'playerContextParams': self.player_context_params},
                ]
            }, 'cpn': self.cpn, 'heartbeatToken': "",
            "heartbeatRequestParams": {
                "heartbeatChecks":
                    ["HEARTBEAT_CHECK_TYPE_LIVE_STREAM_STATUS"]
            }
        }).replace(' ', '').encode('utf-8')

        headers = self._get_youtube_headers()
        headers.update({"Content-Type": "application/json"})

        response = self.request("https://www.youtube.com/youtubei/v1/player/heartbeat?{0}".format(urlencode({
            'alt': 'json',
            'key': self.youtube_api_key,
        })), request_method='POST', headers=headers, data=post_data)

        if response.text is None:
            return YouTubeBase.Heartbeat(code=0)

        json_reply = response.json()
        playability_status = try_get(json_reply, lambda x: x['playabilityStatus'], dict)
        if playability_status is None and response.status_code == 200:
            self.get_logger().debug("Unable to find playability status in heartbeat!")
            return YouTubeBase.Heartbeat(code=-1)

        self.get_logger().debug('FROM YOUTUBE -> {0}'.format(
            playability_status or json_reply or response.text))

        if response.status_code != 200:
            return YouTubeBase.Heartbeat(code=-1)

        return self._playability_status(playability_status)

    def _playability_status(self, playability_status) -> Heartbeat:
        def get_poll_delay_ms() -> int:
            poll_delay_ms = try_get(
                live_stream_renderer, lambda x: x['pollDelayMs'], str)
            if poll_delay_ms:
                return int(poll_delay_ms)
            elif self.poll_delay_ms:
                return self.poll_delay_ms
            else:
                return 9500

        def create_object():
            return self.Heartbeat(code=code, status=status, reason=reason, live_scheduled=live_scheduled,
                                  scheduled_time=scheduled_start_time, stream_over=stream_over)

        code = 0
        live_scheduled = False
        scheduled_start_time = None
        stream_over = None

        live_stream_renderer = try_get(
            playability_status, lambda x: x['liveStreamability']['liveStreamabilityRenderer'], dict)
        if live_stream_renderer:
            self.poll_delay_ms = get_poll_delay_ms()
            video_id = try_get(live_stream_renderer, lambda x: x['videoId'], str)
            if video_id is not None and video_id != self.video_id:
                self.add_youtube_queue()  # just in case something happens.
                self.video_id = video_id
        offline_renderer = try_get(live_stream_renderer, lambda x: x['offlineSlate']['liveStreamOfflineSlateRenderer'],
                                   dict)  # type: dict
        if offline_renderer:
            scheduled_start_time = try_get(offline_renderer, lambda x: x['scheduledStartTime'], str)
            if scheduled_start_time:
                live_scheduled = True
                scheduled_start_time = str_to_int(scheduled_start_time)

        if try_get(live_stream_renderer, lambda x: x['displayEndscreen'], bool):
            stream_over = True

        status = try_get(playability_status, lambda x: x['status'], str)  # type: str
        reason = try_get(playability_status, lambda x: x['reason'], str)  # type: str
        if status:  # Sometimes status is removed and causes an error.
            if "OK" == status.upper():
                code = 2
                return create_object()
            if "STOP" == status.upper():
                stream_over = True
                code = 1
                return create_object()
            if "ERROR" == status.upper():
                code = 0
                return create_object()
            if "LIVE_STREAM_OFFLINE" in status.upper():
                code = 1
                return create_object()
            if "UNPLAYABLE" in status.upper():
                code = 1
                stream_over = True
                return create_object()
        code = 0
        return create_object()
