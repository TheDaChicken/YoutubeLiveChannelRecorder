from threading import Thread
from time import sleep

from flask import Response
from flask import Flask
from flask import request

from . import run_channel, channel_main_array, upload_test_run, google_account_login, is_google_account_login_in, \
    google_account_logout
from .utils.other import terminate_thread
from .utils.windowsNotification import show_windows_toast_notification
from .dataHandler import add_channel_config, DownloadThumbnail, loadData, saveData, UploadVideos, save_username, \
    save_credentials, clear_credentials, get_username, remove_channel_config
from .log import info


# THIS FILE CONTAINS SERVER RELATED STUFF

class _EndpointAction:
    def __init__(self, action):
        self.action = action

    def __call__(self, *args):
        oh = self.action()
        return oh


class _FlaskClass:
    port = None

    class FlaskCustom(Flask):
        def process_response(self, response):
            # Allows more security. People won't see the Web Server in the headers.
            if 'Client' in request.headers:
                response.headers['Server'] = 'ChannelArchiver Server'
            return response

    app = FlaskCustom(__name__)

    def __init__(self, port):
        self.port = port

    def loadServer(self):
        sleep(1.5)
        self.add_url_rules()
        try:
            from gevent.pywsgi import WSGIServer as WSGIServer
        except ImportError:
            WSGIServer = None
        if WSGIServer is None:
            info("To disable this warning, install gevent pip package!")
            self.app.run(host='0.0.0.0', threaded=True, port=self.port)
        else:
            http_server = WSGIServer(('', self.port), self.app)
            info("Server started. Hosted on port: {0}".format(self.port) + "!")
            show_windows_toast_notification("ChannelArchiver Server", "ChannelArchiver server started")
            http_server.serve_forever()

    def add_url_rules(self):
        # This is to add and fix self related errors in flask
        self.app.add_url_rule('/login', 'YoutubeLogin', _EndpointAction(self.youtube_login))
        self.app.add_url_rule('/login/callback', 'YoutubeLoginCallBack', _EndpointAction(self.youtube_login_call_back))
        self.app.add_url_rule('/logout', 'YoutubeLogOut', _EndpointAction(self.youtube_log_out))

    @staticmethod
    @app.before_request
    def before_request():
        # This is used mostly for security. This can be easily broken
        if 'Client' not in request.headers:
            rule = request.url_rule
            if rule is not None:
                url = rule.rule
                if not ('login' in url and request.args.get('unlockCode') is not None) and 'callback' not in url:
                    return Response(None, mimetype='text/plain', status=403)

    @staticmethod
    @app.route('/')
    def hello():
        return "Server is alive."

    @staticmethod
    @app.route('/addChannel')
    def add_channel():
        channel_id = request.args.get('channel_id')
        if channel_id is None:
            return Response("You need Channel_ID in args.", mimetype='text/plain', status=500)
        channel_array = [channel_ for channel_ in channel_main_array
                         if channel_id.casefold() == channel_['class'].get('channel_name').casefold() or
                         channel_id.casefold() == channel_['class'].get('channel_id').casefold()]
        if len(channel_array) is not 0:
            return Response("Channel Already in list!", status=500)
        del channel_array
        ok, message = run_channel(channel_id, returnMessage=True)
        if ok:
            add_channel_config(channel_id)  # NEEDS TO ADD CHANNEL TO CONFIG
            info(channel_id + " has been added to the list of channels.")
            return Response("OK", mimetype='text/plain')
        else:
            return Response(message, mimetype='text/plain', status=500)

    @staticmethod
    @app.route('/removeChannel')
    def remove_channel():
        channel_id = request.args.get('channel_id')
        if channel_id is None:
            return "You need Channel_ID in args."

        channel_array = [channel_ for channel_ in channel_main_array
                         if channel_id.casefold() == channel_['class'].get('channel_name').casefold() or
                         channel_id.casefold() == channel_['class'].get('channel_id').casefold()]
        if channel_array is None or len(channel_array) is 0:
            return Response(channel_id + " hasn't been added to the channel list, so it can't be removed.",
                            mimetype='text/plain', status=500)
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
                    return Response("Unable to Terminate. ",
                                    mimetype='text/plain', status=500)
            except Exception as e:
                return Response("Cannot Remove Channel. " + str(e),
                                mimetype='text/plain', status=500)
        remove_channel_config(channel_array['class'].get('channel_id'))
        channel_main_array.remove(channel_array)
        sleep(.01)
        info(channel_id + " has been removed.")
        del channel_array
        return Response("OK", mimetype='text/plain')

    @staticmethod
    @app.route('/channelInfo')
    def channelInfo():
        from flask import jsonify
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
        return jsonify(json)

    # CHANGING SETTINGS
    @staticmethod
    @app.route('/getQuickSettings')
    def getQuickSetting():
        from flask import jsonify
        json = {
            'settings': {
                'DownloadThumbnail': DownloadThumbnail()
            }
        }
        return jsonify(json)

    @staticmethod
    @app.route('/swap/DownloadThumbnail', methods=['GET', 'POST'])
    def swapDownloadThumbnail():
        if request.method == 'GET':
            return Response("Bad Request. You may want to update your client!", mimetype='text/plain')
        if request.method == 'POST':
            yaml_config = loadData()
            if 'DownloadThumbnail' not in yaml_config:
                return Response("Failed to find DownloadThumbnail in data file. It's really broken. :P",
                                mimetype='text/plain', status=500)
            if yaml_config['DownloadThumbnail'] is True:
                yaml_config['DownloadThumbnail'] = False
            elif yaml_config['DownloadThumbnail'] is False:
                yaml_config['DownloadThumbnail'] = True

            info('DownloadThumbnail has been set to: ' + str(yaml_config['DownloadThumbnail']))
            saveData(yaml_config)
            del yaml_config
            return Response("OK", mimetype='text/plain')

    # For Upload Settings
    @staticmethod
    @app.route('/getUploadSettings')
    def getUploadSetting():
        from flask import jsonify
        json = {
            'settings': {
                'UploadLiveStreams': UploadVideos(),
                'DownloadThumbnail': DownloadThumbnail()
            }
        }
        return jsonify(json)

    # TODO CHANGE STATE VARIABLE TO session['state']
    state = None

    # LOGGING INTO YOUTUBE (FOR UPLOADING)

    @staticmethod
    @app.route('/getLoginURL')
    def youtube_get_login_url():
        from flask import Response, url_for
        url = url_for('YoutubeLogin', _external=True) + "?unlockCode=" + "OK"
        return Response(url, mimetype='text/plain')

    def youtube_login(self):
        from flask import Response, url_for, redirect
        from .youtubeAPI import does_account_exists, get_account_login_in_link
        if does_account_exists():
            return Response("Youtube account already logged-in", mimetype='text/plain', status=500)
        url = url_for('YoutubeLoginCallBack', _external=True)
        link, state = get_account_login_in_link(url)
        self.state = state
        return redirect(link)

    def youtube_login_call_back(self):
        from flask import request, Response, url_for
        from .youtubeAPI import credentials_build, get_youtube_account_user_name, redirect_credentials
        authorization_response = request.url
        state = self.state
        url = url_for('YoutubeLoginCallBack', _external=True)
        credentials = redirect_credentials(authorization_response, state, url)
        username = get_youtube_account_user_name(credentials_build(credentials))
        save_username(username)
        save_credentials(credentials)
        self.state = None
        return Response("OK", mimetype='text/plain')

    @staticmethod
    def youtube_log_out():
        from flask import Response
        if clear_credentials() is True:
            return Response("OK", mimetype='text/plain')
        else:
            return Response("There are no Youtube Account logged-in, to log out.", mimetype='text/plain', status=500)

    # For Getting Login-in Youtube Account info
    @staticmethod
    @app.route('/getUploadInfo')
    def YoutubeLoginInfo():
        from flask import jsonify
        from .youtubeAPI import does_account_exists
        json = {
            'info': {
                'YoutubeAccountName': get_username(),
                'YoutubeAccountLogin-in': does_account_exists(),
            }
        }
        return jsonify(json)

    # Test Uploading
    @staticmethod
    @app.route('/testUpload')
    def YoutubeTestUpload():
        from flask import request
        channel_id = request.args.get('channel_id')
        if channel_id is None:
            return Response("You need Channel_ID in args.", mimetype='text/plain', status=500)
        ok, message = upload_test_run(channel_id, returnMessage=True)
        if ok:
            info(channel_id + " has been added for test uploading.")
            return Response("OK", mimetype='text/plain')
        else:
            return Response(message, mimetype='text/plain', status=500)

    @staticmethod
    @app.route('/youtubeLOGIN')
    def Youtube_Login_FULLY():
        from flask import request
        username = request.args.get('username')
        password = request.args.get('password')
        if username is None or password is None:
            return Response("You need username and password in args.", mimetype='text/plain', status=500)
        ok, message = google_account_login(username, password)
        if ok:
            return Response("OK", mimetype='text/plain')
        else:
            return Response(message, mimetype='text/plain', status=500)

    @staticmethod
    @app.route('/youtubeLOGout')
    def Youtube_Logout_FULLY():
        ok, message = google_account_logout()
        if ok:
            return Response("OK", mimetype='text/plain')
        else:
            return Response(message, mimetype='text/plain', status=500)


def run_server(port):
    current_flask_class = _FlaskClass(port)
    check_streaming_thread = Thread(target=current_flask_class.loadServer,
                                    name="Server Thread")
    check_streaming_thread.daemon = True  # needed control+C to work.
    check_streaming_thread.start()
