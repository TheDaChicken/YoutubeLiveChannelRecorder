import traceback
from ipaddress import ip_address
from os.path import exists
from time import sleep

import requests
from flask import jsonify, request, Flask, redirect, url_for, session
from multiprocessing import Process

from Code.YouTube import ChannelObject as ChannelYouTube
from Code.log import info, error_warning
from Code.YouTubeAPI import YouTubeAPIHandler


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

    def __init__(self, import_name, process_Handler, cached_data_handler, youtube_api_handler):
        """

        :type process_Handler: ProcessHandler
        :type cached_data_handler: CacheDataHandler
        """
        super().__init__(import_name)

        self.process_Handler = process_Handler
        self.cached_data_handler = cached_data_handler
        self.youtube_api_handler = youtube_api_handler
        self.secret_key = 'a good key.'

        self.register_error_handler(500, self.server_internal_error)
        self.register_error_handler(404, self.unable_to_find)

        self.add_url_rule('/', view_func=self.hello)

        self.add_url_rule('/serverInfo', view_func=self.ServerInfo)

        self.add_url_rule('/addChannel', view_func=self.old_add_channel)
        self.add_url_rule('/addChannel/<platform_name>', view_func=self.add_channel)
        self.add_url_rule('/removeChannel', view_func=self.remove_channel)
        self.add_url_rule('/addVideoID', view_func=self.add_video_id)

        self.add_url_rule('/getLoginURL', view_func=self.youtube_api_get_login_url)
        self.add_url_rule('/login', view_func=self.youtube_api_login)
        self.add_url_rule('/login/callback', view_func=self.youtube_api_login_call_back)
        self.add_url_rule('/logoutYouTubeAPI', view_func=self.youtube_api_log_out)

        self.add_url_rule('/getServerSettings', view_func=self.getSetting)

        self.add_url_rule('/testUpload', view_func=self.YoutubeTestUpload)

    @staticmethod
    def hello():
        return Response("Server is alive.")

    def ServerInfo(self):
        channel = {}
        for channel_id in self.process_Handler.channels_dict:
            temp_channel = {channel_id: {}}
            channel_class = self.process_Handler.channels_dict.get(channel_id).get('class')  # type: ChannelYouTube
            process_class = self.process_Handler.channels_dict.get(channel_id).get('thread_class')  # type: Process

            error = self.process_Handler.channels_dict.get('error')
            if error:
                temp_channel[channel_id].update({'error': error})
            else:
                temp_channel[channel_id].update({'is_alive': process_class.is_alive()})
                if not process_class.is_alive():
                    temp_channel[channel_id].update({
                        'crashed_traceback': channel_class.get('crashed_traceback')
                    })
                else:
                    temp_channel[channel_id].update({
                        'name': channel_class.get('channel_name'),
                        'is_alive': process_class.is_alive() if process_class is not None else False,
                        'platform': channel_class.get('platform'),
                    })
                    if 'YOUTUBE' in channel_class.get('platform_name'):
                        temp_channel[channel_id].update({
                            'video_id': channel_class.get('video_id'),
                            'live': channel_class.get('live_streaming'),
                            'privateStream': channel_class.get('privateStream'),
                            'live_scheduled': channel_class.get('live_scheduled'),
                            'broadcastId': channel_class.get('broadcast_id'),
                            'sponsor_on_channel': channel_class.get('sponsor_on_channel'),
                            'last_heartbeat': channel_class.get('last_heartbeat').strftime("%I:%M %p")
                            if channel_class.get('last_heartbeat') is not None else None,
                        })
                    elif 'TWITCH' in channel_class.get('platform_name'):
                        temp_channel[channel_id].update({
                            'broadcast_id': channel_class.get('broadcast_id'),
                            'live': channel_class.get('live_streaming'),
                        })
                    if channel_class.get('live_streaming') is True:
                        temp_channel[channel_id].update({
                            'recording_status': channel_class.get('recording_status')
                        })
                    if channel_class.get('live_scheduled') is True:
                        temp_channel[channel_id].update({
                            'live_scheduled_time': channel_class.get('live_scheduled_time')
                        })
            channel.update(temp_channel)

        # YOUTUBE UPLOAD QUEUE
        uploadQueue = {
            'enabled': self.cached_data_handler.getValue('UploadLiveStreams'),
            'is_alive': self.process_Handler.YouTubeQueueThread.is_alive()
            if self.process_Handler.YouTubeQueueThread is not None else None,
        }
        if self.process_Handler.YouTubeQueueThread:
            uploadQueue.update({'status': self.process_Handler.queue_holder.getStatus()})
            problem_message, last_traceback = self.process_Handler.queue_holder.getProblemOccurred()
            if problem_message:
                uploadQueue.update({'problem_occurred': {'message': problem_message, 'traceback': last_traceback}})
        return Response({
            'channelInfo': {'channel': channel},
            'youtube': {'YoutubeLogin': self.process_Handler.is_google_account_login_in()},
            'youtubeAPI': {
                'uploadQueue': uploadQueue
            },
        })

    @staticmethod
    def old_add_channel():
        """
        USED TO HANDLE OLD CLIENTS.
        """
        channel_id = request.args.get('channel_id')
        return redirect(url_for('add_channel', platform_name="YOUTUBE", channel_id=channel_id))

    def add_channel(self, platform_name):
        def get_channel_identifier_name():
            # YOUTUBE
            if 'YOUTUBE' in platform_name:
                return "CHANNEL_ID", "channel id"
            if 'TWITCH' in platform_name:
                return "CHANNEL_NAME", "channel name"

        argument_name, name = get_channel_identifier_name()
        channel_identifier = request.args.get(argument_name.lower())

        if channel_identifier is None:
            return Response("You need {0} in args.".format(argument_name), status="client-error", status_code=400)
        if channel_identifier is '':
            return Response('You need to specify a valid {0}.'.format(name), status='client-error', status_code=400)
        if channel_identifier in self.process_Handler.channels_dict:
            return Response("Channel Already in list!", status="server-error", status_code=500)
        ok, message = self.process_Handler.run_channel(channel_identifier, platform=platform_name)
        if not ok:
            return Response(message, status="server-error", status_code=500)
        elif ok:
            self.cached_data_handler.addValueList(
                'channels_{0}'.format(platform_name), channel_identifier)
            info("{0} has been added to the list of channels.".format(channel_identifier))
            return Response(None)
        return self.server_internal_error(None)

    def remove_channel(self):
        def searchChannel():
            channel_dict_ = self.process_Handler.channels_dict.get(channel_identifier)
            if channel_dict_ is None:
                channel_array = [channel_ for channel_ in self.process_Handler.channels_dict
                                 if channel_identifier.casefold() ==
                                 self.process_Handler.channels_dict.get(channel_)['class'].get(
                                     'channel_name').casefold()]
                if channel_array is None or len(channel_array) is 0:
                    return None
                return channel_array[0], self.process_Handler.channels_dict.get(channel_array[0])
            return channel_identifier, channel_dict_

        def get_channel_identifier_name():
            # YOUTUBE
            if 'YOUTUBE' in platform_name:
                return "CHANNEL_ID", "channel id"
            if 'TWITCH' in platform_name:
                return "CHANNEL_NAME", "channel name"

        channel_identifier = request.args.get('channel_id')
        if channel_identifier is None:
            return Response("You need Channel_ID in args.", status="client-error", status_code=400)
        channel_identifier, channel_dict = searchChannel()
        if channel_dict is None:
            return Response(
                "{0} hasn't been added to the channel list, so it can't be removed.".format(channel_identifier),
                status="server-error", status_code=500)
        if 'error' not in channel_dict:
            channel_dict['class'].close()
            thread_class = channel_dict['thread_class']
            try:
                thread_class.terminate()
                sleep(1)
                if thread_class.is_alive():
                    return Response("Unable to Terminate.", status="server-error", status_code=500)
            except Exception as e:
                error_warning(traceback.format_exc())
                return Response("Unable to remove channel. {0}".format(str(e)), status="server-error", status_code=500)
        platform_name = channel_dict['class'].get('platform_name')
        self.cached_data_handler.removeValueList(
            'channels_{0}'.format(platform_name), channel_dict['class'].get(
                get_channel_identifier_name()[1]))
        del self.process_Handler.channels_dict[channel_identifier]
        sleep(.01)
        info("{0} has been removed.".format(channel_identifier))
        return Response(None)

    def add_video_id(self):
        video_id = request.args.get('video_id')
        if video_id is None:
            return Response("You need VIDEO_ID in args.", status="client-error", status_code=400)
        if video_id is '':
            return Response('You need to specify a valid video id.', status='client-error', status_code=400)
        channel_array = [channel_ for channel_ in self.process_Handler.channels_dict
                         if video_id == channel_['class'].get('video_id') or
                         video_id == channel_['class'].get('video_id')]
        if channel_array is None or len(channel_array) is not 0:
            return Response("Video Already in list!", status="server-error", status_code=500)
        del channel_array
        ok, message = self.process_Handler.run_channel_with_video_id(video_id, addToData=True)
        if ok:
            return Response(None)
        else:
            return Response(message, status="server-error", status_code=500)

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

    # LOGGING INTO YOUTUBE (FOR UPLOADING)
    @staticmethod
    def youtube_api_get_login_url():
        url = "{0}?unlockCode={1}".format(url_for('youtube_api_login', _external=True), "OK")
        return Response(url)

    def youtube_api_login(self):
        # Check for client secret file...
        if not exists(self.youtube_api_handler.getClientSecretFile()):
            return Response("WARNING: Please configure OAuth 2.0. Information at the Developers Console "
                            "https://console.developers.google.com/", status='server-error', status_code=500)
        if 'youtube_api_credentials' in self.cached_data_handler.getDict():
            return Response("Youtube account already logged-in", status='client-error', status_code=400)
        if self.youtube_api_handler.isMissingPackages():
            return Response("Missing Packages: {0}.".format(', '.join(self.youtube_api_handler.getMissingPackages())))
        url = url_for('youtube_api_login_call_back', _external=True)
        link, session['state'] = self.youtube_api_handler.generate_login_link(url)
        return redirect(link)

    def youtube_api_login_call_back(self):
        authorization_response = request.url
        state = session.get('state')
        url = url_for('youtube_api_login_call_back', _external=True)
        try:
            credentials = self.youtube_api_handler.get_credentials_from_request(authorization_response, state, url)
            if credentials is None:
                return Response("Bad Request.", status='client-error', status_code=400)
            username = self.youtube_api_handler.get_youtube_account_user_name(
                self.youtube_api_handler.get_youtube_api_credentials(credentials))
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
    def YoutubeTestUpload(self):
        channel_id = request.args.get('channel_id')
        if channel_id is None:
            return Response("You need Channel_ID in args.", status='client-error', status_code=400)
        ok, message = self.process_Handler.upload_test_run(channel_id)
        if ok:
            info("{0} has been added for test uploading.".format(channel_id))
            return Response(None)
        else:
            return Response(message, status="server-error", status_code=500)

    # CUSTOM MESSAGES
    @staticmethod
    def server_internal_error(e):
        return Response("The server encountered an internal error and was unable to complete your request.",
                        status="server-error", status_code=500)

    @staticmethod
    def unable_to_find(e):
        return Response("The requested URL was not found on this server.",
                        status="client-error", status_code=404)


def loadServer(process_Handler, cached_data_handler, port, youtube_api_handler, cert=None, key=None):
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
        app = Server(__name__, process_Handler, cached_data_handler, youtube_api_handler)

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
        http_server.serve_forever()
