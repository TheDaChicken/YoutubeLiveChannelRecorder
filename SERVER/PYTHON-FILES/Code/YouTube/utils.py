import re
from Code.utils.parser import parse_json
from Code.log import stopped, warning
from Code.utils.other import try_get, get_format_from_data
from Code.utils.web import download_website, download_m3u8_formats


def get_yt_player_config(website):
    """

    Taken and have been edited from:
    https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1386

    """
    if type(website) is not str:
        return None
    config = re.findall(r';ytplayer\.config\s*=\s*({.+?});', website)
    if config:
        return parse_json(config[0])


def get_yt_initial_data(website):
    """

    Gets Youtube Initial Data. of course

    """
    if type(website) is not str:
        return None
    config = re.findall(r'window\[\"ytInitialData\"]\s=\s(.+);', website)
    if config:
        return parse_json(config[0])


def get_yt_config(website):
    """

    Gets YT Config. of course

    """
    if type(website) is not str:
        return None
    config = re.findall(r'ytcfg\.set({.+?});', website)
    if config:
        return parse_json(config[0])


def get_endpoint_type(website):
    """

    Gets Endpoint Type. of course

    """
    if type(website) is not str:
        return None
    config = re.findall(r'var data\s=\s{\s[^>]*page: \"(.+?)\",', website)
    if config:
        return config[0]


try:
    from urllib.parse import urlencode, parse_qs
except ImportError:
    parse_qs = None  # Fixes a random PyCharm warning.
    urlencode = None
    stopped("Unsupported version of Python. You need Version 3 :<")


def get_video_info(channelClass, recordingHeight=None):
    """
    Gets the stream info from channelClass.
    Looked at for reference:
    https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1675

    """

    url_arguments = {'html5': 1, 'video_id': channelClass.video_id}
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
    if channelClass.cpn is not None:
        url_arguments.update({'cpn': channelClass.cpn})

    downloadClass = download_website(
        'https://www.youtube.com/get_video_info?{0}'.format(
            urlencode(url_arguments)))
    video_info_website = downloadClass.text

    video_info = parse_qs(video_info_website)
    player_response = parse_json(try_get(video_info, lambda x: x['player_response'][0], str))
    if player_response:
        video_details = try_get(player_response, lambda x: x['videoDetails'], dict)
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
            'video_id': channelClass
        }
        return youtube_stream_info
    return None
