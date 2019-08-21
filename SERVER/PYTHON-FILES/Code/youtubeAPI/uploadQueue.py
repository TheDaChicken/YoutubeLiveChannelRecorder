import os
import traceback
from datetime import datetime
from time import sleep

from ..encoder import Encoder
from ..log import info, error_warning, warning, crash_warning
from ..utils.other import getTimeZone
from ..youtubeAPI import get_youtube_api_credentials, initialize_upload, upload_thumbnail


class QueueHandler:
    _queue = {}
    _stats = 'RUNNING'
    _last_problem_occurred = None
    _crash_traceback_message = None

    def getQueue(self):
        return self._queue

    def removeQueue(self, video_id):
        del self._queue[video_id]

    def addQueue(self, update):
        self._queue.update(update)

    def updateStatus(self, status):
        self._stats = status

    def problem_occurred(self, problem, crash_traceback_message=None):
        self._last_problem_occurred = problem
        self._crash_traceback_message = crash_traceback_message

    def getStatus(self):
        return self._stats

    def getProblemOccurred(self):
        return self._last_problem_occurred, self._crash_traceback_message


def uploadQueue(cached_data_handler, queue_holder):
    youtube_api_quota = False
    info("Upload Queue Started.")
    encoder = Encoder()
    try:
        while True:
            queue = queue_holder.getQueue()
            if youtube_api_quota:
                # WAIT UNTIL MIDNIGHT. TURN OFF PROTECTION THEN START UPLOADING AGAIN.
                try:
                    import pytz
                except ImportError:
                    pytz = None
                    queue_holder.updateStatus("Unable to get Pacific Time Zone. "
                                              "Needed to check if midnight in youtube api quota timezone "
                                              "(Pacific Time) to start uploading again due to quota. "
                                              "To fix that, pip install pytz. Then restart the server. "
                                              "Using server timezone, currently. - {0}".format(
                        queue_holder.getStatus()))
                if pytz:
                    pacific_time = pytz.timezone('US/Pacific')
                    now = datetime.now(pacific_time)
                else:
                    now = datetime.now()
                if now.hour == 0 and now.minute > 1 and now.second > 1:
                    youtube_api_quota = False
            elif len(queue) != 0 and not youtube_api_quota:
                for video_id in queue:
                    video_info = queue.get(video_id)  # type: dict
                    video_data = video_info.get('video_data')  # type: dict
                    channel_data = video_info.get('channel_data')  # type: dict
                    file_location = video_info.get('file_location')  # type: list
                    thumbnail_location = video_info.get('thumbnail_location')
                    if len(file_location) < 2:
                        queue_holder.updateStatus('Uploading \'{0}\' recording to YouTube.'.format(video_id))
                        ok, traceback_crash = uploadYouTube(cached_data_handler, video_id, video_data, channel_data,
                                                            file_location[0],
                                                            thumbnail_location)
                        if not ok:
                            # IF NOT A TRACEBACK, WILL SHOW IN STATUS.
                            if 'Traceback' not in traceback_crash:
                                queue_holder.updateStatus(traceback_crash)
                                # IF REASON IS DUE TO QUOTA
                                if 'quota' in traceback_crash:
                                    youtube_api_quota = True
                            else:
                                queue_holder.problem_occurred(
                                    "Failed to upload {0} \'{1}\' recording to YouTube.".format(
                                        channel_data.get('channel_name'), traceback_crash))
                    else:
                        now = video_data.get('start_date')  # type: datetime
                        final_ = os.path.join(os.getcwd(), "RecordedStreams",
                                              '{0} - \'{1}\' {2}-{3}-{4} merged-full-stream.mp4'.format(
                                                  channel_data.get('channel_name'), video_id, now.month, now.day,
                                                  now.year))
                        ok = encoder.merge_streams(file_location, final_)
                        if ok:
                            queue_holder.updateStatus('Merging {0} \'{1}\' recordings for YouTube.'.format(
                                channel_data.get('channel_name'), video_id))
                            while encoder.running:
                                sleep(1)
                            queue_holder.updateStatus('Deleting {0} \'{1}\' recordings due to a merge. '
                                                      'Keeping Merged Version for use.'.format(channel_data.
                                                                                               get('channel_name'),
                                                                                               video_id))
                            # DELETE OLD RECORDINGS.
                            for file in file_location:
                                os.remove(file)
                            queue_holder.updateStatus('Uploading {0} \'{1}\' merged recording to YouTube.'.format(
                                channel_data.get('channel_name'), video_id))
                            ok_, traceback_crash = uploadYouTube(cached_data_handler, video_id, video_data, channel_data,
                                                                final_,
                                                                thumbnail_location)
                            if not ok_:
                                # IF NOT A TRACEBACK, WILL SHOW IN STATUS.
                                if 'Traceback' not in traceback_crash:
                                    queue_holder.updateStatus(traceback_crash)
                                    # IF REASON IS DUE TO QUOTA
                                    if 'quota' in traceback_crash:
                                        youtube_api_quota = True
                                else:
                                    queue_holder.problem_occurred(
                                        "Failed to upload {0} \'{1}\' merged version to YouTube.".
                                            format(channel_data.get('channel_name'), traceback_crash))
                        if not ok:
                            queue_holder.problem_occurred("Failed to start merge {0} \'{1}\' recordings for YouTube.".
                                                          format(channel_data.get('channel_name'), video_id))
                    if not youtube_api_quota:
                        queue_holder.removeQueue(video_id)
            else:
                queue_holder.updateStatus('Waiting.')
            sleep(2)
    except Exception:
        queue_holder.updateStatus("Crash: {0}".format(traceback.format_exc()))
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
        return [True, None]
    except Exception as e1:
        traceback_ = traceback.format_exc()
        if 'quota' in traceback_ and 'usage' in traceback_:
            return [False, str(e1)]
        error_warning(traceback_)
        warning("Unable to upload stream to Youtube.")
        return [False, traceback_]
