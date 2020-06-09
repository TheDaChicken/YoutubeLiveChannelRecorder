import traceback

from Code.log import warning, error_warning, stopped

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
        except ValueError:
            warning("Failed to parse JSON.")
            error_warning(traceback.format_exc())
            return None
    return None


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
