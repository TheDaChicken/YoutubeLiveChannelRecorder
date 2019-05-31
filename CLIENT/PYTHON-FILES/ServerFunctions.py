from utils import download_website, download_json

DefaultHeaders = {'Client': 'PYTHON-CLIENT'}


def check_server(ip, port):
    html_reply = download_website("http://" + ip + ":" + port + "/", Headers=DefaultHeaders)
    if type(html_reply) is not str:
        return False
    return True


def add_channel(ip, port, channel_id):
    html_reply = download_website("http://" + ip + ":" + port + "/addChannel?channel_id=" + channel_id,
                                  Headers=DefaultHeaders)
    if "OK" in html_reply:
        return [True, html_reply]
    return [False, html_reply]


def remove_channel(ip, port, channel_id):
    html_reply = download_website("http://" + ip + ":" + port + "/removeChannel?channel_id=" + channel_id,
                                  Headers=DefaultHeaders)
    if "OK" in html_reply:
        return [True, html_reply]
    return [False, html_reply]


def get_channel_info(ip, port):
    html_reply = download_json("http://" + ip + ":" + port + "/channelInfo", Headers=DefaultHeaders)
    return html_reply


def get_settings(ip, port):
    html_reply = download_json("http://" + ip + ":" + port + "/getQuickSettings", Headers=DefaultHeaders)
    return html_reply


def swap_settings(ip, port, setting_name):
    html_reply = download_website("http://" + ip + ":" + port + "/swap/" + setting_name, Headers=DefaultHeaders,
                                  RequestMethod='POST')
    return html_reply


def get_youtube_settings(ip, port):
    html_reply = download_json("http://" + ip + ":" + port + "/getUploadSettings", Headers=DefaultHeaders)
    return html_reply


def get_youtube_info(ip, port):
    html_reply = download_json("http://" + ip + ":" + port + "/getUploadInfo", Headers=DefaultHeaders)
    return html_reply


def youtube_login(ip, port):
    html_reply = download_website("http://" + ip + ":" + port + "/getLoginURL", Headers=DefaultHeaders)
    return html_reply


def youtube_logout(ip, port):
    html_reply = download_website("http://" + ip + ":" + port + "/logout", Headers=DefaultHeaders)
    return html_reply


def test_upload(ip, port, channel_id):
    html_reply = download_website("http://" + ip + ":" + port + "/testUpload?channel_id=" + channel_id,
                                  Headers=DefaultHeaders)
    if "OK" in html_reply:
        return [True, html_reply]
    return [False, html_reply]
