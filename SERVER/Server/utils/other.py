from os import mkdir
from os.path import exists, dirname, join
from urllib.parse import urlparse, parse_qs

from Server.logger import get_logger


def try_get(src, getter, expected_type=None):
    """
    Taken from https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/utils.py#L2312
    """

    if not isinstance(getter, (list, tuple)):
        getter = [getter]
    for get in getter:
        try:
            v = get(src)
        except (AttributeError, KeyError, TypeError, IndexError):
            pass
        else:
            if expected_type is None or isinstance(v, expected_type):
                return v


def get_utc_offset() -> int:
    # Mostly from https://stackoverflow.com/a/16061385 but as been changed.
    from datetime import datetime
    utc_offset = int((round((datetime.now() - datetime.utcnow()).total_seconds())) / 60)
    return utc_offset


def get_time_zone() -> str or None:
    try:
        import tzlocal as local
    except ImportError:
        local = None
        get_logger().warning("Unable to use TIMEZONE PLACEHOLDER IF TZLOCAL IS NOT INSTALLED.")
    if local:
        try:
            return local.get_localzone().zone
        except Exception as e:
            get_logger().warning(e)
            return None
    return None


def parse_url_query(url: str) -> dict:
    parsed_url = urlparse(url)
    dict_ = parse_qs(parsed_url.query)
    return dict_


def str_to_int(string: str):
    try:
        return int(string)
    except ValueError:
        return None


def parse_width_height(full_res: str):
    split = full_res.split('x') or full_res.split('X')
    if split and len(split) == 2:
        width, height = list(map(lambda x: str_to_int(x), split))
        if width and height:
            return width, height
    return None, None


def quality_str_int(quality: str) -> int or None:
    def width_height(full_res: str):
        width, height = parse_width_height(full_res)
        if width and height:
            return width * height
        return None

    name_to_int = {
        **dict.fromkeys(['1080p', '1080'], 1920 * 1080),
        **dict.fromkeys(['720p', '720'], 1280 * 720),
        **dict.fromkeys(['480p', '480'], 854 * 480),
    }  # type: Dict[str, int]

    if quality == 'original' or quality == 'max':
        return -1

    quality_number = name_to_int.get(quality) or width_height(quality)
    if quality_number is None:
        return None
    return quality_number


def handle_dup_filenames(file_name: str):
    def parse_filename(filename: str):
        num = filename.rfind('.')
        extension_ = filename[num + 1:]
        filename = filename[:num]
        return filename, extension_

    file_name, extension = parse_filename(file_name)
    dir_name = dirname(file_name)
    new_filename = join(dir_name, "{0}.{1}".format(file_name, extension))
    number = 1
    while exists(new_filename):
        new_filename = join(dir_name, "{0}_{1}.{2}".format(file_name, number, extension))
        number += 1
    return new_filename


def mkdir_ignore_exists(path: str):
    try:
        return mkdir(path)
    except FileExistsError:
        return True

