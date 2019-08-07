import ipaddress
import os
import traceback
from os import path, getcwd
from time import sleep

import requests
from flask import request, redirect, Flask, url_for, jsonify, send_from_directory, session

from . import run_channel, channel_main_array, upload_test_run, google_account_login, is_google_account_login_in, \
    google_account_logout, run_youtube_queue_thread, stop_youtube_queue_thread, run_channel_with_video_id
from .log import info, error_warning
from .utils.windowsNotification import show_windows_toast_notification


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
app.secret_key = 'a good key.'

cached_data_handler = None


def loadServer(cached_data_handler_, port, cert=None, key=None):
    # Global Variables.
    global cached_data_handler
    cached_data_handler = cached_data_handler_

    # Importing cached data handler before setting up shared, imports None.
    # This is to fix that problem.
    app.register_error_handler(500, server_internal_error)
    app.register_error_handler(404, unable_to_find)
    try:
        from gevent.pywsgi import WSGIServer as WSGIServer
    except ImportError:
        WSGIServer = None
    if WSGIServer is None:
        info("To disable this warning, install gevent pip package!")
        ssl_context = ((cert, key) if cert and key else None)
        app.run(host='0.0.0.0', threaded=True,
                port=port, ssl_context=ssl_context)
    else:
        if cert and key:
            http_server = WSGIServer(('', port), app, certfile=cert, keyfile=key,
                                     server_side=True)
        else:
            http_server = WSGIServer(('', port), app)
        info("Server started. Hosted on port: {0}!".format(port))
        show_windows_toast_notification(
            "ChannelArchiver Server", "ChannelArchiver server started")
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
    if channel_id is '':
        return Response('You need to specify a valid channel id.', status='client-error', status_code=400)
    channel_array = [channel_ for channel_ in channel_main_array
                     if channel_id.casefold() == channel_['class'].get('channel_name').casefold() or
                     channel_id.casefold() == channel_['class'].get('channel_id').casefold()]
    if len(channel_array) is not 0:
        return Response("Channel Already in list!", status="server-error", status_code=500)
    del channel_array
    ok, message = run_channel(channel_id, addToData=True)
    if ok:
        info("{0} has been added to the list of channels.".format(channel_id))
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
        return Response("{0} hasn't been added to the channel list, so it can't be removed.".format(channel_id),
                        status="server-error", status_code=500)
    channel_array = channel_array[0]
    if 'error' not in channel_array:
        channel_array['class'].close()
        thread_class = channel_array['thread_class']
        try:
            thread_class.terminate()
            sleep(1.0)
            if thread_class.is_alive():
                return Response("Unable to Terminate.", status="server-error", status_code=500)
        except Exception as e:
            error_warning(traceback.format_exc())
            return Response("Unable to remove channel. {0}".format(str(e)), status="server-error", status_code=500)
    cached_data_handler.removeValueList('channel_ids', channel_array['class'].get('channel_id'))
    channel_main_array.remove(channel_array)
    sleep(.01)
    info("{0} has been removed.".format(channel_id))
    del channel_array
    return Response(None)


@app.route('/addVideoID')
def add_video_id():
    video_id = request.args.get('video_id')
    if video_id is None:
        return Response("You need VIDEO_ID in args.", status="client-error", status_code=400)
    if video_id is '':
        return Response('You need to specify a valid video id.', status='client-error', status_code=400)
    channel_array = [channel_ for channel_ in channel_main_array
                     if video_id == channel_['class'].get('video_id') or
                     video_id == channel_['class'].get('video_id')]
    if len(channel_array) is not 0:
        return Response("Video Already in list!", status="server-error", status_code=500)
    del channel_array
    ok, message = run_channel_with_video_id(video_id, addToData=True)
    if ok:
        return Response(None)
    else:
        return Response(message, status="server-error", status_code=500)


