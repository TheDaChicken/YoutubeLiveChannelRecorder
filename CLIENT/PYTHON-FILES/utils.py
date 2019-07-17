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
        urlopen = None
        Request = None
        stopped("Unsupported version of Python. You need Version 3 :<")

    request = Request(url, headers=Headers)
    try:
        response = urlopen(request,
                           data=urllib.parse.urlencode({}).encode("utf-8") if 'POST' in RequestMethod else None)
    except urllib.error.HTTPError as e1:
        try:
            if e1.code == 504:
                return 504
            return e1.read().decode('utf-8')
        except AttributeError:
            if 'CERTIFICATE_VERIFY_FAILED' in str(e1):  # ERROR IN URLError.
                return 2
            return None
    except (TimeoutError, OSError) as e:
        if 'closed' in str(e):  # ERROR IN OSError.
            return 504
        if 'CERTIFICATE_VERIFY_FAILED' in str(e):  # ERROR IN URLError.
            return 2
        return None
    except Exception as e4:
        warning("Unable to request HTTP website.")
        warning("Error: " + str(e4))
        return None
    try:
        website_bytes = response.read()
    except OSError as e4:
        warning("Error: " + str(e4))
        warning("Unable to read website bytes.")
        return None
    try:
        decoded_bytes = website_bytes.decode('utf-8')
    except Exception as e4:
        warning("Error: " + str(e4))
        warning("Unable to decode website bytes.")
        return None
    return decoded_bytes


def parse_json(json_string):
    import json
    try:
        return json.loads(json_string)
    except TypeError as ve:
        errmsg = '%s: Failed to parse JSON. This might just be a python bug.'
        warning(errmsg)


def download_json(url, Headers=None, RequestMethod='GET'):
    res = download_website(url, Headers=Headers, RequestMethod=RequestMethod)
    if type(res) is not str:
        return res
    json_string = res
    return parse_json(json_string)


def stringToInt(string):
    try:
        okay = int(string)
        return okay
    except ValueError:
        return None
