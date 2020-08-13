import re
import traceback
from datetime import datetime
from time import sleep
from typing import Union, List, Any
from urllib.parse import urlencode, parse_qs

from Server.channels.common import ChannelInformation, ChannelVideoInformation, YouTubeBase, \
    ChannelBasicInformation
from Server.extra import GlobalHandler
from Server.utils.m3u8 import Media
from Server.utils.other import try_get, get_utc_offset, get_time_zone
from Server.utils.parser import parse_json
from Server.utils.youtube import get_endpoint_type, get_yt_player_config, get_yt_cfg, get_yt_web_player_config, \
    generate_cpn, get_yt_initial_data


class YouTubeVideoInformation(ChannelVideoInformation):
    def __init__(self, channel: YouTubeBase):
        self.video_id = channel.video_id
        self.title = channel.title
        self.description = channel.description
        self.private_stream = channel.private_live
        self.start_date = channel.start_date
        self.format = channel.video_media
        self.live_status = channel.live_status
        self.heartbeat_class = channel.heartbeat_class

    def get_start_date(self) -> datetime:
        return self.start_date

    def get_video_id(self) -> str:
        return self.video_id

    def get_private_stream(self) -> bool:
        return self.private_stream

    def get_title(self) -> str:
        return self.title

    def get_formats(self) -> Media:
        return self.format

    def get_live_status(self) -> int:
        return self.live_status

    def is_scheduled(self) -> bool:
        if not isinstance(self.heartbeat_class, YouTubeBase.Heartbeat):
            return False
        return self.heartbeat_class.is_live_scheduled()

    def get_lived_scheduled_time(self):
        if not isinstance(self.heartbeat_class, YouTubeBase.Heartbeat):
            return None
        return self.heartbeat_class.get_live_scheduled_time()

    def get_last_heartbeat(self):
        if not isinstance(self.heartbeat_class, YouTubeBase.Heartbeat):
            return None
        return self.heartbeat_class.get_heartbeat_time()


class YouTubeBasicInformation(ChannelBasicInformation):
    def __init__(self):
        self.channel_identifier = None
        self.channel_name = None
        self.channel_image = None

    def get_platform(self) -> str:
        return "YOUTUBE"

    def get_channel_identifier(self) -> str:
        return self.channel_identifier

    def get_channel_name(self) -> str or None:
        return self.channel_name

    def get_best_name(self) -> str:
        """
        Returns available name
        """
        return self.channel_name or self.channel_identifier

    def get_channel_image(self) -> str:
        return self.channel_image


class YouTubeChannelInformation(YouTubeBasicInformation, ChannelInformation):
    def __init__(self):
        super().__init__()
        self.video_information = None

    @staticmethod
    def from_base(channel: YouTubeBase, video_information: YouTubeVideoInformation):
        info = YouTubeChannelInformation()
        info.channel_identifier = channel.channel_identifier
        info.channel_name = channel.channel_name
        info.channel_image = channel.channel_image
        info.video_information = video_information
        return info

    def get_video_information(self) -> YouTubeVideoInformation:
        return self.video_information


