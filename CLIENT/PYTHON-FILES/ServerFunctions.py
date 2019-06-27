from utils import download_website, download_json
from log import stopped

DefaultHeaders = {'Client': 'PYTHON-CLIENT'}
useHTTPS = False


def check_server(ip, port):
    global useHTTPS
    html_reply = download_website("http://" + ip + ":" + port + "/", Headers=DefaultHeaders)
    if html_reply == 504:
        html_reply = download_website("https://" + ip + ":" + port + "/", Headers=DefaultHeaders)
        if type(html_reply) is not str:
            return False
        useHTTPS = True
    if type(html_reply) is not str:
        return False
    return True


def add_channel(ip, port, channel_id):
    html_reply = download_website(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/addChannel?channel_id=" + channel_id,
                                  Headers=DefaultHeaders)
    if "OK" in html_reply:
        return [True, html_reply]
    return [False, html_reply]


def remove_channel(ip, port, channel_id):
    html_reply = download_website(("https://" if useHTTPS else 'http://') + ip + ":" + port +
                                  "/removeChannel?channel_id=" + channel_id, Headers=DefaultHeaders)
    if "OK" in html_reply:
        return [True, html_reply]
    return [False, html_reply]


def get_channel_info(ip, port):
    html_reply = download_json(("https://" if useHTTPS is True else 'http://') + ip + ":" + port + "/channelInfo",
                               Headers=DefaultHeaders)
    return html_reply


def get_settings(ip, port):
    html_reply = download_json(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/getQuickSettings",
                               Headers=DefaultHeaders)
    return html_reply


def swap_settings(ip, port, setting_name):
    html_reply = download_website(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/swap/" + setting_name,
                                  Headers=DefaultHeaders,
                                  RequestMethod='POST')
    return html_reply


def get_youtube_settings(ip, port):
    html_reply = download_json(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/getUploadSettings",
                               Headers=DefaultHeaders)
    return html_reply


def get_youtube_info(ip, port):
    html_reply = download_json(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/getUploadInfo",
                               Headers=DefaultHeaders)
    return html_reply


def youtube_login(ip, port):
    html_reply = download_website(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/getLoginURL",
                                  Headers=DefaultHeaders)
    return html_reply


def youtube_logout(ip, port):
    html_reply = download_website(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/logout",
                                  Headers=DefaultHeaders)
    return html_reply


def test_upload(ip, port, channel_id):
    html_reply = download_website(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/testUpload?channel_id=" +
                                                              channel_id,
                                  Headers=DefaultHeaders)
    if "OK" in html_reply:
        return [True, html_reply]
    return [False, html_reply]


def youtube_fully_login(ip, port, username, password):
    html_reply = download_website(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/youtubeLOGIN?username="
                                                              + username +
                                  '&password=' + password,
                                  Headers=DefaultHeaders)
    if "OK" in html_reply:
        return [True, html_reply]
    return [False, html_reply]


def youtube_fully_logout(ip, port):
    html_reply = download_website(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/youtubeLOGout",
                                  Headers=DefaultHeaders)
    if "OK" in html_reply:
        return [True, html_reply]
    return [False, html_reply]


def listRecordings(ip, port):
    html_reply = download_json(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/listRecordings",
                               Headers=DefaultHeaders)
    return html_reply


def playbackRecording(ip, port, RecordingName):
    from encoder import FFplay
    try:
        from urllib.parse import urlencode
    except ImportError:
        stopped("Unsupported version of Python. You need Version 3 :<")
    FFplay = FFplay(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/playStream?" + urlencode({'stream_name': RecordingName}),
                    Headers=DefaultHeaders)
    FFplay.start_playback()
    return FFplay


def downloadRecording(ip, port, RecordingName):
    from encoder import FFmpeg
    try:
        from urllib.parse import urlencode
    except ImportError:
        stopped("Unsupported version of Python. You need Version 3 :<")
    FFmpeg = FFmpeg(("https://" if useHTTPS else 'http://') + ip + ":" + port + "/playStream?" + urlencode({'stream_name': RecordingName}),
                    RecordingName, Headers=DefaultHeaders)
    FFmpeg.start_recording()
    return FFmpeg
