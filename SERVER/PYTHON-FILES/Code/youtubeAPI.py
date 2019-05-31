import os

from .log import info, stopped, warning
from .dataHandler import loadData, get_credentials

import random
import time

try:
    from http import client
except ImportError:
    client = None
    stopped("Unsupported version of Python. You need Version 3 :<")

try:
    import httplib2
except ImportError:
    httplib2 = None
    stopped("Sorry :/ Upload Video Needs httplib2 installed!")

try:
    from apiclient.discovery import build
    from apiclient.errors import HttpError
    from apiclient.http import MediaFileUpload
except ImportError:
    build = None
    HttpError = None
    MediaFileUpload = None
    stopped("Sorry :/ You need to install using pip: google-api-python-client for using Youtube API")

try:
    from oauth2client.client import flow_from_clientsecrets
    from oauth2client.file import Storage
    from oauth2client.tools import run_flow
except ImportError:
    stopped("Sorry :/ Upload Video Needs oauth2client installed!")

try:
    from google.oauth2.credentials import Credentials
except ImportError:
    Credentials = None
    stopped("Sorry :/ Upload Video Needs google-auth installed!")

try:
    from google_auth_oauthlib.flow import Flow
except ImportError:
    Flow = None
    stopped("Sorry :/ You need to install using pip: google-auth-oauthlib for using Youtube API")

httplib2.RETRIES = 1
MAX_RETRIES = 10
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, client.NotConnected,
                        client.IncompleteRead, client.ImproperConnectionState,
                        client.CannotSendRequest, client.CannotSendHeader,
                        client.ResponseNotReady, client.BadStatusLine)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "client_id.json")
YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
MISSING_CLIENT_SECRETS_MESSAGE = "WARNING: Please configure OAuth 2.0. Information at the Developers Console " \
                                 "https://console.developers.google.com/ "
VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


def get_youtube_client(ignoreConfig=False):
    data_ = loadData()
    if does_account_exists():
        ok = False
        if not ignoreConfig and data_['UploadLiveStreams']:
            ok = True
        elif ignoreConfig:
            ok = True
        if ok:
            info("Found Youtube Account login in. Getting Youtube Upload Client.")
            youtube_client = credentials_build(data_['credentials'])
            del data_
            return youtube_client


def get_account_login_in_link(redirect_url):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=YOUTUBE_READ_WRITE_SCOPE)

    # flow.redirect_uri = flask.url_for('oauth2callback', _external=True)
    flow.redirect_uri = redirect_url

    if not does_account_exists():
        authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type='offline',
            # Enable incremental authorization. Recommended as a best practice.
            include_granted_scopes='true',
            # Allows refresh_token to be always in the authorization url
            prompt='consent')
        # device_id and device_name allows a private ip to be used.

        # &device_id=1&device_name=Web
        return [authorization_url + "", state]
    return [None, None]


def redirect_credentials(authorization_response, state, url):
    def credentials_to_dict(credentials):
        return {'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes}

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=YOUTUBE_READ_WRITE_SCOPE, state=state)
    flow.redirect_uri = url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    return credentials_to_dict(credentials)


def credentials_build(credentials):
    credentials = Credentials(**credentials)

    if build is not None:
        b = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                  credentials=credentials)
    return b


def does_account_exists():
    if get_credentials() is None:
        return False
    return True


# Now Youtube Stuff.


def initialize_upload(youtubeClient, file_location, title, description, keywords, category, privacyStatus):
    tags = None
    if keywords:
        tags = keywords.split(",")

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
        media_body=MediaFileUpload(file_location, chunksize=-1, resumable=True)
    )

    return resumable_upload(insert_request, file_location)


# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request, file_location):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            info("Uploading file...")
            status, response = insert_request.next_chunk()
            if 'id' in response:
                info(file_location + " was successfully uploaded with video id of '%s'." % response['id'])
                return response['id']
            else:
                exit("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                     e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            warning(error)
            retry += 1
            if retry > MAX_RETRIES:
                stopped("No longer attempting to retry. Couldn't upload " + file_location + ".")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            warning("Sleeping %f seconds and then retrying upload..." % sleep_seconds)
            time.sleep(sleep_seconds)


# Call the API's thumbnails.set method to upload the thumbnail image and
# associate it with the appropriate video.
def upload_thumbnail(youtubeClient, video_id, file_location):
    youtubeClient.thumbnails().set(
        videoId=video_id,
        media_body=file_location
    ).execute()


def get_youtube_account_user_name(youtubeClient):
    channels_list = youtubeClient.channels().list(
        part="snippet,contentDetails,statistics",
        mine=True
    ).execute()
    return channels_list['items'][0]['snippet']['title']
