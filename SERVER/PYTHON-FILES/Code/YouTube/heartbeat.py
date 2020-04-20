import traceback
from datetime import datetime

from Code.log import warning, reply, stopped, error_warning
from Code.utils.other import get_highest_thumbnail, try_get
from Code.utils.web import download_website

try:
    from urllib.parse import urlencode
except ImportError:
    urlencode = None
    stopped("Unsupported version of Python. You need Version 3 :<")


def is_live(channel_Class, CookieDict=None, globalVariables=None, json=None):
    """

    Checks if channel is live using the normal Youtube heartbeat.
    Also sets heartbeat related variables.

    :type CookieDict: dict
    :type alreadyChecked: bool
    :type channel_Class: ChannelYouTube
    :type globalVariables: GlobalVariables

    """

    if globalVariables is None:
        class GlobalVariables:
            def get(self, variable):
                return None

        globalVariables = GlobalVariables()

    try:
        if json is None:
            referer_url = 'https://www.youtube.com/channel/{0}/live'.format(channel_Class.channel_id)
            headers = {'Accept': "*/*", 'Accept-Language': 'en-US,en;q=0.9', 'dnt': '1',
                       'referer': referer_url, 'x-youtube-client-name': '1'}
            url_arguments = {'video_id': channel_Class.video_id, 'heartbeat_token': '',
                             'c': (globalVariables.get("client_name") if globalVariables.get(
                                 "client_name") is not None else 'WEB'),
                             'sequence_number': str(channel_Class.sequence_number)}
            if globalVariables.get("account_playback_token") is not None:
                headers.update({'x-youtube-identity-token': globalVariables.get("account_playback_token")})
            if globalVariables.get("page_build_label") is not None:
                headers.update({'x-youtube-page-label': globalVariables.get("page_build_label")})
            if globalVariables.get("page_cl") is not None:
                headers.update({'x-youtube-page-cl': globalVariables.get("page_cl")})
            if globalVariables.get("variants_checksum") is not None:
                headers.update({'x-youtube-variants-checksum': globalVariables.get("variants_checksum")})
            if globalVariables.get("utf_offset") is not None:
                headers.update({'x-youtube-utc-offset': str(globalVariables.get("utf_offset"))})
                url_arguments.update({'utc_offset_minutes': str(globalVariables.get("utf_offset"))})
            if globalVariables.get("client_version") is not None:
                headers.update({'x-youtube-client-version': globalVariables.get("client_version")})
                url_arguments.update({'cver': str(globalVariables.get("client_version"))})
            if globalVariables.get("timezone") is not None:
                url_arguments.update({'time_zone': str(globalVariables.get("timezone"))})
            if channel_Class.cpn is not None:
                url_arguments.update({'cpn': channel_Class.cpn})

            websiteClass = download_website(
                'https://www.youtube.com/heartbeat?{0}'.format(urlencode(url_arguments)),
                headers=headers, CookieDict=CookieDict)
            CookieDict.update(websiteClass.cookies)
            if websiteClass.text is None:
                return None
            json = websiteClass.parse_json()

        channel_Class.sequence_number += 1
        reply('FROM YOUTUBE -> {0}'.format(json))

        # SETTING VARIABLES
        liveStreamAbilityRenderer = try_get(json, lambda x: x['liveStreamability']['liveStreamabilityRenderer'], dict)
        if liveStreamAbilityRenderer:
            thumbnail = get_thumbnail(liveStreamAbilityRenderer)
            if thumbnail:
                channel_Class.thumbnail_url = thumbnail
            channel_Class.pollDelayMs = get_poll_delay_ms(liveStreamAbilityRenderer, channel_Class)
            channel_Class.live_scheduled = get_unix_schedule_time(liveStreamAbilityRenderer) is not None
            channel_Class.broadcast_id = get_broadcast_id(liveStreamAbilityRenderer)
            video_id = get_video_id(liveStreamAbilityRenderer)
            if video_id:
                if video_id != channel_Class.video_id:
                    channel_Class.add_youtube_queue()  # just in case something happens.
                    channel_Class.video_id = video_id

        if channel_Class.live_scheduled is True:
            channel_Class.live_scheduled_timeString = get_schedule_time(liveStreamAbilityRenderer)
            unix_time = get_unix_schedule_time(liveStreamAbilityRenderer)
            if unix_time:
                channel_Class.live_scheduled_time = datetime.fromtimestamp(unix_time)

        if 'stop_heartbeat' in json:
            channel_Class.add_youtube_queue()
            channel_Class.loadVideoData()
            return False

        if try_get(liveStreamAbilityRenderer, lambda x: x['displayEndscreen'], bool):
            last_video_id = channel_Class.video_id
            channel_Class.loadVideoData()
            # CHECK IF A VIDEO ID CHANGE BEFORE ADDING.
            if last_video_id != channel_Class.video_id:
                channel_Class.add_youtube_queue()
            return False

        status = try_get(json, lambda x: x['status'], str)  # type: str
        if status:  # Sometimes status is removed and causes an error.
            if "OK" in status.upper():
                return True
            if "STOP" in status.upper():
                channel_Class.add_youtube_queue()
                channel_Class.loadVideoData()
                return False
            if "ERROR" in status.upper():
                warning("Getting the Live Data, failed on Youtube's Side. Youtube Replied with: " + json['reason'])
                return False
            if "LIVE_STREAM_OFFLINE" in status.upper():
                return False
            warning("The Program couldn't find any value that matches the normal heartbeat. Returning False.")
        return False
    except KeyboardInterrupt:
        pass
    except BrokenPipeError:
        exit()
    except Exception:
        warning("Error occurred when doing Heartbeat.")
        error_warning(traceback.format_exc())
        return 1


