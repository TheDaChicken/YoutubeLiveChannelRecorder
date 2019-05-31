from time import sleep

from ..log import warning, YoutubeReply
from ..utils.other import get_highest_thumbnail
from ..utils.web import download_json
from ..dataHandler import DownloadThumbnail


def is_live(channel_Class, first_time=False):
    """

    Checks if channel is live using the normal Youtube heartbeat.
    Also sets heartbeat related variables.

    :type channel_Class: ChannelInfo
    :type first_time: bool
    """

    if channel_Class.video_id is None:
        if channel_Class.privateStream is True:
            if first_time is False:
                channel_Class.video_id = channel_Class.get_video_id()
            if channel_Class.pollDelayMs is None:
                channel_Class.pollDelayMs = get_poll_delay_ms({}, channel_Class)
            return False

    referer_url = 'https://www.youtube.com/channel/{0}/live'.format(channel_Class.channel_id)
    headers = {'Accept': "*/*", 'Accept-Language': 'en-US,en;q=0.9', 'Connection': 'keep-alive', 'dnt': 1,
               'referer': referer_url, 'x-youtube-client-name': 1}
    url = 'https://www.youtube.com/heartbeat?video_id=' + channel_Class.video_id + \
          '&heartbeat_token&c=WEB&sequence_number=' + str(channel_Class.sequence_number)
    from . import account_playback_token, page_build_label, page_cl, variants_checksum, utf_offset, client_version
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
    channel_Class.thumbnail_url = get_thumbnail(json, channel_Class)
    channel_Class.pollDelayMs = get_poll_delay_ms(json, channel_Class)
    channel_Class.live_scheduled = is_scheduled(json)
    channel_Class.broadcastId = get_broadcast_id(json)
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
def get_poll_delay_ms(heart_beat_json, channel_Class):
    if 'liveStreamability' in heart_beat_json:
        if 'liveStreamabilityRenderer' in heart_beat_json['liveStreamability']:
            if 'pollDelayMs' in heart_beat_json['liveStreamability']['liveStreamabilityRenderer']:
                return int(heart_beat_json['liveStreamability']['liveStreamabilityRenderer']['pollDelayMs'])
    if channel_Class.pollDelayMs is None:
        return 14000
    else:
        return channel_Class.pollDelayMs


# Getting Thumbnails from Heartbeat Json
def get_thumbnail(heart_beat_json, channel_Class):
    if DownloadThumbnail() is not True:
        return None
    if 'liveStreamability' in heart_beat_json:
        live_stream_ability = heart_beat_json['liveStreamability']
        if 'liveStreamabilityRenderer' in live_stream_ability:
            if 'offlineSlate' in live_stream_ability['liveStreamabilityRenderer']:
                offline_slate = live_stream_ability['liveStreamabilityRenderer']['offlineSlate']
                if 'liveStreamOfflineSlateRenderer' in offline_slate:
                    return get_highest_thumbnail(
                        offline_slate['liveStreamOfflineSlateRenderer']['thumbnail']['thumbnails'])
    return 'https://i.ytimg.com/vi/{}/maxresdefault.jpg'.format(channel_Class.video_id)


# Checking if live stream is scheduled from Heartbeat Json
def is_scheduled(heart_beat_json):
    if 'liveStreamability' in heart_beat_json and 'liveStreamabilityRenderer' in heart_beat_json[
        'liveStreamability'] and 'offlineSlate' in heart_beat_json[
        'liveStreamability']['liveStreamabilityRenderer'] and 'liveStreamOfflineSlateRenderer' in heart_beat_json[
        'liveStreamability']['liveStreamabilityRenderer']['offlineSlate']:
        return 'scheduledStartTime' in heart_beat_json['liveStreamability']['liveStreamabilityRenderer'][
            'offlineSlate']['liveStreamOfflineSlateRenderer']
    return False


def get_schedule_time(heart_beat_json):
    if 'liveStreamability' in heart_beat_json and 'liveStreamabilityRenderer' in heart_beat_json[
        'liveStreamability'] and 'offlineSlate' in heart_beat_json[
        'liveStreamability']['liveStreamabilityRenderer']:
        return heart_beat_json['liveStreamability']['liveStreamabilityRenderer'][
            'offlineSlate']['liveStreamOfflineSlateRenderer']['subtitleText']['simpleText']
    return None


def get_broadcast_id(heart_beat_json):
    if 'liveStreamability' in heart_beat_json and 'liveStreamabilityRenderer' in heart_beat_json[
        'liveStreamability'] and 'broadcastId' in heart_beat_json[
        'liveStreamability']['liveStreamabilityRenderer']:
        return heart_beat_json[
            'liveStreamability']['liveStreamabilityRenderer']['broadcastId']
    return None


