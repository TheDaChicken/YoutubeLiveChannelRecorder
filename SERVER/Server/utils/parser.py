import traceback
from Server.logger import get_logger

try:
    import orjson as json
except ImportError:
    import json


def parse_json(json_string, transform_source=None) -> dict or None:
    """
    Taken and have been edited from:
        https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/common.py#L895
    """
    if json_string:
        if transform_source:
            json_string = transform_source(json_string)
        try:
            return json.loads(json_string)
        except ValueError:
            get_logger().warning("Failed to parse JSON.")
            get_logger().error(traceback.format_exc())
            return None
    return None
