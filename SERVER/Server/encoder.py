import subprocess
import time
from abc import ABC, abstractmethod
from datetime import datetime
from threading import Thread
from typing import List

from Server.logger import get_logger


class FFmpegBase(ABC):
    @abstractmethod
    def get_command_argument(self) -> List[str]:
        pass


class FFmpegInput(FFmpegBase):
    def __init__(self, input_str: str):
        self.input = input_str

    def get_command_argument(self) -> List[str]:
        return ["-i", self.input]


class FFmpegFormat(FFmpegBase):
    def __init__(self, format_str: str):
        self.format = format_str

    def get_command_argument(self) -> List[str]:
        return ["-f", self.format]


class FFmpegCodec(FFmpegBase):
    def __init__(self, codec_name: str, type_='v'):
        self.codec_name = codec_name
        self.type = type_

    def get_command_argument(self):
        codec_arg = "-c"
        if self.codec_name != 'copy':
            codec_arg = ":{0}".format(self.type)

        return [codec_arg, self.codec_name]


class FFmpegOutput(FFmpegBase):
    def __init__(self, output: str):
        self.output = output

    def get_command_argument(self) -> List[str]:
        return [self.output]


class FFmpegHeaders(FFmpegBase):
    def __init__(self, headers):
        self.headers = headers

    def get_command_argument(self) -> List[str]:
        command = []
        list(map(lambda x: command.extend(["-headers", '{0}: {1}'.format(x, self.headers[x])]), self.headers))
        return command


class FFmpegMetadata(FFmpegBase):
    def __init__(self, metadata: dict):
        self.metadata = metadata

    def get_command_argument(self) -> List[str]:
        command = []
        list(map(lambda x: command.extend(["-metadata", '{0}={1}'.format(x, self.metadata[x])]), self.metadata))
        return command


class FFmpegHandler:
    enable_logs = False
    last_frame_time = None
    status_code = None
    process = None
    logging_name = "Encoder"

    def __init__(self):
        self._running = None

    def is_running(self):
        if self._running is None:
            return False
        return self._running

    def start_ffmpeg(self, *args):
        if self._running is not None:
            raise ValueError("Encoder Running")
        command_arguments = [
            'ffmpeg', '-hide_banner', '-loglevel', "verbose"]
        command_arguments.extend([
         arg for arg in args for arg in arg.get_command_argument()])
        self.process = subprocess.Popen(
            command_arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8')
        self._start_thread()
        self.hold_until_result()
        if self._running is True:
            get_logger(self.logging_name).info("Recording Started.")
        return self._running

    def print_handle(self):
        """
        For Thread
        """
        log = []

        for line in self.process.stdout:  # Holds until Program stops.
            line = line.strip()
            if 'frame=' in line:
                self.last_frame_time = datetime.now()
            get_logger().encoder(line)
            if len(log) > 400:
                # Don't store all of the log.
                log = log[390:0]
            log.append(line)
            if "Press [q]" in line:
                self._running = True

        if self._running is True:
            get_logger(self.logging_name).warning("FFmpeg has stopped.")

        self.process.wait()
        self.status_code = self.process.poll()
        if self.status_code:
            now = datetime.now()
            get_logger(self.logging_name).warning("Encoder Returned Code: {0}.".format(self.status_code))
            logfile = open('ffmpeg_logfile.txt', 'w')
            logfile.write("\n" + str(now.year) + ", " + str(now.day) +
                          "/" + str(now.month) + " FFMPEG CRASH\n\n")
            logfile.write('\n'.join(log))
            logfile.close()
            get_logger(self.logging_name).warning("See ffmpeg_logfile.txt for last few lines of FFmpeg Log.")
            del now

        del log
        self._running = None
        exit()

    def hold_until_result(self):
        while self._running is None:
            time.sleep(1)

    def _start_thread(self):
        thread = Thread(
            target=self.print_handle, name="FFMPEG Crash/LOG Handler.")
        thread.daemon = True  # needed for control+C to work.
        thread.start()

    def stop_recording(self):
        self._running = None
        if self.process:
            self.process.terminate()
            self.process.wait()


class FFmpegRecording(FFmpegHandler):
    default_metadata = {
        "service_provider":
            "FFmpeg (https://ffmpeg.org) <- YoutubeLiveChannelRecorder ("
            "https://github.com/TheDaChicken/YoutubeLiveChannelRecorder)"
    }

    def start_recording(self, input_str: str, output_str: str, headers=None, input_format=None):
        if headers is None:
            headers = {}
        ff_headers = FFmpegHeaders(headers)
        ff_input = FFmpegInput(input_str)
        ff_metadata = FFmpegMetadata(self.default_metadata)
        ff_copy = FFmpegCodec("copy")
        # ff_mpegts = FFmpegFormat("mpegts")
        ff_output = FFmpegOutput(output_str)
        input = [ff_headers, ff_input, ff_metadata, ff_copy, ff_output]
        if input_format is not None:
            ff_formatinput = FFmpegFormat(input_format)
            input.insert(1, ff_formatinput)
        return self.start_ffmpeg(*input)


