import os
import traceback
from time import sleep

from .parser import parse_json, parse_m3u8_formats

from ..log import stopped, warning, error_warning

import httplib2
from urllib3.exceptions import TimeoutError

#
#
# LITTLE BIT OF THIS CODE IN THIS FILE IS IN YOUTUBE-DL.
# Credit to them!
#


try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError
    from urllib.request import HTTPCookieProcessor, build_opener
    from http.cookiejar import MozillaCookieJar, LoadError, Cookie
except ImportError:
    Request = None
    URLError = None
    HTTPCookieProcessor = None
    build_opener = None
    MozillaCookieJar = None
    LoadError = None
    stopped("Unsupported version of Python. You need Version 3 :<")


def __build_opener(cj):
    """
    :type cj: MozillaCookieJar
    """
    # BUILD OPENER
    opener = build_opener(HTTPCookieProcessor(cj))
    return opener


def __build__cookies(cookies=None):
    class CustomCookieJar(MozillaCookieJar):
        _cookies = None

        def load(self, custom_list=None, **kwargs):
            """
            Allows to load list of Cookies instead of keep loading a cookie file, if needed.
            """
            if custom_list:
                self._cookies = custom_list
            else:
                super().load(**kwargs)

        def save(self, **kwargs):
            super().save(**kwargs)
            return self._cookies

        def get_cookie_list(self):
            return self._cookies

    cj = CustomCookieJar(filename="cookies.txt")
    if os.path.isfile("cookies.txt"):
        try:
            cj.load(custom_list=cookies)
        except LoadError as e:
            if 'format' in str(e):
                print("")
                warning("The Cookies File corrupted, deleting...")
                os.remove("cookies.txt")
                sleep(1)
                print("")
    return cj


def download_website(url, headers=None, data=None, SharedVariables=None):
    """

    Downloads website from url.

    :param SharedVariables: Contains Shared Variables between different processes.
    :param url: url to open request to.
    :param headers: Form data sent to website.
    :param data: Form data sent to website.
    :return: str, int, None
    """

    if headers is None:
        headers = {}
    cj = __build__cookies(SharedVariables.CachedCookieList if SharedVariables is not None else None)
    opener = __build_opener(cj)

    from .. import UserAgent
    if "User-Agent" not in headers:
        headers.update({"User-Agent": UserAgent})

    try:
        request = Request(url, headers=headers, data=data)
    except Exception:
        error_warning(traceback.format_exc())
        return None
    try:
        response = opener.open(request)
    except (URLError, TimeoutError, OSError) as e2:
        try:
            return e2.code
        except AttributeError:
            return None
    except Exception:
        warning("Unable to request HTTP website.")
        error_warning(traceback.format_exc())
        return None

    try:
        if SharedVariables:
            SharedVariables.CachedCookieList = cj.save()  # Saves Cookies
        else:
            cj.save()  # Saves Cookies
    except Exception as e1:
        if 'Permission denied' in str(e1):
            print("")
            stopped("Permission denied Saving Cookies!\n"
                    "You can allow access by running sudo if you are on Linux.")
        else:
            error_warning(traceback.format_exc())
            warning("Unable to save cookies.")
    try:
        website_bytes = response.read()
    except OSError as e2:
        error_warning(traceback.format_exc())
        warning("Unable to read website bytes.")
        return None
    try:
        decoded_bytes = website_bytes.decode('utf-8')
    except Exception:
        error_warning(traceback.format_exc())
        warning("Unable to decode website bytes.")
        return None
    return decoded_bytes


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


def download_json(url, headers=None, data=None, transform_source=None, SharedVariables=None):
    json_string = download_website(url, headers=headers, data=data, SharedVariables=SharedVariables)
    if type(json_string) is str:
        return parse_json(json_string, transform_source=transform_source)
    return json_string


def download_m3u8_formats(m3u8_url, headers=None):
    m3u8_doc = download_website(m3u8_url, headers)
    if type(m3u8_doc) is str:
        return parse_m3u8_formats(m3u8_doc)
    return m3u8_doc
