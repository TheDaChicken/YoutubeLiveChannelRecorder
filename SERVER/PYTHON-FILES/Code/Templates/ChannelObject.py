import atexit
import codecs
import os
import pickle
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from os.path import basename
from time import sleep

from Code.log import verbose
from Code.utils.windows import show_windows_toast_notification
from Code.encoder import Encoder
from Code.dataHandler import CacheDataHandler
from Code.utils.m3u8 import HLSMedia


class SharableHandler:
    def get(self, variable_name):
        try:
            return getattr(self, variable_name)
        except AttributeError:
            return None

    def set(self, variable_name, value):
        return setattr(self, variable_name, value)


class TemplateChannel(SharableHandler, ABC):
    # VIDEO DATA
    title = None
    video_id = None
    description = None

    # SERVER
    crashed_traceback = None
    live_streaming = None

    # FFMPEG!
    EncoderClass = None

    # Channel
    channel_name = None
    channel_id = None
    channel_image = None

    # UPLOADING
    video_list = None
    queue_holder = None

    start_date = None
    start_dateUTC = None
    video_location = None

    StreamFormat = None

    # SERVER VARIABLES
    recording_status = None

    def __init__(self, channel_identifier, SettingDict, SharedCookieDict=None, cachedDataHandler=None,
                 queue_holder=None, globalVariables=None):
        """
        :type channel_identifier: str
        :type cachedDataHandler: CacheDataHandler
        :type SharedCookieDict: dict
        :type globalVariables: GlobalVariables
        """
        self.channel_identifier = channel_identifier
        self.cachedDataHandler = cachedDataHandler
        self.sharedCookieDict = SharedCookieDict
        self.globalVariables = globalVariables
        self.DebugMode = SettingDict.get('debug_mode')
        self.EncoderClass = Encoder()
        self.EncoderClass.enable_logs = SettingDict.get('ffmpeg_logs')
        self.queue_holder = queue_holder
        if 'testUpload' in SettingDict:
            self.TestUpload = True

    def close(self):
        self.EncoderClass.stop_recording()

    def registerCloseEvent(self):
        atexit.register(self.close)

    def start_recording(self, format_: HLSMedia, StartIndex0=False):
        self.start_date = datetime.now()
        self.start_dateUTC = datetime.now(timezone.utc)
        self.recording_status = "Starting Recording."
        recording_dir = os.path.join(os.getcwd(), "RecordedStreams")
        self.create_folder(recording_dir)
        filename = self.create_filename(self.channel_name, self.video_id, self.start_date)
        self.video_location = os.path.join(recording_dir, '{0}.mp4'.format(filename))
        if self.EncoderClass.start_recording(format_.url, self.video_location,
                                             StartIndex0=StartIndex0, format=format_.format):
            self.recording_status = "Recording."
            show_windows_toast_notification("Live Recording Notifications",
                                            "{0} is live and is now recording. \nRecording at {1}".format(
                                                self.channel_name, format_.stream_resolution))
            self.addTemp({
                'video_id': self.video_id, 'title': self.title, 'start_date': self.start_date,
                'file_location': self.video_location, 'channel_name': self.channel_name,
                'channel_id': self.channel_id, 'description': self.description})
            recordingList = self.cachedDataHandler.getValue("recordings")
            if recordingList is None:
                recordingList = []
            recordingList.append({
                'video_id': self.video_id,
                'channel_name': self.channel_name,
                'start_timeUTC': self.start_dateUTC.strftime("%Y-%m-%d %H:%M:%S %Z"),
                'stream_name': basename(self.video_location),
            })
            self.cachedDataHandler.setValue("recordings", recordingList)
            return True

    def stop_recording(self):
        while True:
            if self.EncoderClass.last_frame_time:
                last_seconds = (datetime.now() - self.EncoderClass.last_frame_time).total_seconds()
                # IF BACK LIVE AGAIN IN THE MIDDLE OF WAITING FOR NON ACTIVITY.
                if self.live_streaming is True:
                    break
                if last_seconds > 11:
                    self.EncoderClass.stop_recording()
                    break
            sleep(1)

    @staticmethod
    def create_filename(channel_name, video_id, now):
        # Used to handle lots of names by creating new names and add numbers!
        amount = 1
        while True:
            if amount == 1:
                file_name = "{3} - '{4}' - {0}-{1}-{2}".format(now.month, now.day, now.year,
                                                               channel_name, video_id)
            else:
                file_name = "{3} - '{4}' - {0}-{1}-{2}_{5}".format(now.month, now.day, now.year,
                                                                   channel_name, video_id, amount)
            path = os.path.join("RecordedStreams", '{0}.mp4'.format(file_name))
            if not os.path.isfile(path):
                return file_name
            amount += 1

    @staticmethod
    def create_folder(recording_dir):
        if not os.path.exists(recording_dir):
            os.mkdir(recording_dir)


    def isVideoIDinTemp(self, video_id):
        video_list = list(map(lambda x: self.video_list.get(x).get('video_id'), self.video_list.keys()))
        return video_id in video_list

    def addTemp(self, video_data):
        """

        :type video_data: dict
        :return:
        """
        if self.video_list is None:
            self.video_list = {}
        video_id = video_data.get('video_id')
        if video_id in self.video_list:
            file_location = self.video_list.get(video_id).get('file_location')  # type: list
            file_location.append(video_data.get('file_location'))
            self.video_list.update({
                video_id: {
                    'title': video_data.get('title'),
                    'file_location': file_location
                }
            })
        else:
            video_data.update({'file_location': [video_data.get('file_location')]})
            self.video_list.update({video_data.get('video_id'): video_data})

    def add_youtube_queue(self):
        """
        To add videos to be uploaded in the YouTube Queue.
        """
        print(self.video_list)
        if len(self.video_list) != 0:
            if self.queue_holder:
                verbose("Adding streams to youtube upload queue.")
                for video_id in self.video_list:
                    self.queue_holder.addQueue(self.video_list.get(video_id))
                self.video_list.clear()

    @abstractmethod
    def channel_thread(self, args: dict):
        pass

