from time import sleep

from ..log import warning, YoutubeReply
from ..utils.other import get_highest_thumbnail, try_get
from ..utils.web import download_json
from ..dataHandler import DownloadThumbnail


def is_live(channel_Class, alreadyChecked=False):
    """

    Checks if channel is live using the normal Youtube heartbeat.
    Also sets heartbeat related variables.

    :type channel_Class: ChannelInfo
    :type alreadyChecked: bool
    """

    if channel_Class.privateStream is True:
        if alreadyChecked is False:
            ok, message = channel_Class.loadVideoData()
            if not ok:
                warning(message)
        return False

    from . import account_playback_token, page_build_label, page_cl, variants_checksum, utf_offset, client_version, \
        client_name
    referer_url = 'https://www.youtube.com/channel/{0}/live'.format(channel_Class.channel_id)
    headers = {'Accept': "*/*", 'Accept-Language': 'en-US,en;q=0.9', 'Connection': 'keep-alive', 'dnt': 1,
               'referer': referer_url, 'x-youtube-client-name': 1}
    url = 'https://www.youtube.com/heartbeat?video_id=' + channel_Class.video_id + \
          '&heartbeat_token&c=' + (client_name if client_name is not None else 'WEB') + '&sequence_number=' + \
          str(channel_Class.sequence_number)
    if account_playback_token is not None:
        headers.update({
            'x-youtube-identity-token': account_playback_token,
        })
    if page_build_label is not None:
        headers.update({
            'x-youtube-page-label': page_build_label,
        })
    if page_cl is not None:
        headers.update({
            'x-youtube-page-cl': page_cl,
        })
    if variants_checksum is not None:
        headers.update({
            'x-youtube-variants-checksum': variants_checksum,
        })
    if utf_offset is not None:
        headers.update({
            'x-youtube-utc-offset': utf_offset,
        })
        url += "&utc_offset_minutes=" + str(utf_offset)
    if client_version is not None:
        headers.update({
            'x-youtube-client-version': client_version,
        })
        url += "&cver=" + client_version

    json = download_json(
        url,
        headers=headers)
    if type(json) is bool or json is None:
        return None
    channel_Class.sequence_number += 1
    YoutubeReply('FROM YOUTUBE -> ' + "{}".format(json))

    # SETTING VARIABLES
    liveStreamAbilityRenderer = try_get(json, lambda x: x['liveStreamability']['liveStreamabilityRenderer'], dict)
    if liveStreamAbilityRenderer:
        thumbnail = get_thumbnail(liveStreamAbilityRenderer)
        if thumbnail:
            channel_Class.thumbnail_url = thumbnail
        channel_Class.pollDelayMs = get_poll_delay_ms(liveStreamAbilityRenderer, channel_Class)
        channel_Class.live_scheduled = is_scheduled(liveStreamAbilityRenderer)
        channel_Class.broadcastId = get_broadcast_id(liveStreamAbilityRenderer)

    if channel_Class.live_scheduled is True:
        channel_Class.live_scheduled_time = get_schedule_time(json)
    if 'stop_heartbeat' in json:
        sleep(.5)
        channel_Class.video_id = channel_Class.get_video_id()
        return False
    if 'status' in json:  # Sometimes status is removed and causes an error.
        if "ok" in json['status']:
            return True
        if "stop" in json['status']:
            sleep(.29)
            channel_Class.video_id = channel_Class.get_video_id()
            return False
        if "error" in json['status']:
            warning("Getting the Live Data, failed on Youtube's Side. Youtube Replied with: " + json['reason'])
            return False
        if "live_stream_offline" in json['status']:
            return False
        warning("The Program couldn't find any value that matches the normal heartbeat. Returning False.")
    return False


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
    if DownloadThumbnail() is not True:
        return None
    offlineSlate = try_get(liveStreamAbilityRenderer, lambda x: x['liveStreamabilityRenderer']['offlineSlate'], dict)
    thumbnail_list = try_get(offlineSlate, lambda x: x['liveStreamOfflineSlateRenderer']['thumbnail']['thumbnails'])
    if thumbnail_list:
        return get_highest_thumbnail(
            offlineSlate['liveStreamOfflineSlateRenderer']['thumbnail']['thumbnails'])
    return None


# Checking if live stream is scheduled from Heartbeat Json
def is_scheduled(liveStreamAbilityRenderer):
    offlineSlate = try_get(liveStreamAbilityRenderer, lambda x: x['liveStreamabilityRenderer']['offlineSlate'], dict)
    liveStreamOfflineSlateRenderer = try_get(offlineSlate, lambda x: x['liveStreamOfflineSlateRenderer'], dict)
    if liveStreamOfflineSlateRenderer:
        return 'scheduledStartTime' in liveStreamOfflineSlateRenderer
    return False


def get_schedule_time(liveStreamAbilityRenderer):
    offlineSlate = try_get(liveStreamAbilityRenderer, lambda x: x['liveStreamabilityRenderer']['offlineSlate'], dict)
    liveStreamOfflineSlateRenderer = try_get(offlineSlate, lambda x: x['liveStreamOfflineSlateRenderer'], dict)
    if liveStreamOfflineSlateRenderer:
        return try_get(liveStreamOfflineSlateRenderer, lambda x: x['subtitleText']['simpleText'], str)
    return None


def get_broadcast_id(liveStreamAbilityRenderer):
    broadcastId = try_get(liveStreamAbilityRenderer, lambda x: x['broadcastId'], str)
    return broadcastId
