import re
import urllib

import httplib2
from urllib3.exceptions import TimeoutError

from log import warning, stopped


# MOST OF THE CODE WAS CODE TAKEN FROM YOUTUBE-DL AND OR CHANGED TO FIT HERE. CREDIT TO THE AUTHORS OF YOUTUBE-DL.
# YOU WILL NEED PYTHON 3 FOR THIS.

def download_website(url, Headers=None, RequestMethod='GET'):
    try:
        from urllib.request import urlopen, Request
    except ImportError:
        stopped("Unsupported version of Python. You need Version 3 :<")

    def _guess_encoding_from_content(content_type, webpage_bytes):
        m = re.match(r'[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+\s*;\s*charset=(.+)', content_type)
        if m:
            encoding = m.group(1)
        else:
            m = re.search(br'<meta[^>]+charset=[\'"]?([^\'")]+)[ /\'">]', webpage_bytes[:1024])
            if m:
                encoding = m.group(1).decode('ascii')
            elif webpage_bytes.startswith(b'\xff\xfe'):
                encoding = 'utf-16'
            else:
                encoding = 'utf-8'
        return encoding

    def download_website_handle(http_response):
        content_type = http_response.headers.get('Content-Type', '')
        webpage_bytes = http_response.read()
        encoding = _guess_encoding_from_content(content_type, webpage_bytes)
        try:
            content = webpage_bytes.decode(encoding, 'replace')
        except LookupError:
            content = webpage_bytes.decode('utf-8', 'replace')
        return content

    if Headers is not None:
        # {'User-Agent': UserAgent}
        request = Request(url, headers=Headers)
    else:
        request = Request(url)

    try:
        if 'POST' in RequestMethod:
            website = urlopen(request, data=urllib.parse.urlencode({}).encode("utf-8"))
        elif 'GET' in RequestMethod:
            website = urlopen(request, data=None)
        else:
            website = urlopen(request)
    except (urllib.error.URLError, httplib2.ServerNotFoundError, TimeoutError) as e:
        try:
            if e.code == 500:  # CUSTOM FOR READING ERROR MESSAGES FROM SERVER.
                return e.read().decode('utf-8')
            if e.code == 404:
                return 404
        except AttributeError:
            return None
        return None

    res = download_website_handle(website)
    return res


def parse_json(json_string):
    import json
    try:
        return json.loads(json_string)
    except TypeError as ve:
        errmsg = '%s: Failed to parse JSON. This might just be a python bug.'
        warning(errmsg)


def download_json(url, Headers=None):
    res = download_website(url, Headers=Headers)
    if type(res) is not str:
        return res
    json_string = res
    return parse_json(json_string)