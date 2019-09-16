import os
import subprocess
from datetime import datetime
from threading import Thread
from time import sleep

from .log import verbose, info, EncoderLog, warning


class Encoder:
    """

    FFmpeg Handler Class.

    :type crashFunction: function
    """

    running = None
    process = None
    last_frame_time = None

    def __init__(self, crashFunction=None, Headers=None):
        self.crashFunction = crashFunction
        self.Headers = Headers

    def start_recording(self, videoInput, videoLocation):
        self.running = None
        self.requestFFmpeg(videoInput, videoLocation)
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
        self.requestFFmpegConcat(concat_file, videoLocation)
        self.__hold()
        if self.running is False:
            return False
        info("Merge Started.")
        return True

    def requestFFmpegConcat(self, concatFile, videoLocation):
        self.running = None
        verbose("Opening FFmpeg.")
        command = ["ffmpeg", "-loglevel", "verbose"]  # Enables Full Logs
        if self.Headers:
            for header in self.Headers:
                command.extend(
                    ["-headers", '{0}: {1}'.format(header, self.Headers[header])])
        command.extend(["-f", "concat", "-y", "-safe", "0", "-i", concatFile,
                        "-c:v", "copy", "-c:a", "copy", videoLocation])
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        stdin=subprocess.PIPE, universal_newlines=True)
        self.__startHandler()

    def requestFFmpeg(self, videoInput, videoLocation):
        self.running = None
        verbose("Opening FFmpeg.")
        command = ["ffmpeg", "-loglevel", "verbose"]  # Enables Full Logs
        if self.Headers:
            for header in self.Headers:
                command.extend(
                    ["-headers", '{0}: {1}'.format(header, self.Headers[header])])
        command.extend(["-y", "-i", videoInput, "-c:v", "copy", "-c:a", "copy",
                        "-movflags", "faststart", "-metadata",
                        "service_provider=FFmpeg (https://ffmpeg.org) <- YoutubeLiveChannelRecorder ("
                        "https://github.com/TheDaChicken/YoutubeLiveChannelRecorder)", "-f", "mpegts", videoLocation])
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        stdin=subprocess.PIPE, universal_newlines=True)
        self.__startHandler()

    def __hold(self):
        while True:
            if self.running is not None:
                return None
            sleep(.1)

    def __startHandler(self):
        log = []

        def print_handle():
            for line in self.process.stdout:
                if 'frame=' in line:
                    self.last_frame_time = datetime.now()
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
                    self.process.kill()
                    verbose("SENT KILL TO FFMPEG.")
                    # wait until kill.
                    self.process.wait()
                except subprocess:
                    warning(
                        "There was a problem terminating FFmpeg. It might be because it already closed. Oh NO")
