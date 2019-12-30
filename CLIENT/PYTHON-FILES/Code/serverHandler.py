from Code.log import stopped, Fore
from Code.utils.web import download_website

try:
    from urllib.parse import urlencode
except ImportError:
    urlencode = None

Headers = {'User-Agent': 'WEB-CLIENT'}


def isServerOnline(ip, port):
    downloadClass = server_reply(ip, port, '', {}, httpMethod='http://', returnDownloadClass=True)
    return downloadClass.text is not None


def server_reply(ip, port, function_name, arguments, RequestMethod='GET', httpMethod=None,
                 returnDownloadClass=False):
    def format_response():
        if "OK" in dict_json['status']:
            return [True, dict_json['response']]
        return [False, dict_json['response']]

    if not httpMethod:
        httpMethod = "http://"

    encoded_arguments = '?{0}'.format(urlencode(arguments)) if len(arguments) != 0 else ''
    downloadClass = download_website(
        '{0}{1}:{2}/{3}{4}'.format(httpMethod, ip, port, function_name, encoded_arguments),
        headers=Headers, RequestMethod=RequestMethod)
    if returnDownloadClass:
        return downloadClass
    if downloadClass.text:
        dict_json = downloadClass.parse_json()
        if dict_json is None:
            return [False, "Invalid Response from Server: {1}".format(Fore.LIGHTRED_EX, downloadClass.text)]
        return format_response()
    if not downloadClass.text:
        return [None, "Cannot connect to server."]
