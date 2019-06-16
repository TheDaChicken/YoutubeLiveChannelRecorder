import re

from ..log import warning, stopped
import json


#
#
# LITTLE BIT OF THIS CODE IN THIS FILE IS IN YOUTUBE-DL.
# Credit to them!
#

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
        except TypeError:
            warning("Failed to parse JSON.")
        return None
    return None


def parse_m3u8_formats(m3u8_doc):
    """

    Taken and have been edited from:
    https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/common.py#L1608

    """

    def parse_m3u8_attributes(attrib):
        """
        Taken from https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/utils.py#L3801
        """
        info = {}
        for (key, val) in re.findall(r'(?P<key>[A-Z0-9-]+)=(?P<val>"[^"]+"|[^",]+)(?:,|$)', attrib):
            if val.startswith('"'):
                val = val[1:-1]
            info[key] = val
        return info

    if '#EXT-X-FAXS-CM:' in m3u8_doc:  # Adobe Flash Access
        return []
    if re.search(r'#EXT-X-SESSION-KEY:.*?URI="skd://', m3u8_doc):  # Apple FairPlay
        return []
    last_stream_inf = {}
    formats = []
    for line in m3u8_doc.splitlines():
        if line.startswith('#EXT-X-STREAM-INF:'):
            last_stream_inf = parse_m3u8_attributes(line)
        elif line.startswith('#') or not line.strip():
            continue
        else:
            manifest_url = line.strip()
            f = {
                'url': manifest_url,
            }
            resolution = last_stream_inf.get('RESOLUTION')
            if resolution:
                search = re.search(r'(?P<width>\d+)[xX](?P<height>\d+)', resolution)
                if search:
                    f['width'] = int(search.group('width'))
                    f['height'] = int(search.group('height'))
            formats.append(f)
            last_stream_inf = {}
    return formats


def parse_html_attributes(html_element):
    """
    
    Taken from:
    https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/utils.py#L399

    """
    try:
        from html.parser import HTMLParser
        from urllib.parse import urlencode
    except ImportError:
        HTMLParser = None
        stopped("Unsupported version of Python. You need Version 3 :<")

    class HTMLAttributeParser(HTMLParser):
        """

        Taken from:
        https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/utils.py#L389

        """
        """Trivial HTML parser to gather the attributes for a single element"""

        def __init__(self):
            self.attrs = {}
            HTMLParser.__init__(self)

        def handle_starttag(self, tag, attrs):
            self.attrs = dict(attrs)

    """Given a string for an HTML element such as
    <el
         a="foo" B="bar" c="&98;az" d=boz
         empty= noval entity="&amp;"
         sq='"' dq="'"
    >
    Decode and return a dictionary of attributes.
    {
        'a': 'foo', 'b': 'bar', c: 'baz', d: 'boz',
        'empty': '', 'noval': None, 'entity': '&',
        'sq': '"', 'dq': '\''
    }.
    NB HTMLParser is stricter in Python 2.6 & 3.2 than in later versions,
    but the cases in the unit test will work for all of 2.6, 2.7, 3.2-3.5.
    """
    parser = HTMLAttributeParser()
    try:
        parser.feed(html_element)
        parser.close()
    # Older Python may throw HTMLParseError in case of malformed HTML
    except HTMLParser:
        pass
    return parser.attrs
