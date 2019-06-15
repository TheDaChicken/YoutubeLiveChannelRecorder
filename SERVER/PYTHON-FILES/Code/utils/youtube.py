import re


def get_yt_player_config(website):
    """

    Taken and have been edited from:
    https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1386

    """
    from .parser import parse_json
    if type(website) is not str:
        return None
    config = re.findall(r';ytplayer\.config\s*=\s*({.+?});', website)
    if config:
        return parse_json(config[0])


def get_yt_initial_data(website):
    """

    Gets Youtube Initial Data. of course

    """
    from .parser import parse_json
    if type(website) is not str:
        return None
    config = re.findall(r'window\["ytInitialData"\] = (.+);', website)
    if config:
        return parse_json(config[0])


def get_yt_config(website):
    """

    Gets YT Config. of course

    """
    from .parser import parse_json
    if type(website) is not str:
        return None
    config = re.findall(r'ytcfg\.set({.+?});', website)
    if config:
        return parse_json(config[0])