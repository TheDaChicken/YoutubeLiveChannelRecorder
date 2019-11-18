from ..log import warning


#
#
# LITTLE BIT OF THIS CODE IN THIS FILE IS IN YOUTUBE-DL.
# Credit to them!
#


# This gets the best format of the width.
def get_format_from_data(formats, resolution):
    if type(resolution) is str:
        if 'original' in resolution:
            return max(formats, key=lambda x: x['height'])
        split = resolution.split('x')
        if len(split) != 2:
            warning('The given resolution must be a valid resolution. Getting best format.')
            return max(formats, key=lambda x: x['height'])
        # height x width
        try:
            okay_width = int(split[0])
            okay_height = int(split[1])
        except ValueError:
            warning('The given resolution must be a valid resolution. Getting best format.')
            return max(formats, key=lambda x: x['height'])
        highest_format = None
        for format_ in formats:
            height = format_['height']
            width = format_['width']
            if not (height > okay_height and width > okay_width):
                if highest_format:
                    if highest_format['width'] < width and highest_format['height'] < height:
                        highest_format = format_
                else:
                    highest_format = format_
        if not highest_format:
            warning("Unable to find best resolution fit with recording at. Using best quality.")
            return max(formats, key=lambda x: x['height'])
        return highest_format
    warning("Resolution stored in data is invalid. Getting best format.")
    # BEST FORMAT IS MOSTLY ON TOP.
    return max(formats, key=lambda x: x['height'])


# This could be changed but as right now, it seems to work.
def get_highest_thumbnail(thumbnails):
    thumbnail_highest = max(thumbnails, key=lambda x: x['width'])
    return str(thumbnail_highest['url'])


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


def getTimeZone():
    try:
        import tzlocal as local
    except ImportError:
        local = None
        warning("Unable to use TIMEZONE PLACEHOLDER IF TZLOCAL IS NOT INSTALLED.")
    if local:
        try:
            return local.get_localzone().zone
        except Exception as e:
            warning(e)
            return None
    return None