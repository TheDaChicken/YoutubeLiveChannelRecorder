import traceback
from datetime import datetime
from time import sleep

from ..log import info, error_warning, warning, crash_warning
from ..utils.other import getTimeZone
from ..youtubeAPI import get_youtube_api_credentials, initialize_upload, upload_thumbnail
from ..encoder import Encoder


class QueueHandler:
    _queue = {}
    _stats = 'RUNNING'

    def getQueue(self):
        return self._queue

    def removeQueue(self, video_id):
        del self._queue[video_id]

    def addQueue(self, update):
        self._queue.update(update)

    def updateStatus(self, status):
        self._stats = status

    def getStatus(self):
        return self._stats


def uploadQueue(cached_data_handler, queue_holder):
    info("Upload Queue Started.")
    encoder = Encoder()
    try:
        while True:
            queue = queue_holder.getQueue()
            if len(queue) != 0:
                for video_id in queue:
                    video_info = queue.get(video_id)  # type: dict
                    video_data = video_info.get('video_data')  # type: dict
                    channel_data = video_info.get('channel_data')  # type: dict
                    file_location = video_info.get('file_location')  # type: list
                    thumbnail_location = video_info.get('thumbnail_location')
                    if len(file_location) < 2:
                        queue_holder.updateStatus('Uploading \'{0}\' recording to YouTube.'.format(video_id))
                        uploadYouTube(cached_data_handler, video_id, video_data, channel_data, file_location[0],
                                      thumbnail_location)
                    else:
                        # TODO MERGE FILES OR SOMETHING
                        now = video_data.get('start_date')  # type: datetime
                        for file_ in file_location:
                            queue_holder.updateStatus('Uploading \'{0}\' recordings to YouTube.'.format(video_id))
                            uploadYouTube(cached_data_handler, video_id, video_data, channel_data, file_,
                                          thumbnail_location)
                    queue_holder.removeQueue(video_id)
            else:
                queue_holder.updateStatus('RUNNING')
            sleep(2)
    except Exception:
        crash_warning("{0}:\n{1}".format("Queue Process", traceback.format_exc()))


def uploadYouTube(cached_data_handler, video_id, video_data, channel_data, file_location, thumbnail_location):
    channel_name = channel_data.get('channel_name')

    def get_upload_settings():
        upload_settings = cached_data_handler.getValue('UploadSettings')
        if channel_name:
            if channel_name in upload_settings:
                return upload_settings[channel_name]
        return upload_settings[None]

    def _replace_variables(text):
        class DataDict(dict):
            """
                Taken from and
                have been edited: https://stackoverflow.com/a/11023271
            """

            def __missing__(self, key):
                return ''

        if text is None or text is False or text is True:
            return None
        now = video_data.get('start_date')  # type: datetime
        timezone = getTimeZone()
        text = text.format(
            **DataDict(VIDEO_ID=video_id,
                       FILENAME=file_location,
                       CHANNEL_ID=channel_data.get('channel_id'),
                       CHANNEL_NAME=channel_data.get('channel_name'),
                       START_DATE_MONTH=str(now.month),
                       START_DATE_DAY=str(now.day),
                       START_DATE_YEAR=str(now.year),
                       START_DATE="{0}/{1}/{2}".format(now.month, now.day, now.year),
                       START_TIME=str(now.strftime("%I:%M %p")),
                       TIMEZONE=timezone if timezone is not None else '',
                       TITLE=str(video_data.get('title')),
                       DESCRIPTION=str(video_data.get('description'))
                       ))

        return text

    youtube_client = get_youtube_api_credentials(cached_data_handler)
    settings = get_upload_settings()
    try:
        if cached_data_handler.getValue('UploadLiveStreams') is True:
            upload_video_id = initialize_upload(youtube_client, file_location,
                                                _replace_variables(settings['title']),
                                                _replace_variables(
                                                    '\n'.join(settings['description'])),
                                                _replace_variables(settings['tags']),
                                                settings['CategoryID'], settings['privacyStatus'])
        sleep(3)
        if cached_data_handler.getValue('UploadThumbnail') is True:
            info("Uploading Thumbnail for {0}".format(channel_name))
            upload_thumbnail(youtube_client, upload_video_id,
                             thumbnail_location)
            info("Thumbnail Done Uploading!")
        return True
    except Exception:
        error_warning(traceback.format_exc())
        warning("Unable to upload stream to Youtube.")
        return False