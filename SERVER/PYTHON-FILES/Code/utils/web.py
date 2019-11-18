import os
import traceback
import urllib
from time import sleep

from Code.utils.parser import parse_json, parse_m3u8_formats
from Code.log import stopped, warning, error_warning

UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
            'Chrome/75.0.3770.100 Safari/537.36'


try:
    import requests
    requestSession = requests.Session()
except ImportError:
    requests = None
    try:
        from http.client import HTTPResponse
        from urllib.request import urlopen, Request
        from urllib.error import URLError
        from urllib.request import HTTPCookieProcessor, build_opener
    except ImportError:
        Request = None
        HTTPResponse = None
        URLError = None
        HTTPCookieProcessor = None
        build_opener = None
        stopped("Unsupported version of Python.")

try:
    from http.cookiejar import MozillaCookieJar, LoadError, Cookie
except ImportError:
    MozillaCookieJar = None
    LoadError = None
    stopped("Unsupported version of Python.")


def build_cookies(cookies=None):
    class CustomCookieJar(MozillaCookieJar):
        _cookies = None

        def load(self, custom_list=None, **kwargs):
            """
            Allows to load list of Cookies instead of keep loading a cookie file, if needed.
            :type custom_list: dict
            """
            if custom_list:
                custom_list = custom_list.copy()
                self._cookies = custom_list
            else:
                if os.path.exists(self.filename):
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


def download_website(url, headers=None, data=None, CookieDict=None):
    try:
        if not headers:
            headers = {}

        if 'User-Agent' not in headers:
            headers.update({'User-Agent': UserAgent})
        if requests is None:
            cj = build_cookies(CookieDict if CookieDict is not None else None)
            opener = build_opener(HTTPCookieProcessor(cj))
            request = Request(url, headers=headers, data=data)
            try:
                response = opener.open(request)  # type: HTTPResponse
            except urllib.error.HTTPError as e:
                return e.code
            except (TimeoutError, OSError):
                return None
            website_bytes = response.read()
            decoded_bytes = website_bytes.decode('utf-8')
            return decoded_bytes
        else:
            cj = build_cookies(CookieDict if CookieDict is not None else None)
            requestSession.cookies = cj
            r = requestSession.get(url, headers=headers)
            if r.status_code != 200:
                return r.status_code
            decoded_bytes = r.text
        try:
            cj.save()
        except Exception as e1:
            if 'Permission denied' in str(e1):
                print("")
                stopped("Permission denied Saving Cookies!\n"
                        "You can allow access by running sudo if you are on Linux.")
            else:
                error_warning(traceback.format_exc())
                warning("Unable to save cookies.")
        return decoded_bytes
    except Exception:
        warning("Unable to download website code!")
        error_warning(traceback.format_exc())
        return None


def download_json(url, headers=None, data=None, transform_source=None, CookieDict=None):
    json_string = download_website(url, headers=headers, data=data, CookieDict=CookieDict)
    if type(json_string) is str:
        return parse_json(json_string, transform_source=transform_source)
    return json_string


def download_m3u8_formats(m3u8_url, headers=None):
    m3u8_doc = download_website(m3u8_url, headers)
    if type(m3u8_doc) is str:
        return parse_m3u8_formats(m3u8_doc)
    return m3u8_doc
