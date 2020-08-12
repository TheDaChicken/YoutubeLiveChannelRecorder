import re
from typing import List
from urllib.parse import urlsplit

from Server.logger import get_logger
from Server.utils.other import quality_str_int, parse_width_height

compiled_attributes_re = re.compile(r'(?P<key>[A-Z0-9-]+)=(?P<val>"[^"]+"|[^",]+)(?:,|$)')
# compiled_search_re = re.compile(r'(?P<width>\d+)[xX](?P<height>\d+)')


class Media:
    def __init__(self, url: str, height: int, width: int, stream_resolution: str, format_name: str):
        self.url = url  # type: str
        self.height = height or 0
        self.width = width or 0
        self.stream_resolution = stream_resolution
        self.format_name = format_name

    def __int__(self):
        """
        Returns The Size of width * height
        """
        return self.height * self.width

    def __eq__(self, other):
        return int(self) == int(other)

    def __ge__(self, other):
        return int(other) < int(self)

    def __lt__(self, other):
        return int(self) < int(other)

    def __gt__(self, other):
        return int(self) >= int(other)

    def __le__(self, other):
        return int(self) <= int(other)

    def __str__(self):
        split_url = urlsplit(self.url)
        string = ["<Media {0}".format(split_url.netloc)]
        if self.height and self.width:
            string.append(" [{0} x {1}]".format(self.width, self.height))
        string.append(">")
        return ''.join(string)

    def get_format(self) -> str:
        return self.format_name


class HLS:
    def __init__(self):
        self.formats = []  # type: List[Media]

    def add_format(self, f: dict):
        self.formats.append(Media(
            f['url'], f['height'], f['width'],
            f['stream_resolution'], f['format']))

    def greatest_format(self) -> Media:
        return max(self.formats)

    def lowest_format(self) -> Media:
        return max(self.formats)

    def get_best_format(self, quality: str) -> Media:
        quality_number = quality_str_int(quality)
        if quality_number is None:
            get_logger().warning(
                "Invalid quality \"{0}\". Using best quality Instead as a safe-guard.".format(quality))
            return self.greatest_format()
        if quality_number == -1:
            return self.greatest_format()
        cut = [i for i in self.formats if i <= quality_number]
        if len(cut) == 0:
            get_logger().warning(
                "Invalid quality in this case. ("
                "{0}) Using lowest quality instead as a safe-guard.".format(quality))
            return self.lowest_format()
        lower = min(cut, key=lambda x: abs(int(x) - quality_number))
        return lower

    def __len__(self):
        return len(self.formats)


def parse_m3u8_attributes(attrib):
    """
    Taken from https://github.com/ytdl-org/youtube-dl/blob/e942cfd1a74cea3a3a53231800bbf5a002eed85e/youtube_dl/utils.py#L5493
    and have been edited
    """

    def check(tuple_: tuple):
        key, val = tuple_
        if val.startswith('"'):
            val = val[1:-1]
        return key, val

    ca = compiled_attributes_re.findall(attrib)
    result = dict(map(lambda kv: check((kv[0], kv[1])), ca))
    return result


def parse_formats(response) -> HLS:
    hls = HLS()
    last_stream_inf = {}
    for encoded_line in response.iter_lines():
        if encoded_line:
            line = encoded_line.decode('utf-8')
            if line.startswith('#EXT-X-STREAM-INF:'):
                last_stream_inf = parse_m3u8_attributes(line)
            elif line.startswith('#') or not line.strip():
                continue
            else:
                manifest_url = line.strip()
                f = {
                    'url': manifest_url,
                    'format': 'hls'
                }
                resolution = last_stream_inf.get('RESOLUTION')
                if resolution:
                    search = parse_width_height(resolution)
                    if search:
                        f['width'] = int(search[0])
                        f['height'] = int(search[1])
                        f['stream_resolution'] = "{0}x{1}".format(f['width'], f['height'])
                hls.add_format(f)
                last_stream_inf = {}
    return hls
