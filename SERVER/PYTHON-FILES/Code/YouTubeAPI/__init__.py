import os
import random
import traceback
from http import client
from time import sleep

from Code import CacheDataHandler
from Code.log import error_warning, warning, info

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

missing_packages = []

try:
    from googleapiclient.discovery import build, Resource
    from google_auth_oauthlib.flow import Flow
    from oauthlib.oauth2 import InvalidGrantError
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
except ImportError as e:
    missing_packages.append("google-auth-oauthlib")


class YouTubeAPIHandler:
    CLIENT_SECRETS_FILE = os.path.join(os.getcwd(), "client_id.json")
    YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube"]
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

    # UPLOADING
    RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
    MAX_RETRIES = 10

    def __init__(self, cached_data_handler: CacheDataHandler):
        self.cached_data_handler = cached_data_handler

    @staticmethod
    def is_missing_packages():
        return len(missing_packages) != 0

    @staticmethod
    def get_missing_packages():
        return missing_packages

    def getClientSecretFile(self):
        return self.CLIENT_SECRETS_FILE

    def __build__(self, credentials_dict):
        credentials = Credentials(**credentials_dict)
        b = build(self.YOUTUBE_API_SERVICE_NAME, self.YOUTUBE_API_VERSION, credentials=credentials)
        return b

    def get_api_client(self, credentials_dict=None) -> Resource or None:
        if credentials_dict is None:
            if 'youtube_api_credentials' not in self.cached_data_handler.getDict():
                return None
            info("Found Youtube Account login in. Getting Youtube Upload Client.")
            credentials_dict = self.cached_data_handler.getValue('youtube_api_credentials')
        return self.__build__(credentials_dict)

    def get_credentials_from_request(self, authorization_response, state, url) -> dict or None:
        def credentials_to_dict():
            return {'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes}

        try:
            flow = Flow.from_client_secrets_file(
                self.CLIENT_SECRETS_FILE, scopes=self.YOUTUBE_SCOPES, state=state)
            flow.redirect_uri = url
            flow.fetch_token(authorization_response=authorization_response)
            credentials = flow.credentials
            return credentials_to_dict()
        except InvalidGrantError:
            return None

    def generate_login_link(self, redirect_url):
        flow = Flow.from_client_secrets_file(
            self.CLIENT_SECRETS_FILE, scopes=self.YOUTUBE_SCOPES)
        flow.redirect_uri = redirect_url
        if 'youtube_api_credentials' not in self.cached_data_handler.getDict():
            arguments = dict(
                # Enable offline access so that you can refresh an access token without
                # re-prompting the user for permission. Recommended for web server apps.
                access_type='offline',
                # Enable incremental authorization. Recommended as a best practice.
                include_granted_scopes='true',
                # Allows refresh_token to be always in the authorization url
                prompt='consent')
            authorization_url, state = flow.authorization_url(**arguments)
            return [authorization_url, state]
        return [None, None]

    def getCacheDataHandler(self):
        return self.cached_data_handler


    def initialize_upload(self, file_location, title, description, keywords, category, privacyStatus):
        youtubeClient = self.get_api_client()
        if keywords:
            tags = keywords.split(",")
        else:
            tags = []
        body = dict(
            snippet=dict(
                title=title,
                description=description,
                tags=tags,
                categoryId=category
            ),
            status=dict(
                privacyStatus=privacyStatus
            )
        )
        # Call the API's videos.insert method to create and upload the video.
        insert_request = youtubeClient.videos().insert(
            part=",".join(body.keys()),
            body=body,
            # The chunksize parameter specifies the size of each chunk of data, in
            # bytes, that will be uploaded at a time. Set a higher value for
            # reliable connections as fewer chunks lead to faster uploads. Set a lower
            # value for better recovery on less reliable connections.
            #
            # Setting "chunksize" equal to -1 in the code below means that the entire
            # file will be uploaded in a single HTTP request. (If the upload fails,
            # it will still be retried where it left off.) This is usually a best
            # practice, but if you're using Python older than 2.6 or if you're
            # running on App Engine, you should set the chunksize to something like
            # 1024 * 1024 (1 megabyte).
            media_body=MediaFileUpload(
                file_location, chunksize=1024 * 1024, resumable=True)
        )
        return self.__resumable_upload(insert_request, file_location)

    # This method implements an exponential backoff strategy to resume a
    # failed upload.
    def __resumable_upload(self, insert_request, file_location):
        response = None
        error = None
        retry = 0
        while response is None:
            httperror = HttpError
            try:
                info("Uploading file...")
                status, response = insert_request.next_chunk()
                if response:
                    if 'id' in response:
                        info(file_location + " was successfully uploaded with video id of '%s'." % response['id'])
                        return response['id']
                    else:
                        warning("The upload failed with an unexpected response: %s" % response)
            except httperror as e:
                if e.resp.status in self.RETRIABLE_STATUS_CODES:
                    error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                         e.content)
                else:
                    raise
            except (IOError, client.NotConnected,
                    client.IncompleteRead, client.ImproperConnectionState,
                    client.CannotSendRequest, client.CannotSendHeader,
                    client.ResponseNotReady, client.BadStatusLine) as e:
                error = "A retriable error occurred: %s" % e

            if error is not None:
                warning(error)
                retry += 1
                if retry > self.MAX_RETRIES:
                    info("No longer attempting to retry. Couldn't upload {0}.".format(file_location))
                else:
                    max_sleep = 2 ** retry
                    sleep_seconds = random.random() * max_sleep
                    warning("Sleeping %f seconds and then retrying upload..." % sleep_seconds)
                    sleep(sleep_seconds)

    def upload_thumbnail(self, video_id, file_location):
        youtubeClient = self.get_api_client()
        youtubeClient.thumbnails().set(
            videoId=video_id,
            media_body=file_location
        ).execute()

    def get_youtube_account_user_name(self, youtubeClient=None):
        if youtubeClient is None:
            youtubeClient = self.get_api_client()
        channels_list = youtubeClient.channels().list(
            part="snippet,contentDetails,statistics",
            mine=True
        ).execute()
        return channels_list['items'][0]['snippet']['title']
