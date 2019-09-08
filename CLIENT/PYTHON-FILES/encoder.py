import subprocess
from datetime import datetime
from threading import Thread
from log import verbose, info, EncoderLog, warning


class FFmpeg:
    """
    
    FFmpeg Handler Class.
    
    :type video_url: str
    :type video_location: str
    :type crashFunction: function
    """

    video_url = None
    video_location = None
    process = None
    running = None
    crashFunction = None
    Headers = None
    last_line = None

    def __init__(self, url, videoLocation, crashFunction=None, Headers=None):
        self.video_url = url
        self.video_location = videoLocation
        self.crashFunction = crashFunction
        self.Headers = Headers

    def start_recording(self, videoURL=None, videoLocation=None):
        if videoURL is not None:
            self.video_url = videoURL
        if videoLocation is not None:
            self.video_location = videoLocation
        self.__run_Encoder(self.video_url, self.video_location)
        self.__hold()
        if not self.running:
            return False
        info("Downloading Started.")
        return True

    def __run_Encoder(self, video_url, videoLocation):
        self.running = None
        verbose("Opening FFmpeg.")
        command = ["ffmpeg", "-loglevel", "verbose"]  # Enables Full Logs
        if self.Headers:
            for header in self.Headers:
                command.extend(["-headers", '{0}: {1}'.format(header, self.Headers[header])])
        command.extend(["-y", "-i", video_url, "-c:v", "copy", "-c:a", "copy",
                       videoLocation])
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        stdin=subprocess.PIPE, universal_newlines=True)
        self.__startHandler()

    def __hold(self):
        while True:
            if self.running is not None:
                return None

    def __startHandler(self):
        log = []

        def print_handle():
            for line in self.process.stdout:
                EncoderLog(line)
                if self.running is None:
                    log.append(line)
                    if "Press [q] to stop" in line:
                        self.running = True
            if not self.running:
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
            if self.running:
                self.running = False
                warning("FFmpeg has stopped.")
            exit()

        encoder_crash_handler = Thread(
            target=print_handle, name="FFMPEG Crash/LOG Handler.")
        encoder_crash_handler.daemon = True  # needed control+C to work.
        encoder_crash_handler.start()

    def stop_recording(self):
        info("Recording Stopped.")
        if self.process.poll() is None:
            verbose("SENT KILL TO FFMPEG.")
            try:
                self.process.kill()
                # wait until kill.
                self.process.wait()
            except subprocess:
                warning("There was a problem terminating FFmpeg. It might be because it already closed. Oh NO")
