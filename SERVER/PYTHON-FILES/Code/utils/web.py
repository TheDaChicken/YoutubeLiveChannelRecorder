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


class download_website:
    use_requests = requests is not None
    text = None
    response_headers = None

    def __init__(self, url, headers=None, data=None, CookieDict=None):
        if not headers:
            headers = {}
        if 'User-Agent' not in headers:
            headers.update({'User-Agent': UserAgent})
        self.headers = headers
        self.cj = build_cookies(CookieDict if CookieDict is not None else None)
        if self.use_requests:
            requestSession.cookies = self.cj
            try:
                r = requestSession.get(url, headers=headers)
                self.status_code = r.status_code
                self.text = r.text
                self.response_headers = r.headers
            except requests.exceptions.ConnectionError:
                pass
        else:
            opener = build_opener(HTTPCookieProcessor(self.cj))
            request = Request(url, headers=headers, data=data)
            try:
                response = opener.open(request)  # type: HTTPResponse
                self.status_code = response.getcode()
                self.response_headers = response.getheaders()
                self.text = response.read().decode('utf-8')
            except urllib.error.HTTPError as e:
                self.status_code = e.code
                self.response_headers = response.getheaders()
                self.text = response.read().decode('utf-8')
            except urllib.error.URLError:
                pass
            except (OSError, TimeoutError):
                pass
        self.cookies = self.cj.save()

    def parse_json(self):
        """

        Parses Response As JSON DICT

        :return: dict
        """
        return parse_json(self.text)


def download_m3u8_formats(m3u8_url, headers=None):
    m3u8_doc = download_website(m3u8_url, headers)
    if type(m3u8_doc) is str:
        return parse_m3u8_formats(m3u8_doc)
    return m3u8_doc
