from threading import Thread
from time import sleep

from flask import request, redirect, Flask, url_for, jsonify

from . import run_channel, channel_main_array, upload_test_run, google_account_login, is_google_account_login_in, \
    google_account_logout
from .utils.windowsNotification import show_windows_toast_notification
from .dataHandler import add_channel_config, DownloadThumbnail, loadData, saveData, UploadVideos, save_username, \
    save_credentials, clear_credentials, get_username, remove_channel_config
from .log import info


# THIS FILE CONTAINS SERVER RELATED STUFF

def Response(response, status="OK", status_code=200):
    """

    Allows a custom json formatted response.

    :type response: str, None
    :type status: str
    :type status_code: int
    """
    json_dict = {
        'status': status,
        'response': response,
        'status_code': status_code
    }
    return jsonify(json_dict), status_code


class FlaskCustom(Flask):
    def process_response(self, response):
        # Allows more security. People won't see the Web Server in the headers.
        if 'Client' in request.headers:
            response.headers['Server'] = 'ChannelArchiver Server'
        return response


app = FlaskCustom(__name__)


def loadServer(port, cert=None, key=None):
    sleep(1.5)
    try:
        from gevent.pywsgi import WSGIServer as WSGIServer
    except ImportError:
        WSGIServer = None
    if WSGIServer is None:
        info("To disable this warning, install gevent pip package!")
        ssl_context = ((cert, key) if cert and key else None)
        app.run(host='0.0.0.0', threaded=True, port=port, ssl_context=ssl_context)
    else:
        if cert and key:
            http_server = WSGIServer(('', port), app, certfile=cert, keyfile=key,
                                     server_side=True)
        else:
            http_server = WSGIServer(('', port), app)
        info("Server started. Hosted on port: {0}".format(port) + "!")
        show_windows_toast_notification("ChannelArchiver Server", "ChannelArchiver server started")
        http_server.serve_forever()


@app.before_request
def before_request():
    # This is used mostly for security. This can be easily broken
    if 'Client' not in request.headers:
        rule = request.url_rule
        if rule is not None:
            url = rule.rule
            if not ('login' in url and request.args.get('unlockCode') is not None) and 'callback' not in url:
                return '', 403


@app.route('/')
def hello():
    return Response("Server is alive.")


@app.route('/addChannel')
def add_channel():
    channel_id = request.args.get('channel_id')
    if channel_id is None:
        return Response("You need Channel_ID in args.", status="client-error", status_code=400)
    channel_array = [channel_ for channel_ in channel_main_array
                     if channel_id.casefold() == channel_['class'].get('channel_name').casefold() or
                     channel_id.casefold() == channel_['class'].get('channel_id').casefold()]
    if len(channel_array) is not 0:
        return Response("Channel Already in list!", status="server-error", status_code=500)
    del channel_array
    ok, message = run_channel(channel_id)
    if ok:
        add_channel_config(channel_id)  # NEEDS TO ADD CHANNEL TO CONFIG
        info(channel_id + " has been added to the list of channels.")
        return Response(None)
    else:
        return Response(message, status="server-error", status_code=500)


@app.route('/removeChannel')
def remove_channel():
    channel_id = request.args.get('channel_id')
    if channel_id is None:
        return Response("You need Channel_ID in args.", status="client-error", status_code=400)

    channel_array = [channel_ for channel_ in channel_main_array
                     if channel_id.casefold() == channel_['class'].get('channel_name').casefold() or
                     channel_id.casefold() == channel_['class'].get('channel_id').casefold()]
    if channel_array is None or len(channel_array) is 0:
        return Response(channel_id + " hasn't been added to the channel list, so it can't be removed.",
                        status="server-error", status_code=500)
    channel_array = channel_array[0]
    if 'error' not in channel_array:
        print(channel_array['class'].get('channel_id'))
        channel_array['class'].close()
        thread_class = channel_array['thread_class']
        try:
            thread_class.terminate()
            sleep(1.0)
            if thread_class.is_alive():
                thread_class.close()
                return Response("Unable to Terminate.", status_code="server-error", status=500)
        except Exception as e:
            return Response("Cannot Remove Channel. " + str(e), status_code="server-error", status=500)
    remove_channel_config(channel_array['class'].get('channel_id'))
    channel_main_array.remove(channel_array)
    sleep(.01)
    info(channel_id + " has been removed.")
    del channel_array
    return Response(None)


@app.route('/channelInfo')
def channelInfo():
    json = {
        'YoutubeLogin': is_google_account_login_in(),
        'channels': [],
        'channel': {}
    }

    for channel in channel_main_array:
        channel_class = channel['class']
        json['channels'].append(channel['class'].get('channel_id'))
        json['channel'].update({
            channel_class.get('channel_id'): {
                'name': channel_class.get('channel_name'),
                'live': channel_class.get('live_streaming'),
                'video_id': channel_class.get('video_id'),
                'recording_status': channel_class.get('recording_status'),
                'privateStream': channel_class.get('privateStream'),
                'live_scheduled': channel_class.get('live_scheduled'),
                'live_scheduled_time': channel_class.get('live_scheduled_time'),
                'broadcastId': channel_class.get('broadcastId'),
                'sponsor_on_channel': channel_class.get('sponsor_on_channel'),
                'last_heartbeat': channel_class.get('last_heartbeat').strftime("%I:%M %p")
                if channel_class.get('last_heartbeat') is not None else None,
            }
        })
        if 'error' in channel:
            json['channel'][channel['class'].get('channel_id')].update({
                'error': channel['error'],
            })
    return Response(json)


