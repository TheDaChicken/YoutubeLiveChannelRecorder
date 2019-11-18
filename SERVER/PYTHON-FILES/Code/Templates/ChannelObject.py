import atexit
import os

from Code.log import verbose


class SharableHandler:
    def get(self, variable_name):
        try:
            return getattr(self, variable_name)
        except AttributeError:
            return None

    def set(self, variable_name, value):
        return setattr(self, variable_name, value)


class TemplateChannel(SharableHandler):
    # VIDEO DATA
    title = None
    StreamInfo = None  # DICT THAT HOLDS STREAM URLS

    # SERVER
    crashed_traceback = None
    live_streaming = None

    # FFMPEG!
    EncoderClass = None

    # UPLOADING
    video_list = None
    queue_holder = None

    def close(self):
        if self.EncoderClass:
            self.EncoderClass.stop_recording()

    def registerCloseEvent(self):
        atexit.register(self.close)

    @staticmethod
    def create_filename(channel_identifier, video_id, now):
        # Used to handle lots of names by creating new names and add numbers!
        amount = 1
        while True:
            if amount is 1:
                file_name = "{3} - '{4}' - {0}-{1}-{2}".format(now.month, now.day, now.year,
                                                               channel_identifier, video_id)
            else:
                file_name = "{3} - '{4}' - {0}-{1}-{2}_{5}".format(now.month, now.day, now.year,
                                                                   channel_identifier, video_id, amount)
            path = os.path.join("RecordedStreams", '{0}.mp4'.format(file_name))
            if not os.path.isfile(path):
                return file_name
            amount += 1

    def add_youtube_queue(self):
        """
        To add videos to be uploaded in the YouTube Queue.
        """
        if len(self.video_list) != 0:
            if self.queue_holder:
                verbose("Adding streams to youtube upload queue.")
                self.queue_holder.addQueue(self.video_list)
                self.video_list.clear()
