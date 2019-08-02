from utils import download_website, download_json
from log import stopped

DefaultHeaders = {'Client': 'PYTHON-CLIENT'}
useHTTPS = False

try:
    from urllib.parse import urlencode
except ImportError:
    urlencode = None
    stopped("Unsupported version of Python. You need Version 3 :<")


def check_server(ip, port):
    global useHTTPS
    html_reply = download_website("http://" + ip + ":" + port + "/", Headers=DefaultHeaders)
    if html_reply == 504:
        html_reply = download_website("https://" + ip + ":" + port + "/", Headers=DefaultHeaders)
        if html_reply == 2:
            stopped("Certificate verify failed. Hostname mismatch, certificate is not valid for '{0}'".format(ip))
        if type(html_reply) is not str:
            return False
        useHTTPS = True
    if type(html_reply) is not str:
        return False
    return True


def __server_reply(ip, port, function_name, arguments, RequestMethod='GET'):
    def format_response():
        if dict_json is None:
            stopped("Lost Connection of the Server!")
        if "OK" in dict_json['status']:
            return [True, dict_json['response']]
        return [False, dict_json['response']]

    dict_json = download_json('{0}{1}:{2}/{3}?{4}'.format((
        "https://" if useHTTPS else 'http://'), ip, port, function_name, urlencode(arguments)), Headers=DefaultHeaders,
        RequestMethod=RequestMethod)
    return format_response()


def add_channel(ip, port, channel_id):
    function_name = 'addChannel'
    arguments = {'channel_id': channel_id}
    return __server_reply(ip, port, function_name, arguments)


def remove_channel(ip, port, channel_id):
    function_name = 'removeChannel'
    arguments = {'channel_id': channel_id}
    return __server_reply(ip, port, function_name, arguments)


def get_channel_info(ip, port):
    function_name = 'channelInfo'
    arguments = {}
    return __server_reply(ip, port, function_name, arguments)


def get_server_settings(ip, port):
    function_name = 'getServerSettings'
    arguments = {}
    return __server_reply(ip, port, function_name, arguments)


def swap_settings(ip, port, setting_name):
    function_name = 'swap/{0}'.format(setting_name)
    arguments = {}
    return __server_reply(ip, port, function_name, arguments, RequestMethod='POST')


def get_youtube_api_info(ip, port):
    function_name = 'getYouTubeAPIInfo'
    arguments = {}
    return __server_reply(ip, port, function_name, arguments)


def youtube_login(ip, port):
    function_name = 'getLoginURL'
    arguments = {}
    return __server_reply(ip, port, function_name, arguments)


def youtube_logout(ip, port):
    function_name = 'logoutYouTubeAPI'
    arguments = {}
    return __server_reply(ip, port, function_name, arguments)


def test_upload(ip, port, channel_id):
    function_name = 'testUpload'
    arguments = {'channel_id': channel_id}
    return __server_reply(ip, port, function_name, arguments)


def youtube_fully_login(ip, port, username, password):
    function_name = 'youtubeLOGIN'
    arguments = {'username': username, 'password': password}
    return __server_reply(ip, port, function_name, arguments)


def update_data_cache(ip, port):
    function_name = 'updateDataCache'
    arguments = {}
    return __server_reply(ip, port, function_name, arguments)


def youtube_fully_logout(ip, port):
    function_name = 'youtubeLOGout'
    arguments = {}
    return __server_reply(ip, port, function_name, arguments)


def listRecordings(ip, port):
    function_name = 'listRecordings'
    arguments = {}
    return __server_reply(ip, port, function_name, arguments)


def playbackRecording(ip, port, RecordingName):
    from encoder import FFplay
    try:
        from urllib.parse import urlencode
    except ImportError:
        stopped("Unsupported version of Python. You need Version 3 :<")
    FFplay = FFplay(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/playRecording?" + urlencode(
        {'stream_name': RecordingName}),
                    Headers=DefaultHeaders)
    FFplay.start_playback()
    return FFplay


def downloadRecording(ip, port, RecordingName):
    from encoder import FFmpeg
    try:
        from urllib.parse import urlencode
    except ImportError:
        stopped("Unsupported version of Python. You need Version 3 :<")
    FFmpeg = FFmpeg(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/playRecording?" + urlencode(
        {'stream_name': RecordingName}),
                    RecordingName, Headers=DefaultHeaders)
    FFmpeg.start_recording()
    return FFmpeg
