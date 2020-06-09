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

    def start_recording(self, video_input, video_location: str, headers=None, format=None, StartIndex0=False) -> bool:
        command = ["-hide_banner"]
        if headers is None:
            headers = {}
        list(map(lambda x: command.extend(["-headers", '{0}: {1}'.format(x, headers[x])]), headers))
        if StartIndex0 is True:
            command.extend(['-live_start_index', '0'])
        if format is not None:
            command.extend(['-f', format])
        command.extend(['-i', video_input, "-c:v", "copy", "-c:a", "copy", '-f', 'mpegts'])
        for metadata in self.recording_metadata:
            command.extend(['-metadata', metadata])
        command.extend([video_location])
        self.requestFFmpeg(command)
        self.hold_until_result()
        if self.running is True:
            info("Recording Started.")
        return self.running or False

    def merge_streams(self, video_input: list, video_location: str):
        """

        Merges streams using FFmpeg.

        """
        now = datetime.now()
        concat_file = os.path.join(os.getcwd(), 'temp_concat.txt')
        with open(concat_file, 'w') as file:
            file.write('# Automated Concat File Created At: {0}.\n'.format(
                str(now.strftime("%d/%m/%Y %I:%M %p"))))
            for video in video_input:
                # '\''
                video = video.replace('\'', "'\\''")
                if video:
                    file.write('file \'{0}\'\n'.format(video))
            file.close()
        self.requestFFmpeg(["-f", "concat", "-y", "-safe", "0", "-i",
                            concat_file, "-c:v", "copy", "-c:a", "copy", video_location])
        self.hold_until_result()
        if self.running is True:
            info("Recording Started.")
        return self.running or False

    def requestFFmpeg(self, arguments):
        self.running = None
        command = ["ffmpeg", "-loglevel", "verbose"]  # Enables Full Logs
        command.extend(arguments)
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8')
        self._start_thread()

    def hold_until_result(self):
        while self.running is None:
            sleep(1)

    def print_handle(self):
        """
        For Thread
        """
        log = []

        for line in self.process.stdout:  # Holds until Program stops.
            line = line.strip()
            if 'frame=' in line:
                self.last_frame_time = datetime.now()
            if self.enable_logs:
                EncoderLog(line)
            if len(log) > 400:
                # Don't store all of the log
                log = log[390:0]
            log.append(line)
            if self.running is None:
                if "Press [q]" in line:
                    self.running = True

        self.process.wait()
        self.running = False
        warning("FFmpeg has stopped.")

        self.status_code = self.process.poll()
        if self.status_code:
            if self.running is not False:
                now = datetime.now()
                warning("Encoder Returned Code: {0}.".format(self.status_code))
                logfile = open('ffmpeg_logfile.txt', 'w')
                logfile.write("\n" + str(now.year) + ", " + str(now.day) +
                              "/" + str(now.month) + " FFMPEG CRASH\n\n")
                logfile.write('\n'.join(log))
                logfile.close()
                warning("See ffmpeg_logfile.txt for last few lines of FFmpeg Log.")
                del now

        del log
        if self.running is True:
            self.running = False
            warning("FFmpeg has stopped.")
        exit()

    def _start_thread(self):
        thread = Thread(
            target=self.print_handle, name="FFMPEG Crash/LOG Handler.")
        thread.daemon = True  # needed for control+C to work.
        thread.start()

    def stop_recording(self):
        if self.process and self.running is True:
            try:
                self.running = False
                self.process.terminate()
                verbose("SENT KILL TO FFMPEG.")
                # wait until kill.
                self.process.wait()
                info("Recording Stopped.")
            except subprocess:
                warning("There was a problem terminating FFmpeg. "
                        "It might be because it already closed. Oh NO")
