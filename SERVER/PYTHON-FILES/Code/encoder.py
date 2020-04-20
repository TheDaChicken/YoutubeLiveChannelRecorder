import os
import subprocess
from datetime import datetime
from threading import Thread
from time import sleep

from .log import verbose, info, EncoderLog, warning


class Encoder:
    recording_metadata = ["service_provider=FFmpeg (https://ffmpeg.org) <- YoutubeLiveChannelRecorder ("
                          "https://github.com/TheDaChicken/YoutubeLiveChannelRecorder)"]
    process = None
    running = None
    enable_logs = False

    def start_recording(self, videoInput, videoLocation, headers=None,
                        format=None, StartIndex0=False):
        self.running = None
        command = ["-hide_banner"]
        if headers is None:
            headers = {}
        for header in headers:
            command.extend(
                ["-headers", '{0}: {1}'.format(header, headers[header])])
        if StartIndex0 is True:
            command.extend(['-live_start_index', '0'])
        if format is not None:
            command.extend(['-f', format])
        command.extend(['-i', videoInput, "-c:v", "copy", "-c:a", "copy", '-f', 'mpegts'])
        for metadata in self.recording_metadata:
            command.extend(['-metadata', metadata])
        command.extend([videoLocation])
        self.requestFFmpeg(command)
        self.__hold()
        if self.running is False:
            return False
        info("Recording Started.")
        return True

    def merge_streams(self, videoInput, videoLocation):
        """

        Merges streams using FFmpeg.

        :type videoInput: list
        :type videoLocation: str
        """
        self.running = None
        concat_file = os.path.join(os.getcwd(), 'temp_concat.txt')
        with open(concat_file, 'w') as file:
            now = datetime.now()
            file.write('# Automated Concat File Created At: {0}.\n'.format(
                str(now.strftime("%d/%m/%Y %I:%M %p"))))
            for video in videoInput:
                # '\''
                video = video.replace('\'', "'\\''")
                if video:
                    file.write('file \'{0}\'\n'.format(video))
            file.close()
        self.requestFFmpeg(["-f", "concat", "-y", "-safe", "0", "-i",
                            concat_file, "-c:v", "copy", "-c:a", "copy", videoLocation])
        self.__hold()
        if self.running is False:
            return False
        info("Merge Started.")
        return True

    def requestFFmpeg(self, arguments):
        command = ["ffmpeg", "-loglevel", "verbose"]  # Enables Full Logs
        command.extend(arguments)
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        stdin=subprocess.PIPE, universal_newlines=True)
        self.__startHandler()

    def __hold(self):
        while self.running is not None:
            sleep(1)

    def __startHandler(self):
        log = []

        def print_handle():
            for line in self.process.stdout:
                if 'frame=' in line:
                    self.last_frame_time = datetime.now()
                if self.enable_logs:
                    EncoderLog(line)
                if self.running is None:
                    log.append(line)
                    if "Press [q] to stop" in line:
                        self.running = True
            if self.running is None:
                warning("FFmpeg failed to start running.")
                self.running = False
                info("Saving FFmpeg Crash to Log File.")
                logfile = open('ffmpeg_logfile.txt', 'w')
                now = datetime.now()
                logfile.write("\n")
                logfile.write("" + str(now.year) + ", " + str(now.day) +
                              "/" + str(now.month) + " FFMPEG CRASH\n")
                del now
                logfile.write("\n")
                logfile.write(''.join(log))
            if self.running is True:
                self.running = False
                warning("FFmpeg has stopped.")
            exit()

        encoder_crash_handler = Thread(
            target=print_handle, name="FFMPEG Crash/LOG Handler.")
        encoder_crash_handler.daemon = True  # needed control+C to work.
        encoder_crash_handler.start()

    def stop_recording(self):
        if self.process:
            if self.running is True:
                info("Recording Stopped.")
                try:
                    self.process.terminate()
                    verbose("SENT KILL TO FFMPEG.")
                    # wait until kill.
                    self.process.wait()
                except subprocess:
                    warning(
                        "There was a problem terminating FFmpeg. It might be because it already closed. Oh NO")

