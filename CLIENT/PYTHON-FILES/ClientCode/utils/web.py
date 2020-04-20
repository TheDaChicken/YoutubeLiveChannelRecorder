from ClientCode.log import stopped
from ClientCode.utils.parser import parse_json

UserAgent = 'Python Client'

try:
    import requests

    requestSession = requests.Session()
except ImportError:
    requests = None
    try:
        from http.client import HTTPResponse
        from urllib.request import urlopen, Request
        from urllib.parse import urlencode
        from urllib.error import URLError, HTTPError
    except ImportError:
        urlencode = None
        urlopen = None
        Request = None
        HTTPResponse = None
        URLError = None
        HTTPError = None
        stopped("Unsupported version of Python.")


class download_website:
    use_requests = requests is not None
    text = None
    response_headers = None

    def __init__(self, url, headers=None, data=None, RequestMethod='GET'):
        if not headers:
            headers = {}
        if 'User-Agent' not in headers:
            headers.update({'User-Agent': UserAgent})
        self.headers = headers
        if self.use_requests:
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
            request = Request(url, headers=headers, data=data)
            try:
                response = urlopen(request, data=urlencode(
                        data).encode("utf-8") if 'POST' in RequestMethod else None)  # type: HTTPResponse
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

    def parse_json(self):
        """

        Parses Response As JSON DICT

        :return: dict
        """
        return parse_json(self.text)
