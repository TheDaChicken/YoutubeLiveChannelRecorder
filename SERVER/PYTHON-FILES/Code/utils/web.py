import os
import traceback
import urllib
from time import sleep
from Code.utils.parser import parse_json
from Code.log import stopped, warning, error_warning

try:
    from http.client import HTTPResponse
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
    HTTPResponse = None
    stopped("Unsupported version of Python.")


def download_website(url, headers=None, data=None, CookieDict=None):
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

    try:
        cj = __build__cookies(CookieDict if CookieDict is not None else None)
        opener = build_opener(HTTPCookieProcessor(cj))
        request = Request(url, headers=headers, data=data)
        try:
            response = opener.open(request)  # type: HTTPResponse
        except urllib.error.HTTPError as e:
            return e.code
        except (TimeoutError, OSError):
            return None
        except Exception:
            warning("Unable to request HTTP website.")
            error_warning(traceback.format_exc())
            return None
        try:
            website_bytes = response.read()
        except Exception:
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
    except Exception:
        error_warning(traceback.format_exc())
        return None


def download_json(url, headers=None, data=None, transform_source=None, CookieDict=None):
    json_string = download_website(url, headers=headers, data=data, CookieDict=CookieDict)
    if type(json_string) is str:
        return parse_json(json_string, transform_source=transform_source)
    return json_string
