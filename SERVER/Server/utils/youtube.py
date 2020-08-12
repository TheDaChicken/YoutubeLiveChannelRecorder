import re
from random import randint

from Server.utils.parser import parse_json

yt_player_config = re.compile(r';ytplayer\.config\s*=\s*({.+?});')


def get_yt_cfg(website: str):
    config = re.findall(r";ytcfg.set\((.+?)\);", website)
    if config:
        return parse_json(config[0])
    return None


def get_yt_player_config(website: str) -> dict or None:
    """
    Taken and have been edited from:
    https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1386
    """
    config = yt_player_config.findall(website)
    if config:
        return parse_json(config[0])
    return None


def get_yt_initial_data(website: str) -> dict or None:
    """
    Gets Youtube Initial Data. of course
    """
    if type(website) is not str:
        return None
    config = re.findall(r'window\[\"ytInitialData\"]\s=\s(.+);', website)
    if config:
        return parse_json(config[0])


def get_yt_web_player_config(website: str) -> dict or None:
    config = re.findall(r';ytplayer\.'
                        r'web_player_context_config'
                        r'\s*=\s*({.+?});', website)
    if config:
        return parse_json(config[0])
    return None


def get_endpoint_type(website: str) -> str or None:
    """
    Gets Endpoint Type. of course
    """
    config = re.findall(r'{\s[^>]*page: \"(.+?)\",', website)
    if config:
        return config[0]
    return None


def generate_cpn():
    """
    Looked at for reference:
    https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1531
    """
    CPN_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
    return ''.join((CPN_ALPHABET[randint(0, 256) & 63] for _ in range(0, 16)))

