import re
from typing import List

compiled_attributes_re = re.compile(r'(?P<key>[A-Z0-9-]+)=(?P<val>"[^"]+"|[^",]+)(?:,|$)')
compiled_search_re = re.compile(r'(?P<width>\d+)[xX](?P<height>\d+)')


class HLS:
    formats = None

    def __init__(self):
        self.formats = []  # type: List[HLSMedia]

    def is_twitch_ad(self):
        pass

    def add_format(self, format: dict):
        self.formats.append(HLSMedia(
            format['url'], format['height'], format['width'],
            format['stream_resolution'], format['format']))


class HLSMedia:
    def __init__(self, url: str, height: int, width: int, stream_resolution: str, format_: str):
        self.url = url
        self.height = height
        self.width = width
        self.stream_resolution = stream_resolution
        self.format = format_


def parse_m3u8_attributes(attrib):
    """
    Taken from https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/utils.py#L3801
    """
    info = {}
    for (key, val) in compiled_attributes_re.findall(attrib):
        if val.startswith('"'):
            val = val[1:-1]
        info[key] = val
    return info


def parse_formats(m3u8_text) -> HLS:
    hls = HLS()
    last_stream_inf = {}
    for line in m3u8_text.splitlines():
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
                search = compiled_search_re.search(resolution)
                if search:
                    f['width'] = int(search.group('width'))
                    f['height'] = int(search.group('height'))
                    f['stream_resolution'] = "{0}x{1}".format(f['width'], f['height'])
            hls.add_format(f)
            last_stream_inf = {}
    return hls
