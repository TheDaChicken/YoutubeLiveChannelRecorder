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
    def create_filename(channel_name, video_id, now):
        # Used to handle lots of names by creating new names and add numbers!
        amount = 1
        while True:
            if amount is 1:
                file_name = "{3} - '{4}' - {0}-{1}-{2}".format(now.month, now.day, now.year,
                                                               channel_name, video_id)
            else:
                file_name = "{3} - '{4}' - {0}-{1}-{2}_{5}".format(now.month, now.day, now.year,
                                                                   channel_name, video_id, amount)
            path = os.path.join("RecordedStreams", '{0}.mp4'.format(file_name))
            if not os.path.isfile(path):
                return file_name
            amount += 1

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
        if len(self.video_list) != 0:
            if self.queue_holder:
                verbose("Adding streams to youtube upload queue.")
                for video_id in self.video_list:
                    self.queue_holder.addQueue(self.video_list.get(video_id))
                self.video_list.clear()
