import traceback
from datetime import datetime
from os import getcwd, mkdir
from os.path import join, basename, exists
from time import sleep
from shutil import move

from Code.encoder import Encoder
from Code.log import crash_warning, error_warning, warning, info
from Code.utils.other import getTimeZone
from . import YouTubeAPIHandler


class QueueHandler:
    _queue = []
    _status = 'RUNNING'
    _last_problem = None

    def addQueue(self, video_data):
        self._queue.append(video_data)

    def getNextQueue(self):
        try:
            return self._queue.pop()
        except IndexError:
            return None

    def updateStatus(self, new_status):
        self._status = new_status

    def getStatus(self):
        return self._status

    def setProblemOccurred(self, channelName, action, problemMessage):
        self._last_problem = dict({
            'channel_name': channelName,
            'message': '{0}'.format(problemMessage), # FOR OLD CLIENTS
            'action': action
        })

    def getProblemOccurred(self):
        return self._last_problem


def runQueue(youtube_api_handler, queue_holder):
    """

    :type youtube_api_handler: YouTubeAPIHandler
    :type queue_holder: QueueHandler
    """

    def is_midnight():
        if pytz:
            pacific_time = pytz.timezone('US/Pacific')
            now = datetime.now(pacific_time)
        else:
            now = datetime.now()
        if now.hour == 0 and now.minute > 1 and now.second > 1:
            return True
        return False

    def uploadYouTube():
        try:
            # youtube_api_handler.initialize_upload()
            def get_upload_settings():
                upload_settings = youtube_api_handler.getCacheDataHandler().getValue('UploadSettings')
                channel_name = video_data.get('channel_name')
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

                now = video_data.get('start_date')  # type: datetime
                timezone = getTimeZone()
                if text is not None:
                    text = text.format(
                        **DataDict(VIDEO_ID=video_id,
                                   FILENAME=file_locations[0],
                                   CHANNEL_ID=video_data.get('channel_id'),
                                   CHANNEL_NAME=video_data.get('channel_name'),
                                   START_DATE_MONTH=str(now.month),
                                   START_DATE_DAY=str(now.day),
                                   START_DATE_YEAR=str(now.year),
                                   START_DATE="{0}/{1}/{2}".format(now.month, now.day, now.year),
                                   START_TIME=str(now.strftime("%I:%M %p")),
                                   TIMEZONE=timezone if timezone is not None else '',
                                   TITLE=str(video_data.get('title')),
                                   DESCRIPTION=str(video_data.get('description'))
                                   ))
                    if text is None:
                        return "[FAILED TO REPLACE VARIABLES]"
                return text

            settings = get_upload_settings()

            if youtube_api_handler.getCacheDataHandler().getValue('UploadLiveStreams') is True:
                upload_video_id = youtube_api_handler.initialize_upload(file_locations[0],
                                                                        _replace_variables(settings['title']),
                                                                        _replace_variables(
                                                                            '\n'.join(settings['description'])),
                                                                        _replace_variables(settings['tags']),
                                                                        settings['CategoryID'],
                                                                        settings['privacyStatus'])
                sleep(3)
                if youtube_api_handler.getCacheDataHandler().getValue('UploadThumbnail') is True:
                    info("Uploading Thumbnail for {0}".format(video_data.get('channel_name')))
                    youtube_api_handler.upload_thumbnail(upload_video_id, None)
                    # TODO Get Auto Uploading thumbnails! working again!
                    info("Thumbnail Done Uploading!")
                return [True, None]
        except:
            traceback_ = traceback.format_exc()
            if 'quota' in traceback_ and 'usage' in traceback_:
                return [False, "YouTube API Quota has been exceeded. Waiting until YouTube API Quota resets."]
            error_warning(traceback_)
            warning("Unable to upload stream to Youtube.")
            return [False, traceback]

    if youtube_api_handler.is_missing_packages():
        queue_holder.updateStatus(
            "Missing Packages: {0}.".format(', '.join(youtube_api_handler.get_missing_packages())))
    encoder = Encoder()
    youtube_api_quota = False
    try:
        while True:
            if youtube_api_handler.is_missing_packages():
                continue
            if youtube_api_quota is True:
                try:
                    import pytz
                except ImportError:
                    pytz = None
                youtube_api_quota = not is_midnight()
                if youtube_api_quota is True:
                    continue
            video_data = queue_holder.getNextQueue()
            if video_data is not None:
                video_id = video_data.get('video_id')  # type: str
                file_locations = video_data.get('file_location')  # type: list
                start_date = video_data.get('start_date')  # datetime.

                if len(file_locations) > 2:
                    final_file = join(getcwd(), "RecordedStreams",
                                      '{0} - \'{1}\' {2}-{3}-{4} merged-full-stream.mp4'.format(
                                          video_data.get('channel_name'), video_id, start_date.month, start_date.day,
                                          start_date.year))
                    ok = encoder.merge_streams(file_locations, final_file)
                    if ok:
                        queue_holder.updateStatus('Merging {0} \'{1}\' recordings for YouTube.'.format(
                            video_data.get('channel_name'), video_id))
                        while encoder.running:
                            sleep(1)

                        OldFromMergedFiles = join(getcwd(), "OldFromMergedFiles")
                        if not exists(OldFromMergedFiles):
                            mkdir(OldFromMergedFiles)

                        # MOVE TO ANOTHER FOLDER
                        for file_location in file_locations:
                            move(file_location, join(OldFromMergedFiles, basename(file_location)))
                        file_locations = [final_file]
                    if not ok:
                        queue_holder.setProblemOccurred(
                            video_data.get('channel_name'), 'FFmpeg Concat Merging',
                            "Not unable to Merge Recordings for {0} \'{1}\'".format(video_data.get('channel_name'), video_id))
                        continue
                if len(file_locations) == 1:
                    queue_holder.updateStatus('Uploading {0} \'{1}\' merged recording to YouTube.'.format(
                        video_data.get('channel_name'), video_id))
                    ok, traceback_crash = uploadYouTube()
                    if not ok:
                        if 'quota' in traceback_crash:
                            youtube_api_quota = True
                        queue_holder.setProblemOccurred(
                            video_data.get("channel_name"), "Unable to upload {0} \'{1}\' recording to YouTube.".format(
                                video_data.get("channel_name"), traceback_crash), 'Uploading [YouTubeAPI]')
            else:
                queue_holder.updateStatus("Waiting.")
            sleep(4)
    except KeyboardInterrupt:
        pass
    except:
        queue_holder.updateStatus("Crash: {0}".format(traceback.format_exc()))
        crash_warning("{0}:\n{1}".format("Queue Process", traceback.format_exc()))