class YouTubeChannel(YouTubeBase):
    """YouTube Channel Class
    """
    platform = "YOUTUBE"

    # Channel Information
    private_live = None  # type: bool

    # global variables
    variables = {}

    live_status = None

    last_heartbeat = None

    def __init__(self, channel_identifier: str, global_handler, queue):
        super().__init__(channel_identifier, global_handler, queue)
        self.private_live = False
        self.dvr_enabled = False
        self.live_scheduled = False
        self.poll_delay_ms = 8000

    def load_channel_data(self) -> List[Union[bool, str]]:
        url = "https://www.youtube.com/channel/{0}/live".format(self.channel_identifier)
        headers = {"sec-fetch-dest": "document", "sec-fetch-mode": "navigate", "sec-fetch-site": "same-origin",
                   "sec-fetch-user": "?1", "upgrade-insecure-requests": "1", "accept": "text/html"}
        with self.request(url, headers=headers) as website_object:
            if website_object.status_code == 404:
                return [False, "Failed getting Youtube Data! \"{0}\" doesn't exist as a channel id!".format(
                    self.channel_identifier)]
            elif website_object.text is None:
                return [False, "Failed getting Youtube Data from the internet! "
                               "This means there is no good internet available!"]
            website_string = website_object.text
            with open('html.html', 'w', encoding='utf-8') as f:
                f.write(website_string)
            endpoint_type = get_endpoint_type(website_string)
            if endpoint_type and endpoint_type == 'browse':
                channel_name = try_get(re.findall(r'property="og:title" content="(.+?)"', website_string),
                                       lambda x: x[0],
                                       str)
                if channel_name:
                    self.get_logger().warning(
                        "{0} has the live stream currently unlisted or private. "
                        "Using safeguard. This may not be the best to leave on.\n".format(
                            channel_name))
                    self.channel_name = channel_name
                    self.video_id = None
                    self.private_live = True
                    self.live_status = 0
            else:
                if not endpoint_type == 'watch':
                    if endpoint_type is None:
                        self.get_logger().warning("Unable to find endpoint type.")
                    else:
                        self.get_logger().warning(
                            "Unrecognized endpoint type. Endpoint Type: {0}.".format(endpoint_type))
                self.get_logger().debug("Getting Video ID.")
                yt_player_config = get_yt_player_config(website_string)
                self.youtube_api_key = try_get(yt_player_config, lambda x: x['args']['innertube_api_key'], str)
                player_response = parse_json(try_get(yt_player_config, lambda x: x['args']['player_response'], str))
                video_details = try_get(player_response, lambda x: x['videoDetails'], dict)
                if yt_player_config and video_details:
                    if "isLiveContent" in video_details and \
                            video_details['isLiveContent'] and \
                            ("isLive" in video_details or "isUpcoming" in video_details):
                        self.channel_name = try_get(video_details, lambda x: x['author'], str)
                        self.video_id = try_get(video_details, lambda x: x['videoId'], str)
                        self.private_live = False
                        if not self.channel_identifier:
                            self.channel_identifier = try_get(video_details, lambda x: x['channelId'], str)
                    else:
                        return [False, "Found a watchable YouTube content, the stream seemed to be a non-live stream."]
                else:
                    return [False, "Unable to get yt player config, and videoDetails."]
                contents = try_get(get_yt_initial_data(website_string),
                                   lambda x: x['contents']['twoColumnWatchNextResults']['results']['results'][
                                       'contents'], list)
                video_secondary_info = try_get(
                    [content for content in contents if content.get("videoSecondaryInfoRenderer") is not None],
                    lambda x: x[0], dict).get("videoSecondaryInfoRenderer")
                channel_image_formats = try_get(
                    video_secondary_info, lambda x: x['owner']['videoOwnerRenderer']['thumbnail']['thumbnails'], list)
                if channel_image_formats is not None:
                    self.channel_image = max(channel_image_formats, key=lambda x: x.get("height")).get("url")
                self.get_youtube_variables(website_string)
                if not self.private_live and player_response:
                    # TO AVOID REPEATING REQUESTS.
                    playability_status = try_get(player_response, lambda x: x['playabilityStatus'], dict)
                    status = try_get(playability_status, lambda x: x['status'], str)  # type: str
                    reason = try_get(playability_status, lambda x: x['reason'], str)  # type: str
                    if playability_status and status:
                        self.get_logger().debug('FROM YOUTUBE -> {0}'.format(playability_status))
                        if 'OK' in status.upper():
                            if reason and 'ended' in reason:
                                return [False, reason]
                            result, message = self._parse_player_response(player_response)
                            if isinstance(message, Media):
                                self.video_media = message
                        self.player_context_params = try_get(playability_status, lambda x: x['contextParams'], str)
                        self.heartbeat_class = self._playability_status(playability_status)
                        self.live_status = self.heartbeat_class.get_status_code()

            self.cpn = generate_cpn()
            self.sequence_number = 0
            return [True, "a"]

    def get_youtube_variables(self, website_string: str):
        yt_cfg = get_yt_cfg(website_string)
        # Get YouTube variables page build label etc

        self.variables.update({
            "page_build_label": try_get(yt_cfg, lambda x: x['PAGE_BUILD_LABEL'], str),
            "identity_token": try_get(yt_cfg, lambda x: x['XSRF_TOKEN'], str),
            "client_name": try_get(yt_cfg, lambda x: x['INNERTUBE_CONTEXT_CLIENT_NAME'], int),
            "client_version": try_get(yt_cfg, lambda x: x['INNERTUBE_CONTEXT_CLIENT_VERSION'], str),
            "visitor_id": try_get(yt_cfg, lambda x: x['VISITOR_DATA'], str),
            "variants_checksum": try_get(yt_cfg, lambda x: x['VARIANTS_CHECKSUM'], str),
            "device": "cbr=Chrome&cbrver=83.0.4103.116&ceng=WebKit&cengver=537.36&cos=Windows&cosver=10.0"
            # TODO CHANGE THIS WHEN BROWSER IS CHANGED OR FIND A WAY TO GET THAT FROM GOOGLE ^^^
        })
        yt_web_config = get_yt_web_player_config(website_string)
        expremients_ids_strings = try_get(yt_web_config, lambda x: x['serializedExperimentIds'], str)
        if not expremients_ids_strings:
            self.get_logger().warning("Unable to find {0}.".format("serializedExperimentIds"))
        else:
            self.variables['experiment_ids'] = list(map(lambda x: int(x), expremients_ids_strings.split(',')))

    def is_live(self) -> YouTubeBase.Heartbeat or YouTubeBase.PrivateStream:
        if self.private_live:
            return YouTubeBase.PrivateStream()
        try:
            result = self._post_heartbeat(sequence_number=self.sequence_number)
            if result.get_status_code() > 0:
                self.sequence_number += 1
            self.last_heartbeat = result
            return result
        except Exception:
            self.get_logger().error(traceback.format_exc())

    def close(self):
        self.encoder_class.stop_recording()

    def wait_poll(self):
        sleep(self.poll_delay_ms / 1000)

    def handle_status_one(self):
        if self.heartbeat_class.is_stream_over():
            self.get_logger().info("Live stream is now over! Getting New Video ID.")
            self.load_channel_data()
            self.poll_delay_ms = 1000
        else:
            if self.heartbeat_class.is_live_scheduled():
                time_obj = self.heartbeat_class.get_live_scheduled_time()
                self.get_logger().info("Scheduled For: {0}.".format(time_obj.strftime("%x %I:%M %p")))
            else:
                self.get_logger().info("{0} is not live!".format(self.channel_name))
            self.poll_delay_ms = self.heartbeat_class.get_poll_delay()

    def handle_status_second(self):
        if self.encoder_class.is_running() is False:
            result, message = self._get_video_info()
            if isinstance(message, Media):
                self.video_media = message
                self.start_recording(self.video_media, cpn=self.cpn)
            elif isinstance(message, str):
                self.get_logger().warning(message)

    def handle_status_zero(self):
        self.get_logger().warning("No Data from YouTube. This could be because there is no internet!")
        self.poll_delay_ms = 3500

    def handle_status_negative(self):
        self.get_logger().critical("Error on Heartbeat.")
        self.poll_delay_ms = 3500

    def channel_thread(self):
        if self.live_status == 2:
            if self.video_media:
                self.start_recording(self.video_media, cpn=self.cpn)
        self.wait_poll()

        while True:
            result = self.is_live()
            if isinstance(result, YouTubeBase.PrivateStream):
                self.heartbeat_class = None
                self.load_channel_data()
                self.poll_delay_ms = 10000
            elif isinstance(result, YouTubeBase.Heartbeat):
                self.heartbeat_class = result
                self.live_status = self.heartbeat_class.get_status_code()
                function_list = {
                    -1: self.handle_status_negative,
                    0: self.handle_status_zero,
                    1: self.handle_status_one,
                    2: self.handle_status_second,
                }
                if self.live_status == 1 and self.encoder_class.is_running() is True:
                    # Always stop the recording when it's offline.
                    self.encoder_class.stop_recording()
                function_list.get(self.live_status)()
            self.wait_poll()

    def get_information(self) -> YouTubeChannelInformation:
        video = YouTubeVideoInformation(self)
        return YouTubeChannelInformation.from_base(self, video)

    @staticmethod
    def search_channel(global_handler: GlobalHandler, query: str) -> Union[bool, Any]:
        def format_contents(content: dict):
            if "channelRenderer" in content:
                channel = content.get("channelRenderer")  # type: dict
                image_formats = try_get(channel, lambda x: x['thumbnail']['thumbnails'], list)
                channel_image = None
                if image_formats is not None:
                    channel_image = "https:{0}".format(max(image_formats, key=lambda x: x.get("height")).get("url"))
                format_dict = {
                    'channel_identifier': try_get(channel, lambda x: x['channelId'], str),
                    'channel_name': try_get(channel, lambda x: x['title']['simpleText'], str),
                    'follower_count': try_get(channel, lambda x: x['subscriberCountText']['simpleText'], str),
                    'channel_image': channel_image,
                    'platform': 'YOUTUBE'
                }
                return format_dict
            return None

        response = global_handler.request(
            "https://www.youtube.com/results?{0}".format(urlencode({'search_query': query, 'sp': 'EgIQAg%3D%3D'})))
        youtube_initial_data = get_yt_initial_data(response.text)
        if youtube_initial_data is None:
            return [False, 'Unable to find YouTube initial data.']
        contents = try_get(youtube_initial_data,
                           lambda x: x['contents']['twoColumnSearchResultsRenderer']['primaryContents'][
                               'sectionListRenderer']['contents'], list)
        item_section = try_get(
            [content for content in contents if content.get("itemSectionRenderer") is not None] or [],
            lambda x: x[0], dict).get("itemSectionRenderer")
        if item_section is None:
            return [False, 'Unable to find itemSectionRenderer.']
        contents = item_section.get("contents")
        if contents is None:
            return [False, "Unable to find itemSectionRenderer contents."]
        channels = [x for x in map(format_contents, contents) if x is not None]
        return [True, channels]
