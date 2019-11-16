import traceback
from Code.log import warning, error_warning

try:
    import orjson as json
except ImportError:
    import json


def parse_json(json_string, transform_source=None):
    """
    Taken and have been edited from:
        https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/common.py#L895
    """
    if json_string:
        if transform_source:
            json_string = transform_source(json_string)
        try:
            return json.loads(json_string)
        except Exception:
            warning("Failed to parse JSON.")
            error_warning(traceback.format_exc())
            return None
    return None
