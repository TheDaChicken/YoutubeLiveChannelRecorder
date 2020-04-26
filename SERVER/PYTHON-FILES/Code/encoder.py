import os
import selectors
import subprocess
from datetime import datetime
from queue import Queue
from threading import Thread
from time import sleep

from .log import verbose, info, EncoderLog, warning


class Encoder:
    recording_metadata = ["service_provider=FFmpeg (https://ffmpeg.org) <- YoutubeLiveChannelRecorder ("
                          "https://github.com/TheDaChicken/YoutubeLiveChannelRecorder)"]
    process = None
    running = None
    enable_logs = False
    last_frame_time = None
    status_code = None

    def start_recording(self, videoInput, videoLocation, headers=None,
                        format=None, StartIndex0=False) -> bool:
        self.running = None
        command = ["-hide_banner"]
        if headers is None:
            headers = {}
        list(map(lambda x: command.extend(["-headers", '{0}: {1}'.format(x, headers[x])]), headers))
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
        if self.running is True:
            info("Recording Started.")
        return self.running

    def merge_streams(self, videoInput: list, videoLocation: str):
        """

        Merges streams using FFmpeg.

        """
        self.running = None
        now = datetime.now()
        concat_file = os.path.join(os.getcwd(), 'temp_concat.txt')
        with open(concat_file, 'w') as file:
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
        info("Recording Started.")
        return True

    def requestFFmpeg(self, arguments):
        command = ["ffmpeg", "-loglevel", "verbose"]  # Enables Full Logs
        command.extend(arguments)
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8')
        self.__startHandler()

    def __hold(self):
        while self.running is not None:
            sleep(1)

    def print_handle(self):
        log = []

        def handle_line(line):
            line = line.strip()
            if 'frame=' in line:
                self.last_frame_time = datetime.now()
            if self.enable_logs:
                EncoderLog(line)
            if self.running is None:
                log.append(line)
                if "Press [q] to stop" in line:
                    self.running = True

        list(map(handle_line, self.process.stdout))

        self.process.wait()
        warning("FFmpeg has stopped.")

        self.status_code = self.process.poll()
        if self.status_code:
            if self.running is not False:
                warning("Encoder Returned Code: {0}, {1}".format(self.status_code, ' '.join(log)))

        if self.running is None:
            now = datetime.now()
            warning("Saving FFmpeg Crash to Log File.")
            self.running = False
            logfile = open('ffmpeg_logfile.txt', 'w')
            logfile.write("\n" + str(now.year) + ", " + str(now.day) +
                          "/" + str(now.month) + " FFMPEG CRASH\n\n")
            del now
            logfile.write('\n'.join(log))
            logfile.close()
        if self.running is True:
            self.running = False
            warning("FFmpeg has stopped.")
        exit()

    def __startHandler(self):
        encoder_crash_handler = Thread(
            target=self.print_handle, name="FFMPEG Crash/LOG Handler.")
        encoder_crash_handler.daemon = True  # needed control+C to work.
        encoder_crash_handler.start()

    def stop_recording(self):
        if self.process and self.running is True:
                info("Recording Stopped.")
                try:
                    self.running = False
                    self.process.terminate()
                    verbose("SENT KILL TO FFMPEG.")
                    # wait until kill.
                    self.process.wait()
                except subprocess:
                    warning("There was a problem terminating FFmpeg. "
                            "It might be because it already closed. Oh NO")
