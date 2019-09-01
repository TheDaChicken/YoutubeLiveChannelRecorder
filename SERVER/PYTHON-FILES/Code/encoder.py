import os
import subprocess
from threading import Thread
from time import sleep

from datetime import datetime

from .log import verbose, info, EncoderLog, warning


class Encoder:
    """

    FFmpeg Handler Class.

    :type crashFunction: function
    """

    running = None

    def __init__(self, crashFunction=None, Headers=None):
        self.crashFunction = crashFunction
        self.Headers = Headers

    def start_recording(self, videoInput, videoLocation):
        self.running = None
        self.__run_Encoder(videoInput, videoLocation)
        self.__hold()
        if not self.running:
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
        self.__run__Encoder_Concat(concat_file, videoLocation)
        self.__hold()
        if not self.running:
            return False
        info("Merge Started.")
        return True

    def __run__Encoder_Concat(self, concatFile, videoLocation):
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
        encoder_crash_handler = Thread(
            target=self.__crashHandler, name="FFMPEG Crash Handler.")
        encoder_crash_handler.daemon = True  # needed control+C to work.
        encoder_crash_handler.start()

    def __run_Encoder(self, videoInput, videoLocation):
        self.running = None
        verbose("Opening FFmpeg.")
        command = ["ffmpeg", "-loglevel", "verbose"]  # Enables Full Logs
        if self.Headers:
            for header in self.Headers:
                command.extend(
                    ["-headers", '{0}: {1}'.format(header, self.Headers[header])])
        command.extend(["-re", "-y", "-i", videoInput, "-c:v", "copy", "-c:a", "copy",
                        "-movflags", "faststart", "-metadata",
                        "service_provider=FFmpeg (https://ffmpeg.org) <- YoutubeLiveChannelRecorder ("
                        "https://github.com/TheDaChicken/YoutubeLiveChannelRecorder)", "-f", "mpegts", videoLocation])
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        stdin=subprocess.PIPE, universal_newlines=True)
        encoder_crash_handler = Thread(
            target=self.__crashHandler, name="FFMPEG Crash Handler.")
        encoder_crash_handler.daemon = True  # needed control+C to work.
        encoder_crash_handler.start()

    def __hold(self):
        while True:
            if self.running is not None:
                return None
            sleep(.1)

    # Handles when FFMPEG Crashes and when it's fully running.
    def __crashHandler(self):
        log = []
        for line in self.process.stdout:
            if True:
                EncoderLog(line)
            if self.running is None:
                log.append(line)
            if "Press [q] to stop" in line:
                self.running = True
        if self.running is True:
            warning("FFmpeg has stopped.")
            self.running = False
        else:
            warning("FFmpeg failed to start running.")
            self.running = False
            info("Saving FFmpeg Crash to Log File.")
            logfile = open('ffmpeg_logfile.txt', 'w')
            import datetime
            now = datetime.datetime.now()
            logfile.write("\n")
            logfile.write("" + str(now.year) + ", " + str(now.day) +
                          "/" + str(now.month) + " FFMPEG CRASH\n")
            del now
            del datetime
            logfile.write("\n")
            logfile.write(''.join(log))
        if self.crashFunction is not None:
            self.crashFunction()
        exit()  # It kinda of closes the thread...

    def stop_recording(self):
        info("Recording Stopped.")
        if self.process.poll() is None:
            verbose("SENT KILL TO FFMPEG.")
            try:
                self.process.kill()
                # wait until kill.
                self.process.wait()
            except subprocess:
                warning(
                    "There was a problem terminating FFmpeg. It might be because it already closed. Oh NO")
