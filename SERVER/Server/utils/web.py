from http import cookiejar
from http.cookiejar import MozillaCookieJar
from os.path import exists

from requests import Session, Request, Response
from requests.adapters import HTTPAdapter, CaseInsensitiveDict, get_encoding_from_headers, extract_cookies_to_jar

from Server.utils.m3u8 import parse_formats as parse_m3u8_formats, HLS

UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
            'Chrome/83.0.4103.116 Safari/537.36'


class CustomResponse(Response):
    def m3u8(self) -> HLS:
        return parse_m3u8_formats(self)


class CustomHTTPAdapter(HTTPAdapter):
    def build_response(self, req, resp):
        response = CustomResponse()

        response.status_code = getattr(resp, 'status', None)

        response.headers = CaseInsensitiveDict(getattr(resp, 'headers', {}))

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode('utf-8')
        else:
            response.url = req.url

        extract_cookies_to_jar(response.cookies, req, resp)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response


def create_session() -> Session:
    s = Session()
    cookie_jar = MozillaCookieJar('cookies.txt')
    if exists("cookies.txt"):
        try:
            cookie_jar.load()
        except cookiejar.LoadError as e:
            pass
    s.cookies = cookie_jar
    s.mount(
        'https://', CustomHTTPAdapter(),
    )
    return s
