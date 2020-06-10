import re
from Code.utils.parser import parse_json


def get_yt_player_config(website: str) -> dict or None:
    """

    Taken and have been edited from:
    https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1386

    """
    config = re.findall(r';ytplayer\.config\s*=\s*({.+?});', website)
    if config:
        return parse_json(config[0])


def get_yt_initial_data(website: str) -> dict or None:
    """

    Gets Youtube Initial Data. of course

    """
    if type(website) is not str:
        return None
    config = re.findall(r'window\[\"ytInitialData\"]\s=\s(.+);', website)
    if config:
        return parse_json(config[0])


def get_yt_config(website: str) -> dict or None:
    """

    Gets YT Config. of course

    """
    if type(website) is not str:
        return None
    config = re.findall(r'ytcfg\.set({.+?});', website)
    if config:
        return parse_json(config[0])


def get_endpoint_type(website: str) -> dict or None:
    """

    Gets Endpoint Type. of course

    """
    config = re.findall(r'var data\s=\s{\s[^>]*page: \"(.+?)\",', website)
    if config:
        return config[0]