@app.route('/serverInfo')
def serverInfo():
    channelInfo = {
        'channel': {}
    }
    for channel in channel_main_array:
        channel_class = channel['class']
        process_class = channel['thread_class']
        channelInfo['channel'].update({channel_class.get('channel_id'): {}})
        if 'error' in channel:
            channelInfo['channel'][channel_class.get('channel_id')].update({
                'error': channel['error'],
            })
        else:
            channelInfo['channel'][channel_class.get('channel_id')].update({
                'name': channel_class.get('channel_name'),
                'is_alive': process_class.is_alive() if process_class is not None else False,
            })
            if process_class.is_alive():
                channelInfo['channel'][channel_class.get('channel_id')].update({
                    'video_id': channel_class.get('video_id'),
                    'live': channel_class.get('live_streaming'),
                    'privateStream': channel_class.get('privateStream'),
                    'live_scheduled': channel_class.get('live_scheduled'),
                    'broadcastId': channel_class.get('broadcastId'),
                    'sponsor_on_channel': channel_class.get('sponsor_on_channel'),
                    'last_heartbeat': channel_class.get('last_heartbeat').strftime("%I:%M %p")
                    if channel_class.get('last_heartbeat') is not None else None,
                })
                if channel_class.get('live_streaming') is True:
                    channelInfo['channel'][channel_class.get('channel_id')].update({
                        'recording_status': channel_class.get('recording_status')
                    })
                if channel_class.get('live_scheduled') is True:
                    channelInfo['channel'][channel_class.get('channel_id')].update({
                        'live_scheduled_time': channel_class.get('live_scheduled_time')
                    })
            elif not process_class.is_alive():
                channelInfo['channel'][channel_class.get('channel_id')].update({
                    'crashed_traceback': channel_class.get('crashed_traceback')
                })
    from . import uploadThread, queue_holder
    uploadQueue = {
        'enabled': cached_data_handler.getValue('UploadLiveStreams'),
        'is_alive': uploadThread.is_alive() if uploadThread is not None else None,
    }
    if uploadThread:
        uploadQueue.update({'status': queue_holder.getStatus()})
    return Response({
        'channelInfo': channelInfo,
        'youtube': {'YoutubeLogin': is_google_account_login_in()},
        'youtubeAPI': {
            'uploadQueue': uploadQueue
        },
    })


@app.route('/swap/<name>', methods=['GET', 'POST'])
def swapDownloadThumbnail(name):
    if request.method == 'GET':
        return Response("Bad Request. You may want to update your client!", status='client-error',
                        status_code=400)
    if request.method == 'POST':
        if name not in cached_data_handler.getDict():
            return Response("Failed to find {0} in data file. It's really broken. :P".format(name),
                            status="server-error", status_code=500)

        if type(cached_data_handler.getValue(name)) is bool:
            swap_value = (not cached_data_handler.getValue(name))
            if name == "UploadLiveStreams":
                # Check for client secret file before doing something that uses the YouTube API.
                if cached_data_handler.getValue(name) is False:
                    CLIENT_SECRETS_FILE = os.path.join(
                        os.getcwd(), "client_id.json")
                    if not path.exists(CLIENT_SECRETS_FILE):
                        return Response(
                            "WARNING: Please configure OAuth 2.0. \nInformation at the Developers Console "
                            "https://console.developers.google.com/", status='server-error', status_code=500)
                # RUN QUEUE THREAD WHEN ENABLED>
                if swap_value:
                    okay = run_youtube_queue_thread(skipValueCheck=True)
                    if not okay:
                        return Response('Unable to start upload Queue Thread.',
                                        status="server-error", status_code=500)
                if not swap_value:
                    okay = stop_youtube_queue_thread()
                    if not okay:
                        return Response('Unable to stop upload Queue Thread.',
                                        status="server-error", status_code=500)
            cached_data_handler.setValue(name, swap_value)
        else:
            return Response('Value is not a bool. Cannot invert type, {0}.'.format(
                str(type(cached_data_handler.getValue(name)))))

        info('{0} has been set to: {1}'.format(
            name, str(cached_data_handler.getValue(name))))
        return Response(None)


# For Upload Settings
@app.route('/getServerSettings')
def getSetting():
    json = {
        'DownloadThumbnail': {'value': cached_data_handler.getValue('DownloadThumbnail'),
                              'description': 'Downloads the thumbnail from the original stream.',
                              'type': 'swap'},
        'UploadLiveStreams': {'value': cached_data_handler.getValue('UploadLiveStreams'),
                              'description':
                                  'Auto uploads recorded YouTube Live streams to YouTube using the YouTube API.',
                              'type': 'swap'},
        'UploadThumbnail': {'value': cached_data_handler.getValue('UploadThumbnail'),
                            'description':
                                'Uploads the thumbnail from the original stream to the auto uploaded YouTube version.',
                            'type': 'swap'},
        'YouTube API LOGIN': {'value': 'youtube_api_credentials' in cached_data_handler.getDict(),
                              'description':
                                  'Login to the YouTube API to upload the auto uploads to your '
                                  'channel.',
                              'type': 'youtube_api_login', 'AccountName':
                                  cached_data_handler.getValue('youtube_api_account_username')},
        'YouTube API Test Upload': {'value': None, 'description': 'Records a channel for a few seconds. '
                                                                  'Then tries uploading that through the YouTube API.',
                                    'type': 'channel_id'},
        'Refresh Data File Cache': {'value': None, 'description': 'Refreshes the cache created from the data.yml file.',
                                    'type': 'refresh_data_cache'}
    }
    return Response(json)


