import os
import subprocess
import traceback
from datetime import datetime
# from io import BytesIO
from os import getcwd, walk
from os.path import exists, join, basename
from threading import Thread
from time import sleep
from urllib.parse import urlencode
from uuid import uuid4

import requests
from flask import jsonify, request, Flask, redirect, url_for, session, send_from_directory, make_response, send_file
from multiprocessing import Process

from Code import CacheDataHandler
from Code.utils.other import try_get, translateTimezone
from Code.YouTube import ChannelObject as ChannelYouTube
from Code.YouTube import searchChannels as SearchChannelsYouTube
from Code.Twitch import searchChannels as SearchChannelsTwitch
from Code.log import info, error_warning, verbose


# from Code.YouTubeAPI import YouTubeAPIHandler


def Response(response, json_on=True, status="OK", status_code=200, headers=None, **kwargs):
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
    json_dict.update(kwargs)
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

    def __init__(self, import_name, process_Handler, cached_data_handler: CacheDataHandler, youtube_api_handler):
        """

        :type process_Handler: ProcessHandler
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
        self.add_url_rule('/addChannel/<platform_name>', view_func=self.add_channel, methods=['GET', 'POST'])
        self.add_url_rule('/removeChannel', view_func=self.remove_channel)
        self.add_url_rule('/addVideoID', view_func=self.add_video_id)
        self.add_url_rule('/getLoginURL', view_func=self.youtube_api_get_login_url)
        self.add_url_rule('/youtubeAPI/login', view_func=self.youtube_api_login)
        self.add_url_rule('/youtubeAPI/login/callback', view_func=self.youtube_api_login_call_back)
        self.add_url_rule('/logoutYouTubeAPI', view_func=self.youtube_api_log_out)
        self.add_url_rule('/getServerSettings', view_func=self.getSetting)
        self.add_url_rule('/testUpload', view_func=self.YoutubeTestUpload)
        self.add_url_rule('/platforms', view_func=self.getPlatform)
        self.add_url_rule('/getChannel/<platform_name>', view_func=self.get_channel)
        self.add_url_rule('/listRecordings', view_func=self.list_recordings)
        self.add_url_rule('/recordings', view_func=self.recordings)
        self.add_url_rule('/playRecording', view_func=self.playRecording)
        self.add_url_rule('/searchChannels/<platform_name>', view_func=self.searchChannels)
        self.add_url_rule('/liveChannels', view_func=self.liveChannels)
        self.add_url_rule('/generateThumbnail', view_func=self.generateThumbnail)

    @staticmethod
    def hello():
        return Response("Server is alive.")

    def ServerInfo(self):
        headers = request.headers  # type: dict
        timezone_name = headers.get("TimeZone")

        def formatChannel(channel_id):
            channel_class = self.process_Handler.channels_dict.get(channel_id).get('class')  # type: ChannelYouTube
            process_class = self.process_Handler.channels_dict.get(channel_id).get('thread_class')  # type: Process
            channel = {
                'name': channel_class.get("channel_name"),
                'is_alive': process_class.is_alive() if process_class is not None else False,
                'platform': channel_class.get('platform_name'),
                'live': channel_class.get('live_streaming'),
                'channel_image': channel_class.get("channel_image")
            }
            if not process_class.is_alive():
                channel.update({
                    'crashed_traceback': channel_class.get('crashed_traceback')
                })
            if 'YOUTUBE' in channel_class.get('platform_name'):
                last_heartbeat = None
                if channel_class.get("last_heartbeat") is not None:
                    last_heartbeat = translateTimezone(timezone_name, channel_class.get('last_heartbeat')).strftime(
                        "%I:%M %p")
                channel.update({
                    'video_id': channel_class.get('video_id'),
                    'privateStream': channel_class.get('privateStream'),
                    'broadcastId': channel_class.get('broadcast_id'),
                    'sponsor_on_channel': channel_class.get('sponsor_on_channel'),
                    'last_heartbeat': last_heartbeat,
                })
                live_scheduled = {
                    'live_scheduled': channel_class.get('live_scheduled')
                }
                if channel_class.get('live_scheduled') is True:
                    time = channel_class.get('live_scheduled_timeString')
                    datetime_ = channel_class.get("live_scheduled_time")  # type: datetime
                    if datetime_ is not None:
                        time = translateTimezone(timezone_name, datetime_).strftime("%B %d %Y, %I:%M %p")
                    live_scheduled.update({
                        'live_scheduled_time': time
                    })
                channel.update({'live_scheduled': live_scheduled})
            elif 'TWITCH' in channel_class.get('platform_name'):
                channel.update({
                    'broadcast_id': channel_class.get('broadcast_id'),
                    'viewers': channel_class.get("viewers"),
                })
            if channel_class.get('live_streaming') is True:
                channel.update({
                    'recording_status': channel_class.get('recording_status')
                })
            return {
                channel_id: channel
            }

        channels = {}

        list(map(channels.update, list(map(formatChannel, self.process_Handler.channels_dict))))

        # YOUTUBE UPLOAD QUEUE
        uploadQueue = {
            'enabled': self.cached_data_handler.getValue('UploadLiveStreams'),
            'is_alive': self.process_Handler.YouTubeQueueThread.is_alive()
            if self.process_Handler.YouTubeQueueThread is not None else None,
        }
        if self.process_Handler.YouTubeQueueThread:
            uploadQueue.update({'status': self.process_Handler.queue_holder.getStatus()})
            problemInformation = self.process_Handler.queue_holder.getProblemOccurred()  # type: dict
            if problemInformation:
                uploadQueue.update({'problem_occurred': problemInformation})
        return Response({
            'channelInfo': {'channel': channels},
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

    def add_channel(self, platform_name: str):
        if platform_name.upper() not in self.process_Handler.platforms:
            return Response("Unknown Platform: {0}.".format(platform_name), status="client-error", status_code=404)
        if request.method == 'GET':
            return Response("Bad Request.", status='client-error',
                            status_code=400)
        if request.method == 'POST':
            content_type = request.headers.get("Content-Type")
            if content_type:
                if 'application/json' in content_type:
                    json = request.get_json()  # type: dict
                    channel_holder_class = None

                    dvr_recording = try_get(json, lambda x: x['dvr_recording']) or False
                    session_id = try_get(json, lambda x: x['SessionID'], str)
                    channel_identifier = try_get(json, lambda x: x['channel_identifier'])
                    test_upload = try_get(json, lambda x: x['test_upload']) or False
                    if session_id:
                        if session_id not in self.sessions:
                            return Response(
                                "Unknown Session ID. The Session ID might have expired.",
                                status="client-error", status_code=404)
                        sessionStuff = self.sessions.get(session_id)  # type: dict
                        channel_holder_class = sessionStuff.get('class')
                        channel_identifier = sessionStuff.get('channel_identifier')
                        if channel_identifier in self.process_Handler.channels_dict:
                            return Response("Channel Already in list!", status="server-error", status_code=500)
                    if channel_identifier:
                        if channel_identifier == '':
                            return Response('You need to specify a valid {0}.'.format("channel_identifier"),
                                            status='client-error',
                                            status_code=400)
                        if channel_identifier in self.process_Handler.channels_dict:
                            return Response("Channel Already in list!", status="server-error", status_code=500)

                        if channel_holder_class is None:
                            channel_identifier = channel_holder_class
                        ok, message = self.process_Handler.run_channel(channel_holder_class, platform=platform_name,
                                                                       enableDVR=dvr_recording,
                                                                       testUpload=test_upload)

                        if not ok:
                            return Response(message, status="server-error", status_code=500)
                        elif ok:
                            channels = self.cached_data_handler.getValue("channels")
                            if channels is None:
                                channels = {}
                            if platform_name.upper() not in channels:
                                channels.update({platform_name.upper(): []})
                            list_ = channels.get(platform_name.upper())  # type: list
                            list_.append(channel_identifier)
                            channels.update({platform_name.upper(): list_})
                            self.cached_data_handler.setValue("channels", channels)
                            info("{0} has been added to the list of channels.".format(channel_identifier))
                            return Response(None)
                    return Response("You need {0} in response.".format("channel_identifier"), status="client-error",
                                    status_code=400)
            return Response("Bad Request.", status='client-error',
                            status_code=400)

    def remove_channel(self):
        def searchChannel():
            channel_dict_ = self.process_Handler.channels_dict.get(channel_identifier)
            if channel_dict_ is None:
                channel_array = [channel_ for channel_ in self.process_Handler.channels_dict
                                 if channel_identifier.casefold() ==
                                 self.process_Handler.channels_dict.get(channel_)['class'].get(
                                     'channel_name').casefold()]
                if channel_array is None or len(channel_array) == 0:
                    return [channel_identifier, None]
                return channel_array[0], self.process_Handler.channels_dict.get(channel_array[0])
            return channel_identifier, channel_dict_

        args = request.args  # type: ImmutableMultiDict
        channel_identifier = args.get("channel_id")
        if channel_identifier is None:
            channel_identifier = args.get("channel_identifier")
        if channel_identifier == '':
            return Response('You need to specify a valid {0}.'.format(channel_identifier), status='client-error',
                            status_code=400)
        if channel_identifier is None:
            return Response("You need {0} in args.".format("channel_identifier"), status="client-error",
                            status_code=400)

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
        channels = self.cached_data_handler.getValue("channels")
        if channels is None:
            channels = {}
        if platform_name.upper() not in channels:
            channels.update({platform_name.upper(): []})
        list_ = channels.get(platform_name.upper())  # type: list
        list_.remove(channel_identifier)
        channels.update({platform_name.upper(): list_})
        self.cached_data_handler.setValue("channels", channels)
        del self.process_Handler.channels_dict[channel_identifier]
        sleep(.01)
        info("{0} has been removed.".format(channel_identifier))
        return Response(None)

    def add_video_id(self):
        video_id = request.args.get('video_id')
        if video_id is None:
            return Response("You need VIDEO_ID in args.", status="client-error", status_code=400)
        if video_id == '':
            return Response('You need to specify a valid video id.', status='client-error', status_code=400)
        channel_array = [channel_ for channel_ in self.process_Handler.channels_dict
                         if video_id == self.process_Handler.channels_dict.get(channel_).get('video_id')]

        if channel_array is None or len(channel_array) != 0:
            return Response("Video Already in list!", status="server-error", status_code=500)
        del channel_array
        ok, message = self.process_Handler.run_channel_video_id(video_id)
        if ok:
            return Response(None)
        else:
            return Response(message, status="server-error", status_code=500)

    # USED TO ADD CHANNEL USING SESSION ID FROM GET_CHANNEL_INFO
    sessions = {}
    removeSessionThread = None

    def remove_SessionThread(self):
        """
        Used for removing Session ID after a while. We don't want that many Session IDs in a list. >_>
        """
        verbose("Starting Remove Session Thread.")
        sleep(110)
        verbose("Clearing Sessions.")
        self.sessions.clear()
        self.removeSessionThread = None

    def get_channel(self, platform_name):
        """
        :type platform_name: str
        """

        def get_channel_identifier_name():
            # YOUTUBE
            if 'youtube' in platform_name.lower():
                return "CHANNEL_ID", "channel id"
            if 'twitch' in platform_name.lower():
                return "CHANNEL_NAME", "channel name"

        if platform_name.upper() not in self.process_Handler.platforms:
            return Response("Unknown Platform: {0}.".format(platform_name), status="client-error", status_code=404)
        argument_name, name = get_channel_identifier_name()
        channel_identifier = request.args.get(argument_name.lower()) or request.args.get("channel_identifier")
        if channel_identifier is None:
            return Response("You need {0} in args.".format(argument_name), status="client-error", status_code=400)
        if channel_identifier == '':
            return Response('You need to specify a valid {0}.'.format(name), status='client-error', status_code=400)

        if channel_identifier not in self.process_Handler.channels_dict:
            channelClass = self.process_Handler.get_channel_class(
                channel_identifier, platform_name)  # type: ChannelYouTube
            ok, message = channelClass.loadVideoData()
            if not ok:
                return Response(message, status="server-error", status_code=500)
        else:
            channelClass = self.process_Handler.channels_dict.get(channel_identifier).get('class')
        channel = {
            'channel_name': channelClass.get('channel_name'),
            'channel_identifier': channel_identifier,
            'live': channelClass.get('live_streaming'),
        }
        if 'YOUTUBE' in platform_name:
            channel.update({
                'privateStream': channelClass.get('privateStream'),
            })
        response = {
            'channel': channel,
            'alreadyList': channel_identifier in self.process_Handler.channels_dict
        }
        if channelClass.get('live_streaming') is True:
            response.update({'dvr_enabled': channelClass.get('dvr_enabled')})
        new_uuid = uuid4()
        while str(new_uuid) in session:
            new_uuid = uuid4()  # just in case anything happens. I know, probably useless. :P
        response.update({'SessionID': str(new_uuid)})
        # Session allow not repeating requests and use the same class that was created. :/
        self.sessions.update({str(new_uuid): {'class': channelClass, 'channel_identifier': channel_identifier}})
        if self.removeSessionThread is None:
            self.removeSessionThread = Thread(target=self.remove_SessionThread)
            self.removeSessionThread.daemon = True
            self.removeSessionThread.start()
        return Response(response)

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
                            "https://console.developers.google.com/. CLIENT SECRET FILE MUST BE NAMED {0}.".format(
                basename(self.youtube_api_handler.getClientSecretFile())), status='server-error', status_code=500)
        if 'youtube_api_credentials' in self.cached_data_handler.getDict():
            return Response("Youtube account already logged-in", status='client-error', status_code=400)
        if self.youtube_api_handler.is_missing_packages():
            return Response("Missing Packages: {0}.".format(', '.join(self.youtube_api_handler.get_missing_packages())))
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
                self.youtube_api_handler.get_api_client(credentials))
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

    def getPlatform(self):
        return Response(self.process_Handler.platforms)

    @staticmethod
    def list_recordings():
        """
        For Old CLIENT :p
        """
        recorded_streams_dir = join(getcwd(), "RecordedStreams")
        list_recordings = []
        for (dir_path, dir_names, file_names) in walk(recorded_streams_dir):
            for file_name in file_names:
                if 'mp4' in file_name:
                    list_recordings.append(file_name)
        list_recordings.sort()
        return Response(list_recordings)

    def recordings(self):
        """
        For newer clients :p
        """

        def formatTime(recording):
            """
            :type recording: dict
            """
            stream_name = recording.get("stream_name")
            if stream_name:
                if not exists(join("RecordedStreams", stream_name)):
                    self.cached_data_handler.removeValueList("recordings", recording)
                    return None
            start_time = recording.get("start_timeUTC")
            if start_time:
                time = translateTimezone(timezone_name, datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S %Z"))
                recording.update({'date': time.strftime("%Y-%m-%d")})
                recording.update({'time': time.strftime("%H:%M:%S")})
            recording.update({'thumbnail': "{0}?{1}".format(url_for('generateThumbnail', _external=True),
                                                            urlencode({'stream_name': stream_name}))})
            return recording

        headers = request.headers  # type: dict
        timezone_name = headers.get("TimeZone")

        recording_list = self.cached_data_handler.getValue("recordings")
        if recording_list is None:
            recording_list = []
        recording_list = list(map(formatTime, recording_list))
        recording_list = [recording for recording in recording_list if recording is not None]
        return Response(recording_list)

    # Playback recordings / downloading them.

    @staticmethod
    def generateThumbnail():
        stream_name = request.args.get('stream_name')
        width = request.args.get('width')
        height = request.args.get('height')
        stream_location = join(getcwd(), "RecordedStreams", stream_name)
        devnull = open(os.devnull)
        commands = ['ffmpeg', '-i', stream_location, '-ss', '00:00:00', '-vframes', '1',
                    '-c:v', 'png']
        if width is not None or height is not None:
            resolution = "{0}x{1}".format(width, height)
            commands.extend(['-s', resolution])
        commands.extend(['-f', 'image2pipe', '-'])
        proc = subprocess.Popen(commands,
                                stdout=subprocess.PIPE, stderr=devnull)
        devnull.close()
        image = proc.stdout.read()
        return image, 200, {'Content-Type': 'image/png', 'Content-Length': len(image)}

    @staticmethod
    def playRecording():
        stream_name = request.args.get('stream_name')
        if stream_name is None:
            return Response("You need stream_name in args.", status='client-error', status_code=400)
        stream_folder = join(getcwd(), "RecordedStreams")
        return send_from_directory(directory=stream_folder, filename=stream_name)

    def searchChannels(self, platform_name):
        channel_name = request.args.get('channel_name')
        if channel_name is None:
            return Response("You need {0} in args.".format("channel_name"), status="client-error",
                            status_code=400)
        if channel_name == '':
            return Response('You need to specify a valid {0}.'.format("channel_name"), status='client-error',
                            status_code=400)
        if 'YOUTUBE' in platform_name:
            okay, channels = SearchChannelsYouTube(channel_name, self.process_Handler.shared_cookieDictHolder)
            if okay is True:
                return Response(channels)
            return Response(channels, status_code=500, status='server-error')
        if 'TWITCH' in platform_name:
            okay, channels = SearchChannelsTwitch(channel_name, self.process_Handler.shared_cookieDictHolder,
                                                  self.process_Handler.shared_globalVariables)
            if okay is True:
                return Response(channels)
            return Response(channels, status_code=500, status='server-error')
        return Response(
            "Not such a platform, {0} on server or platform doesn't support searching.".format(platform_name),
            status_code=404,
            status='client-error')

    def liveChannels(self):
        def formatChannel(channel_id):
            channel_class = self.process_Handler.channels_dict.get(channel_id).get('class')  # type: ChannelYouTube
            process_class = self.process_Handler.channels_dict.get(channel_id).get('thread_class')  # type: Process
            channel = {
                'name': channel_class.get("channel_name"),
                'is_alive': process_class.is_alive() if process_class is not None else False,
                'platform': channel_class.get('platform_name'),
                'live': channel_class.get('live_streaming'),
                'channel_image': channel_class.get("channel_image")
            }
            return channel

        channels = [x for x in list(map(formatChannel, self.process_Handler.channels_dict)) if x.get("live") is True]
        return Response(channels)

    # CUSTOM MESSAGES
    @staticmethod
    def server_internal_error(e):
        return Response("The server encountered an internal error and was unable to complete your request.",
                        status="server-error", status_code=500)

    @staticmethod
    def unable_to_find(e):
        return Response("The requested URL was not found on this server.",
                        status="client-error", status_code=404)


def loadServer(process_handler, cached_data_handler, port, youtube_api_handler, cert=None, key=None):
    try:
        from gevent.pywsgi import WSGIServer as web_server
    except ImportError:
        error_warning("Get gevent package! Unable to run.")
        web_server = None
    if web_server:
        ssl_args = dict()
        if cert:
            ssl_args['certfile'] = cert
        if key:
            ssl_args['keyfile'] = key
        app = Server(__name__, process_handler, cached_data_handler, youtube_api_handler)

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

        http_server = web_server(('0.0.0.0', port), app, **ssl_args)

        info("Starting server. Hosted on port: {0}!".format(port))
        http_server.serve_forever()
