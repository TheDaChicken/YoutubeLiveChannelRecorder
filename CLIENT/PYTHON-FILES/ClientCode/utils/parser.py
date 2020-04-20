import json


def parse_json(json_string, transform_source=None):
    """
    Taken and have been edited from:
        https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/common.py#L895
    """
    if transform_source:
        json_string = transform_source(json_string)
    try:
        return json.loads(json_string)
    except Exception:
        return None
