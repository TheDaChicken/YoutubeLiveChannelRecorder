import re
from Code.utils.parser import parse_json
from Code.log import stopped


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
