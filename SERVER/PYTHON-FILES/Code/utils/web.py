import os
from time import sleep

from .parser import parse_json, parse_m3u8_formats

from ..log import stopped, warning

import httplib2
from urllib3.exceptions import TimeoutError

#
#
# LITTLE BIT OF THIS CODE IN THIS FILE IS IN YOUTUBE-DL.
# Credit to them!
#

try:
    from urllib.request import HTTPCookieProcessor, build_opener
    from http.cookiejar import MozillaCookieJar, LoadError
except ImportError:
    LWPCookieJar = None
    HTTPCookieProcessor = None
    stopped("Unsupported version of Python. You need Version 3 :<")

cj = MozillaCookieJar(filename="cookies.txt")

if os.path.isfile("cookies.txt"):
    try:
        cj.load()
    except LoadError as e:
        if 'format file' in str(e):
            print("")
            warning("The Cookies File corrupted, deleting...")
            os.remove("cookies.txt")
            sleep(1)
            print("")


opener = build_opener(HTTPCookieProcessor(cj))


def download_website(url, headers=None, data=None):
    """

    Downloads website from url.

    :param url: url to open request to.
    :param headers: Form data sent to website.
    :param data: Form data sent to website.
    :return: str, int, None
    """
    try:
        from urllib.request import urlopen, Request
        from urllib.error import URLError
    except ImportError:
        Request = None
        URLError = None
        stopped("Unsupported version of Python. You need Version 3 :<")

    from .. import UserAgent
    if headers is None:
        headers = {"User-Agent": UserAgent}
    elif "User-Agent" not in headers:
        headers.update({"User-Agent": UserAgent})

    request = Request(url, headers=headers, data=data)

    try:
        response = opener.open(request)
    except (URLError, TimeoutError, OSError) as e2:
        try:
            return e2.code
        except AttributeError:
            return None
    except Exception as e2:
        warning("Unable to request HTTP website.")
        warning("Error: " + str(e2))
        return None
    try:
        cj.save()  # Saves Cookies
        cj.clear_expired_cookies()
    except Exception as e1:
        if 'Permission denied' in str(e1):
            print("")
            stopped("Permission denied Saving Cookies!\n"
                    "You can allow access by running sudo if you are on Linux.")
        else:
            warning("Error: " + str(e1))
            warning("Unable to save cookies.")
    try:
        website_bytes = response.read()
    except OSError as e2:
        warning("Error: " + str(e2))
        warning("Unable to read website bytes.")
        return None
    return website_bytes.decode('utf-8')


def download_image(image_url, file_name):
    try:
        from urllib.request import urlretrieve
        from urllib.error import URLError
    except ImportError:
        URLError = None
        urlretrieve = None
        stopped("Unsupported version of Python. You need Version 3 :<")
    try:
        urlretrieve(image_url, file_name)
        return True
    except (httplib2.ServerNotFoundError, TimeoutError, URLError):
        return False


def download_json(url, headers=None, data=None, transform_source=None):
    json_string = download_website(url, headers=headers, data=data)
    if type(json_string) is str:
        return parse_json(json_string, transform_source=transform_source)
    return json_string


def download_m3u8_formats(m3u8_url):
    m3u8_doc = download_website(m3u8_url)
    return parse_m3u8_formats(m3u8_doc)