# For Getting Login-in Youtube Account info
@app.route('/getYouTubeAPIInfo')
def YoutubeAPILoginInfo():
    """

    RIGHT NOW USELESS, BUT CAN BE USED IN YOUR OWN CLIENTS ;)

    """
    json = {
        'YoutubeAccountName': {'value': cached_data_handler.getValue('youtube_api_account_username')},
        'YoutubeAccountLogin-in': {'value': 'youtube_api_credentials' in cached_data_handler.getDict(),
                                   'description': 'Login to the YouTube API to upload the auto uploads to your channel.'},
    }
    return Response(json)


# For Getting Login-in Youtube Account info
@app.route('/updateDataCache')
def updateDataCache():
    cached_data_handler.updateCache()
    return Response(None)


# LOGGING INTO YOUTUBE (FOR UPLOADING)
@app.route('/getLoginURL')
def youtube_get_login_url():
    url = "{0}?unlockCode={1}".format(url_for('youtube_login', _external=True), "OK")
    return Response(url)


@app.route('/login')
def youtube_login():
    # Check for client secret file...
    CLIENT_SECRETS_FILE = os.path.join(os.getcwd(), "client_id.json")
    if not path.exists(CLIENT_SECRETS_FILE):
        return Response("WARNING: Please configure OAuth 2.0. Information at the Developers Console "
                        "https://console.developers.google.com/", status='server-error', status_code=500)
    from .youtubeAPI import get_youtube_api_login_link
    if 'youtube_api_credentials' in cached_data_handler.getDict():
        return Response("Youtube account already logged-in", status='client-error', status_code=400)
    url = url_for('youtube_login_call_back', _external=True)
    is_private_ip = ipaddress.ip_address(request.remote_addr).is_private
    link, session['state'] = get_youtube_api_login_link(url, cached_data_handler, isPrivateIP=is_private_ip)
    return redirect(link)


@app.route('/login/callback')
def youtube_login_call_back():
    from .youtubeAPI import credentials_build, get_youtube_account_user_name, get_request_credentials
    authorization_response = request.url
    state = session.get('state')
    url = url_for('youtube_login_call_back', _external=True)
    try:
        credentials = get_request_credentials(authorization_response, state, url)
        username = get_youtube_account_user_name(credentials_build(credentials))
    except requests.exceptions.SSLError:
        return Response("The server encountered an SSL error and was unable to complete your request.",
                        status='server-error', status_code=500)
    cached_data_handler.setValue('youtube_api_account_username', username)
    cached_data_handler.setValue('youtube_api_credentials', credentials)
    session.pop('state', None)
    return Response(None)


@app.route('/logoutYouTubeAPI')
def youtube_log_out():
    if 'youtube_api_credentials' in cached_data_handler.getDict():
        cached_data_handler.deleteKey('youtube_api_credentials')
        return Response(None)
    else:
        return Response("There are no Youtube Account logged-in, to log out.",
                        status="server-error", status_code=500)


# Test Uploading
@app.route('/testUpload')
def YoutubeTestUpload():
    channel_id = request.args.get('channel_id')
    if channel_id is None:
        return Response("You need Channel_ID in args.", status='client-error', status_code=400)
    ok, message = upload_test_run(channel_id)
    if ok:
        info("{0} has been added for test uploading.".format(channel_id))
        return Response(None)
    else:
        return Response(message, status="server-error", status_code=500)


@app.route('/youtubeLOGIN')
def Youtube_Login_FULLY():
    username = request.args.get('username')
    password = request.args.get('password')
    if username is None or password is None:
        return Response("You need username and password in args.", status='client-error', status_code=400)
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


# Playback recordings / downloading them.

@app.route('/listRecordings')
def listStreams():
    from os import walk
    recorded_streams_dir = path.join(getcwd(), "RecordedStreams")
    list_recordings = []
    for (dir_path, dir_names, file_names) in walk(recorded_streams_dir):
        for file_name in file_names:
            if 'mp4' in file_name:
                list_recordings.append(file_name)
    return Response(list_recordings)


@app.route('/playRecording')
def uploadVideo():
    stream_name = request.args.get('stream_name')
    if stream_name is None:
        return Response("You need stream_name in args.", status='client-error', status_code=400)
    stream_folder = path.join(getcwd(), "RecordedStreams")
    return send_from_directory(directory=stream_folder, filename=stream_name)


# CUSTOM MESSAGES
def server_internal_error(e):
    return Response("The server encountered an internal error and was unable to complete your request.",
                    status="server-error", status_code=500)


def unable_to_find(e):
    return Response("The requested URL was not found on this server.",
                    status="client-error", status_code=404)