# CHANGING SETTINGS
@app.route('/getQuickSettings')
def getQuickSetting():
    json = {
        'settings': {
            'DownloadThumbnail': DownloadThumbnail()
        }
    }
    return Response(json)


@app.route('/swap/DownloadThumbnail', methods=['GET', 'POST'])
def swapDownloadThumbnail():
    if request.method == 'GET':
        return Response("Bad Request. You may want to update your client!", status='client-error',
                        status_code=400)
    if request.method == 'POST':
        yaml_config = loadData()
        if 'DownloadThumbnail' not in yaml_config:
            return Response("Failed to find DownloadThumbnail in data file. It's really broken. :P",
                            status="server-error", status_code=500)
        if yaml_config['DownloadThumbnail'] is True:
            yaml_config['DownloadThumbnail'] = False
        elif yaml_config['DownloadThumbnail'] is False:
            yaml_config['DownloadThumbnail'] = True

        info('DownloadThumbnail has been set to: ' + str(yaml_config['DownloadThumbnail']))
        saveData(yaml_config)
        del yaml_config
        return Response(None)


# For Upload Settings
@app.route('/getUploadSettings')
def getUploadSetting():
    json = {
        'settings': {
            'UploadLiveStreams': UploadVideos(),
            'DownloadThumbnail': DownloadThumbnail()
        }
    }
    return Response(json)


# TODO CHANGE STATE VARIABLE TO session['state']
state = None


# LOGGING INTO YOUTUBE (FOR UPLOADING)

@app.route('/getLoginURL')
def youtube_get_login_url():
    from flask import Response, url_for
    url = url_for('YoutubeLogin', _external=True) + "?unlockCode=" + "OK"
    return Response(url)


state = None


@app.route('/login')
def youtube_login():
    from .youtubeAPI import does_account_exists, get_account_login_in_link
    if does_account_exists():
        return Response("Youtube account already logged-in", mimetype='text/plain', status=500)
    url = url_for('YoutubeLoginCallBack', _external=True)
    global state
    link, state = get_account_login_in_link(url)
    return redirect(link)


@app.route('/login/callback')
def youtube_login_call_back():
    from .youtubeAPI import credentials_build, get_youtube_account_user_name, redirect_credentials
    authorization_response = request.url
    global state
    url = url_for('YoutubeLoginCallBack', _external=True)
    credentials = redirect_credentials(authorization_response, state, url)
    username = get_youtube_account_user_name(credentials_build(credentials))
    save_username(username)
    save_credentials(credentials)
    state = None
    return Response(None)


@app.route('/logout')
def youtube_log_out():
    if clear_credentials() is True:
        return Response(None)
    else:
        return Response("There are no Youtube Account logged-in, to log out.",
                        status="server-error", status_code=500)


# For Getting Login-in Youtube Account info
@app.route('/getUploadInfo')
def YoutubeLoginInfo():
    from .youtubeAPI import does_account_exists
    json = {
        'info': {
            'YoutubeAccountName': get_username(),
            'YoutubeAccountLogin-in': does_account_exists(),
        }
    }
    return Response(json)


# Test Uploading
@app.route('/testUpload')
def YoutubeTestUpload():
    channel_id = request.args.get('channel_id')
    if channel_id is None:
        return Response("You need Channel_ID in args.", mimetype='text/plain', status=500)
    ok, message = upload_test_run(channel_id)
    if ok:
        info(channel_id + " has been added for test uploading.")
        return Response(None)
    else:
        return Response(message, status="server-error", status_code=500)


@app.route('/youtubeLOGIN')
def Youtube_Login_FULLY():
    username = request.args.get('username')
    password = request.args.get('password')
    if username is None or password is None:
        return Response("You need username and password in args.", mimetype='text/plain', status=500)
    ok, message = google_account_login(username, password)
    if ok:
        return Response(None)
    else:
        return Response(message, status="server-error", status_code=500)


@app.route('/youtubeLOGout')
def Youtube_Logout_FULLY():
    ok, message = google_account_logout()
    if ok:
        return Response(None)
    else:
        return Response(message, status="server-error", status_code=500)


# Playback recordings and downloading them.

@app.route('/listRecordings')
def listStreams():
    from os import path, getcwd, walk
    recorded_streams_dir = path.join(getcwd(), "RecordedStreams")
    list_recordings = []
    for (dir_path, dir_names, file_names) in walk(recorded_streams_dir):
        for file_name in file_names:
            if 'mp4' in file_name:
                list_recordings.append(file_name)
    return Response(list_recordings)


@app.route('/playStream')
def uploadVideo():
    stream_name = request.args.get('stream_name')
    if stream_name is None:
        return Response("You need stream_name in args.", mimetype='text/plain', status=500)
    from os import path, getcwd
    stream_folder = path.join(getcwd(), "RecordedStreams")
    from flask import send_from_directory
    return send_from_directory(directory=stream_folder, filename=stream_name)


# CUSTOM MESSAGES
def server_internal_error(e):
    return Response("The server encountered an internal error and was unable to complete your request.",
                    status="server-error", status_code=500)


def unable_to_find(e):
    return Response("The requested URL was not found on this server.",
                    status="client-error", status_code=404)


def run_server(port, cert=None, key=None):
    app.register_error_handler(500, server_internal_error)
    app.register_error_handler(404, unable_to_find)
    load_server_thread = Thread(target=loadServer,
                                name="Server Thread",
                                args=(port, cert, key,))
    load_server_thread.daemon = True  # needed control+C to work.
    load_server_thread.start()
