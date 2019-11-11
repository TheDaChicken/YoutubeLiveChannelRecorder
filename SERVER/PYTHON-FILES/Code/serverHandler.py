import os
import traceback
from os import path, getcwd
from time import sleep

import requests
from flask import request, redirect, Flask, url_for, jsonify, send_from_directory, session, make_response

import ipaddress
from . import run_channel, channel_main_array, upload_test_run, google_account_login, is_google_account_login_in, \
    google_account_logout, run_youtube_queue_thread, stop_youtube_queue_thread, run_channel_with_video_id
from .log import info, error_warning
from .utils.windowsNotification import show_windows_toast_notification


# THIS FILE CONTAINS SERVER RELATED STUFF


def Response(response, json_on=True, status="OK", status_code=200, headers=None):
    """

    Allows a custom json formatted response.

    :type response: str, None
    :type status: str
    :type status_code: int
    :type headers: dict
    :type json_on: bool

    """
    if headers is None:
        headers = {}
    if not json_on:
        return response, status_code, headers
    json_dict = {
        'status': status,
        'response': response,
        'status_code': status_code
    }
    return jsonify(json_dict), status_code, headers


class Server(Flask):
    def process_response(self, response):
        # Allows more security. People won't see the Web Server in the headers.
        user_agent = request.headers.get('User-Agent')
        client_header = request.headers.get('Client')
        if (user_agent and 'WEB-CLIENT' in user_agent) or client_header:
            response.headers['Server'] = 'ChannelArchiver Server'
            if client_header:
                response.headers['NOTICE'] = 'You are using an old version of the client. ' \
                                             'Please update the client to the latest version!'
        return response

    def __init__(self, import_name, cached_data_handler):
        super(Server, self).__init__(import_name)

        self.cached_data_handler = cached_data_handler
        self.secret_key = 'a good key.'

        self.register_error_handler(500, self.server_internal_error)
        self.register_error_handler(404, self.unable_to_find)

        self.add_url_rule('/', view_func=self.hello)

        # CHANNEL ADDING/REMOVING RELATED
        self.add_url_rule('/addChannel', view_func=self.old_add_channel)
        self.add_url_rule('/addChannel/<platform_name>', view_func=self.add_channel)
        self.add_url_rule('/removeChannel', view_func=self.remove_channel)
        self.add_url_rule('/addVideoID', view_func=self.add_video_id)

        # Server INFO :P
        self.add_url_rule('/serverInfo', view_func=self.serverInfo)

        # SETTINGS RELATED
        self.add_url_rule('/swap/<name>', view_func=self.swapBooleanValue, methods=['GET', 'POST'])
        self.add_url_rule('/getServerSettings', view_func=self.getSetting)
        self.add_url_rule('/getYouTubeAPIInfo', view_func=self.YoutubeAPILoginInfo)
        self.add_url_rule('/updateDataCache', view_func=self.updateDataCache)
        self.add_url_rule('/recording_at_resolution', view_func=self.recording_at_resolution)

        # YOUTUBE API
        self.add_url_rule('/getLoginURL', view_func=self.youtube_api_get_login_url)
        self.add_url_rule('/login', view_func=self.youtube_api_login)
        self.add_url_rule('/login/callback', view_func=self.youtube_api_login_call_back)
        self.add_url_rule('/logoutYouTubeAPI', view_func=self.youtube_api_log_out)

        # YOUTUBE LOGIN/LOGOUT
        self.add_url_rule('/youtubeLOGIN', view_func=self.Youtube_Login_FULLY)
        self.add_url_rule('/youtubeLOGout', view_func=self.Youtube_Logout_FULLY)

        # RECORDINGS RELATED.
        self.add_url_rule('/listRecordings', view_func=self.listStreams)
        self.add_url_rule('/listStreams', view_func=self.listStreams)

        self.add_url_rule('/playRecording', view_func=self.playRecording)

        self.add_url_rule('/playLiveStream', view_func=self.playLiveStream)
        self.add_url_rule('/MPEG-DASH_init/<filename>', view_func=self.MPEG_DASH_init)
        self.add_url_rule('/MPEG-DASH_segments/<filename>', view_func=self.MPEG_DASH_segments)

        self.add_url_rule('/testUpload', view_func=self.YoutubeTestUpload)

    @staticmethod
    def hello():
        return Response("Server is alive.")

    @staticmethod
    def old_add_channel():
        """
        USED TO HANDLE OLD CLIENTS.
        """
        channel_id = request.args.get('channel_id')
        return redirect(url_for('add_channel', platform_name="YOUTUBE", channel_id=channel_id))

    @staticmethod
    def add_channel(platform_name):
        if 'YOUTUBE' in platform_name:
            channel_id = request.args.get('channel_id')
            print(channel_id)
            if channel_id is None:
                return Response("You need Channel_ID in args.", status="client-error", status_code=400)
            if channel_id is '':
                return Response('You need to specify a valid channel id.', status='client-error', status_code=400)
            channel_array = [channel_ for channel_ in channel_main_array
                             if 'YOUTUBE' in channel_['class'].get('platform')
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
        elif 'TWITCH' in platform_name:
            channel_name = request.args.get('channel_name')
            if channel_name is None:
                return Response("You need Channel_NAME in args.", status="client-error", status_code=400)
            if channel_name is '':
                return Response('You need to specify a valid channel name.', status='client-error', status_code=400)
            # TODO CHECK PLATFORM (JUST IN CASE, WANTED TO RECORD BOTH YOUTUBE AND TWITCH STREAM WITH SAME NAME)
            if len([channel_ for channel_ in channel_main_array
                    if channel_name.casefold() == channel_['class'].get('channel_name').casefold()]) is not 0:
                return Response("Channel Already in list!", status="server-error", status_code=500)
            ok, message = run_channel(channel_name, platform='TWITCH', addToData=True)
            if ok:
                info("{0} has been added to the list of channels.".format(channel_name))
                return Response(None)
            else:
                return Response(message, status="server-error", status_code=500)
        return Response("Unknown platform name.", status="client-error", status_code=404)

    def remove_channel(self):
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
            channel_array['class'].close_recording()
            thread_class = channel_array['thread_class']
            try:
                thread_class.terminate()
                sleep(1.0)
                if thread_class.is_alive():
                    return Response("Unable to Terminate.", status="server-error", status_code=500)
            except Exception as e:
                error_warning(traceback.format_exc())
                return Response("Unable to remove channel. {0}".format(str(e)), status="server-error", status_code=500)
        if 'TWITCH' in channel_array['class'].get('platform'):
            self.cached_data_handler.removeValueList(
                'channels_{0}'.format(channel_array['class'].get('platform')),
                channel_array['class'].get('channel_name'))
        if 'YOUTUBE' in channel_array['class'].get('platform'):
            self.cached_data_handler.removeValueList(
                'channels_{0}'.format(channel_array['class'].get('platform')), channel_array['class'].get('channel_id'))
        channel_main_array.remove(channel_array)
        sleep(.01)
        info("{0} has been removed.".format(channel_id))
        del channel_array
        return Response(None)

    @staticmethod
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

    def serverInfo(self):
        channelInfo = {
            'channel': {}
        }
        for channel in channel_main_array:
            channel_class = channel['class']
            process_class = channel['thread_class']
            channel_id = channel_class.get('channel_id')

            channelInfo['channel'].update({channel_id: {}})
            if 'error' in channel:
                channelInfo['channel'][channel_id].update({
                    'error': channel['error'],
                })
            else:
                channelInfo['channel'][channel_id].update({
                    'name': channel_class.get('channel_name'),
                    'is_alive': process_class.is_alive() if process_class is not None else False,
                    'platform': channel_class.get('platform'),
                })
                if process_class.is_alive():
                    if 'YOUTUBE' in channel_class.get('platform'):
                        channelInfo['channel'][channel_id].update({
                            'video_id': channel_class.get('video_id'),
                            'live': channel_class.get('live_streaming'),
                            'privateStream': channel_class.get('privateStream'),
                            'live_scheduled': channel_class.get('live_scheduled'),
                            'broadcastId': channel_class.get('broadcast_id'),
                            'sponsor_on_channel': channel_class.get('sponsor_on_channel'),
                            'last_heartbeat': channel_class.get('last_heartbeat').strftime("%I:%M %p")
                            if channel_class.get('last_heartbeat') is not None else None,
                        })
                    elif 'TWITCH' in channel_class.get('platform'):
                        channelInfo['channel'][channel_id].update({
                            'broadcast_id': channel_class.get('broadcast_id'),
                            'live': channel_class.get('live_streaming'),
                        })
                    if channel_class.get('live_streaming') is True:
                        channelInfo['channel'][channel_id].update({
                            'recording_status': channel_class.get('recording_status')
                        })
                    if channel_class.get('live_scheduled') is True:
                        channelInfo['channel'][channel_id].update({
                            'live_scheduled_time': channel_class.get('live_scheduled_time')
                        })

                elif not process_class.is_alive():
                    channelInfo['channel'][channel_id].update({
                        'crashed_traceback': channel_class.get('crashed_traceback')
                    })

        # YOUTUBE UPLOAD QUEUE
        from . import uploadThread, queue_holder
        uploadQueue = {
            'enabled': self.cached_data_handler.getValue('UploadLiveStreams'),
            'is_alive': uploadThread.is_alive() if uploadThread is not None else None,
        }
        if uploadThread:
            uploadQueue.update({'status': queue_holder.getStatus()})
            problem_message, last_traceback = queue_holder.getProblemOccurred()
            if problem_message:
                uploadQueue.update({'problem_occurred': {'message': problem_message, 'traceback': last_traceback}})
        return Response({
            'channelInfo': channelInfo,
            'youtube': {'YoutubeLogin': is_google_account_login_in()},
            'youtubeAPI': {
                'uploadQueue': uploadQueue
            },
        })

    def swapBooleanValue(self, name):
        if request.method == 'GET':
            return Response("Bad Request. You may want to update your client!", status='client-error',
                            status_code=400)
        if request.method == 'POST':
            if name not in self.cached_data_handler.getDict():
                return Response("Failed to find {0} in data file. It's really broken. :P".format(name),
                                status="server-error", status_code=500)

            if type(self.cached_data_handler.getValue(name)) is bool:
                swap_value = (not self.cached_data_handler.getValue(name))
                if name == "UploadLiveStreams":
                    # Check for client secret file before doing something that uses the YouTube API.
                    if self.cached_data_handler.getValue(name) is False:
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
                self.cached_data_handler.setValue(name, swap_value)
            else:
                return Response('Value is not a bool. Cannot invert type, {0}.'.format(
                    str(type(self.cached_data_handler.getValue(name)))))

            info('{0} has been set to: {1}'.format(
                name, str(self.cached_data_handler.getValue(name))))
            return Response(None)

    # For Upload Settings
    def getSetting(self):
        json = {
            'DownloadThumbnail': {'value': self.cached_data_handler.getValue('DownloadThumbnail'),
                                  'description': 'Downloads the thumbnail from the original stream.',
                                  'type': 'swap'},
            'UploadLiveStreams': {'value': self.cached_data_handler.getValue('UploadLiveStreams'),
                                  'description':
                                      'Auto uploads recorded YouTube Live streams to YouTube using the YouTube API. '
                                      '(ENABLES YOUTUBE UPLOAD QUEUE)',
                                  'type': 'swap'},
            'UploadThumbnail': {'value': self.cached_data_handler.getValue('UploadThumbnail'),
                                'description': 'Uploads the thumbnail from the original stream'
                                               ' to the auto uploaded YouTube version.',
                                'type': 'swap'},
            'YouTube API LOGIN': {'value': 'youtube_api_credentials' in self.cached_data_handler.getDict(),
                                  'description':
                                      'Login to the YouTube API to upload the auto uploads to your '
                                      'channel.',
                                  'type': 'youtube_api_login', 'AccountName':
                                      self.cached_data_handler.getValue('youtube_api_account_username')},
            'YouTube API Test Upload': {'value': None,
                                        'description':
                                            'Records a channel for a few seconds. '
                                            'Then tries uploading that through the YouTube API.',
                                        'type': 'channel_id'},
            'Refresh Data File Cache': {'value': None,
                                        'description': 'Refreshes the cache created from the data.yml file.',
                                        'type': 'refresh_data_cache'},
            'Recording At': {'value': self.cached_data_handler.getValue('recordingResolution'),
                             'description': 'Changes recording quality. Reduces data usage. '
                                            'If unable to record at quality, will choose available quality.',
                             'type': 'recording_at_resolution'}
        }
        return Response(json)

    # For Getting Login-in Youtube Account info
    def YoutubeAPILoginInfo(self):
        """

        RIGHT NOW USELESS, BUT CAN BE USED IN YOUR OWN CLIENTS ;)

        """
        json = {
            'YoutubeAccountName': {'value': self.cached_data_handler.getValue('youtube_api_account_username')},
            'YoutubeAccountLogin-in': {'value': 'youtube_api_credentials' in self.cached_data_handler.getDict(),
                                       'description':
                                           'Login to the YouTube API to upload the auto uploads to your channel.'},
        }
        return Response(json)

    # Refresh Data Cache.
    def updateDataCache(self):
        self.cached_data_handler.updateCache()
        return Response(None)

    def recording_at_resolution(self):
        resolution = request.args.get('resolution')
        if resolution is None:
            return Response("You need resolution in args.", status='client-error', status_code=400)
        if type(resolution) is str:
            if 'original' in resolution:
                self.cached_data_handler.setValue('recordingResolution', resolution)
            if 'x' in resolution:
                split = resolution.split('x')
                if len(split) != 2:
                    return Response('The given resolution must be a valid resolution.')
                # VERIFY IF NUMBER.
                for number in split:
                    try:
                        int(number)
                    except ValueError:
                        return Response('{0} is not a number!'.format(number))
                self.cached_data_handler.setValue('recordingResolution', resolution)
                return Response("Resolution has been saved.")
        return Response("Resolution should be a str.", status='client-error', status_code=400)

    # LOGGING INTO YOUTUBE (FOR UPLOADING)
    @staticmethod
    def youtube_api_get_login_url():
        url = "{0}?unlockCode={1}".format(url_for('youtube_api_login', _external=True), "OK")
        return Response(url)

    def youtube_api_login(self):
        # Check for client secret file...
        CLIENT_SECRETS_FILE = os.path.join(os.getcwd(), "client_id.json")
        if not path.exists(CLIENT_SECRETS_FILE):
            return Response("WARNING: Please configure OAuth 2.0. Information at the Developers Console "
                            "https://console.developers.google.com/", status='server-error', status_code=500)
        from .youtubeAPI import get_youtube_api_login_link
        if 'youtube_api_credentials' in self.cached_data_handler.getDict():
            return Response("Youtube account already logged-in", status='client-error', status_code=400)
        url = url_for('youtube_api_login_call_back', _external=True)
        is_private_ip = ipaddress.ip_address(request.remote_addr).is_private if request.remote_addr is '::1' else False
        link, session['state'] = get_youtube_api_login_link(url, self.cached_data_handler, isPrivateIP=is_private_ip)
        return redirect(link)

    def youtube_api_login_call_back(self):
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
        self.cached_data_handler.setValue('youtube_api_account_username', username)
        self.cached_data_handler.setValue('youtube_api_credentials', credentials)
        session.pop('state', None)
        return Response(None)

    def youtube_api_log_out(self):
        if 'youtube_api_credentials' in self.cached_data_handler.getDict():
            self.cached_data_handler.deleteKey('youtube_api_credentials')
            return Response(None)
        else:
            return Response("There are no Youtube Account logged-in, to log out.",
                            status="server-error", status_code=500)

    # Test Uploading
    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def Youtube_Logout_FULLY():
        ok, message = google_account_logout()
        if ok:
            return Response(None)
        else:
            return Response(message, status="server-error", status_code=500)

    # Playback recordings / downloading them.
    @staticmethod
    def listStreams():
        rule = request.url_rule
        if 'listRecordings' in rule.rule:
            recorded_streams_dir = path.join(getcwd(), "RecordedStreams")
            list_recordings = []
            for (dir_path, dir_names, file_names) in os.walk(recorded_streams_dir):
                for file_name in file_names:
                    if 'mp4' in file_name:
                        list_recordings.append(file_name)
            list_recordings.sort()
            return Response(list_recordings)
        if 'listStreams' in rule.rule:
            recorded_streams_dir = path.join(getcwd(), "RecordedStreams")
            list_recordings = []
            for (dir_path, dir_names, file_names) in os.walk(recorded_streams_dir):
                for file_name in file_names:
                    if 'mp4' in file_name:
                        list_recordings.append(file_name)
            list_recordings.sort()
            return Response({'recordings': list_recordings, 'live': []})

    @staticmethod
    def playRecording():
        stream_name = request.args.get('stream_name')
        if stream_name is None:
            return Response("You need stream_name in args.", status='client-error', status_code=400)
        stream_folder = path.join(getcwd(), "RecordedStreams")
        return send_from_directory(directory=stream_folder, filename=stream_name)

    @staticmethod
    def playLiveStream():
        stream_id = request.args.get('stream_id')
        if stream_id is None:
            return Response("You need stream_id in args.", status='client-error', status_code=400)
        mpeg_dash_folder = path.join(getcwd(), "MPEG-DASH_manifest_temp")
        if not os.path.exists(mpeg_dash_folder):
            return Response("Unable to find MPEG-DASH manifest.", status='client-error', status_code=404)
        mpeg_dash_manifest = path.join(getcwd(), "MPEG-DASH_manifest_temp", "{0}.mpd".format(stream_id))
        if not os.path.exists(mpeg_dash_manifest):
            return Response("Unable to find MPEG-DASH manifest.", status='client-error', status_code=404)
        f = open(mpeg_dash_manifest, "r")
        contents = f.read()
        f.close()
        return Response(contents, json_on=False, headers={
            'Content-Type': 'video/vnd.mpeg.dash.mpd', 'Cache-Control': 'no-cache, must-revalidate',
            'pragma': 'no-cache', 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET'})

    @staticmethod
    def MPEG_DASH_init(filename):
        if os.name == "nt":
            TempMPEG_DASH_dir = getcwd()
        else:
            TempMPEG_DASH_dir = os.path.join(getcwd(), "MPEG-DASH_manifest_temp")
        stream_folder = path.join(TempMPEG_DASH_dir, "MPEG-DASH_init")
        response = make_response(send_from_directory(directory=stream_folder, filename=filename))
        if os.path.exists(os.path.join(stream_folder, filename)):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET'
        return response

    @staticmethod
    def MPEG_DASH_segments(filename):
        if os.name == "nt":
            TempMPEG_DASH_dir = getcwd()
        else:
            TempMPEG_DASH_dir = os.path.join(getcwd(), "MPEG-DASH_manifest_temp")
        stream_folder = path.join(TempMPEG_DASH_dir, "MPEG-DASH_segments")
        response = make_response(send_from_directory(directory=stream_folder, filename=filename))
        if os.path.exists(os.path.join(stream_folder, filename)):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET'
        return response

    # CUSTOM MESSAGES
    @staticmethod
    def server_internal_error(e):
        return Response("The server encountered an internal error and was unable to complete your request.",
                        status="server-error", status_code=500)

    @staticmethod
    def unable_to_find(e):
        return Response("The requested URL was not found on this server.",
                        status="client-error", status_code=404)


def loadServer(cached_data_handler, port, cert=None, key=None):
    try:
        from gevent.pywsgi import WSGIServer as WSGIServer
    except ImportError:
        WSGIServer = None
    if WSGIServer:
        ssl_args = dict()
        if cert:
            ssl_args['certfile'] = cert
        if key:
            ssl_args['keyfile'] = key
        app = Server(__name__, cached_data_handler)

        @app.before_request
        def before_request():
            user_agent = request.headers.get('User-Agent')
            client_header = request.headers.get('Client')
            if not (user_agent and 'WEB-CLIENT' in user_agent) and not client_header:
                rule = request.url_rule
                if rule is not None:
                    url = rule.rule
                    if not ('login' in url and request.args.get('unlockCode') is not None) and 'callback' not in url:
                        return '', 403

        http_server = WSGIServer(('0.0.0.0', port), app, **ssl_args)

        info("Starting server. Hosted on port: {0}!".format(port))
        show_windows_toast_notification(
            "ChannelArchiver Server", "ChannelArchiver server starting...")
        http_server.serve_forever()