# Getting Poll Delay from Heartbeat Json
def get_poll_delay_ms(liveStreamAbilityRenderer, channel_Class):
    pollDelayMs = try_get(liveStreamAbilityRenderer, lambda x: x['pollDelayMs'], str)
    if pollDelayMs:
        return int(pollDelayMs)
    elif channel_Class.pollDelayMs:
        return channel_Class.pollDelayMs
    else:
        return 9500


# Getting Thumbnails from Heartbeat Json
def get_thumbnail(liveStreamAbilityRenderer):
    offlineSlate = try_get(liveStreamAbilityRenderer, lambda x: x['liveStreamabilityRenderer']['offlineSlate'], dict)
    thumbnail_list = try_get(offlineSlate, lambda x: x['liveStreamOfflineSlateRenderer']['thumbnail']['thumbnails'],
                             list)
    if thumbnail_list:
        return get_highest_thumbnail(thumbnail_list)
    return None


def get_schedule_time(liveStreamAbilityRenderer):
    offlineSlate = try_get(liveStreamAbilityRenderer, lambda x: x['offlineSlate'], dict)
    liveStreamOfflineSlateRenderer = try_get(offlineSlate, lambda x: x['liveStreamOfflineSlateRenderer'], dict)
    if liveStreamOfflineSlateRenderer:
        return try_get(liveStreamOfflineSlateRenderer, lambda x: x['subtitleText']['simpleText'], str)
    return None


def get_broadcast_id(liveStreamAbilityRenderer):
    broadcastId = try_get(liveStreamAbilityRenderer, lambda x: x['broadcastId'], str)
    return broadcastId


def get_video_id(liveStreamAbilityRenderer):
    videoID = try_get(liveStreamAbilityRenderer, lambda x: x['videoId'], str)
    return videoID


def get_unix_schedule_time(liveStreamAbilityRenderer):
    offlineSlate = try_get(liveStreamAbilityRenderer, lambda x: x['offlineSlate'], dict)
    liveStreamOfflineSlateRenderer = try_get(offlineSlate, lambda x: x['liveStreamOfflineSlateRenderer'],
                                             dict)  # type: dict
    if liveStreamOfflineSlateRenderer:
        scheduledStartTime = liveStreamOfflineSlateRenderer.get("scheduledStartTime")
        if scheduledStartTime:
            try:
                return int(scheduledStartTime)
            except ValueError:
                return None
    return None
