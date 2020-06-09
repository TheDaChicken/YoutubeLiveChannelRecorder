import os
from time import sleep

from Code.utils.parser import parse_json
from Code.utils.m3u8 import parse_formats as parse_m3u8_formats
from Code.log import stopped, warning

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
        from urllib.error import URLError, HTTPError
        from urllib.parse import urlencode
        from urllib.request import HTTPCookieProcessor, build_opener
    except ImportError:
        urlencode = None
        Request = None
        HTTPResponse = None
        URLError = None
        HTTPError = None
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

        def save(self, **kwargs) -> dict:
            super().save(**kwargs)
            return self._cookies

        def get_cookie_list(self) -> dict:
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
    response_headers = {}

    def __init__(self, url, headers=None, data=None, CookieDict=None, RequestMethod='GET'):
        if not headers:
            headers = {}
        if not data:
            data = {}
        if 'User-Agent' not in headers:
            headers.update({'User-Agent': UserAgent})
        self.headers = headers
        self.cj = build_cookies(CookieDict if CookieDict is not None else None)
        if self.use_requests:
            requestSession.cookies = self.cj
            try:
                if RequestMethod == 'GET':
                    r = requestSession.get(url, headers=headers, stream=True)
                if RequestMethod == 'POST':
                    r = requestSession.post(url, headers=headers, json=data)
                self.status_code = r.status_code
                self.text = r.text
                self.response_headers = r.headers
            except requests.exceptions.ConnectionError:
                pass
        else:
            opener = build_opener(HTTPCookieProcessor(self.cj))
            request = Request(url, headers=headers,
                              data=urlencode(data).encode("utf-8") if 'POST' in RequestMethod else None)
            try:
                response = opener.open(request)  # type: HTTPResponse
                self.status_code = response.getcode()
                self.response_headers = response.getheaders()
                self.text = response.read().decode('utf-8')
            except HTTPError as e:
                self.status_code = e.code
                self.response_headers = response.getheaders()
                self.text = response.read().decode('utf-8')
            except URLError:
                pass
            except (OSError, TimeoutError):
                pass
        self.cookies = self.cj.save()
        if CookieDict is not None:
            CookieDict.update(self.cookies)
        else:
            warning("No CookieDict")

    def parse_json(self):
        """

        Parses Response As JSON DICT

        :return: dict
        """
        return parse_json(self.text)

    def parse_m3u8_formats(self):
        """

        Parses Response As JSON DICT
        """
        return parse_m3u8_formats(self.text)
