import subprocess
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
        info("Recording Started.")
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
        encoder_crash_handler = Thread(target=self.__crashHandler, name="FFMPEG Crash Handler.")
        encoder_crash_handler.daemon = True  # needed control+C to work.
        encoder_crash_handler.start()

    def __hold(self):
        while True:
            if self.running is not None:
                return None

    # Handles when FFMPEG Crashes and when it's fully running.
    def __crashHandler(self):
        log = ""
        for line in self.process.stdout:
            if True:
                EncoderLog(line)
            if self.running is None and self.running is not None:
                log += line
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
            logfile.write("" + str(now.year) + ", " + str(now.day) + "/" + str(now.month) + " FFMPEG CRASH\n")
            del now
            del datetime
            logfile.write("\n")
            logfile.write(log)
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
                warning("There was a problem terminating FFmpeg. It might be because it already closed. Oh NO")


class FFplay:
    """

    FFmpeg Handler Class.

    :type video_url: str
    :type crashFunction: function
    """

    video_url = None
    process = None
    running = None
    crashFunction = None
    Headers = None

    def __init__(self, url, crashFunction=None, Headers=None):
        self.video_url = url
        self.crashFunction = crashFunction
        self.Headers = Headers

    def start_playback(self, videoURL=None):
        if videoURL is not None:
            self.video_url = videoURL
        self.__run_Encoder(self.video_url)
        self.__hold()
        if not self.running:
            return False
        info("Recording Started.")
        return True

    def __run_Encoder(self, video_url):
        self.running = None
        verbose("Opening FFmpeg.")
        command = ["ffplay", "-loglevel", "verbose", "-x", "1280", "-y", "720", "-i", video_url]
        if self.Headers:
            for header in self.Headers:
                command.extend(["-headers", '{0}: {1}'.format(header, self.Headers[header])])
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        stdin=subprocess.PIPE, universal_newlines=True)
        encoder_crash_handler = Thread(target=self.__crashHandler, name="FFMPEG Crash Handler.")
        encoder_crash_handler.daemon = True  # needed control+C to work.
        encoder_crash_handler.start()

    def __hold(self):
        while True:
            if self.running is not None:
                return None

    # Handles when FFMPEG Crashes and when it's fully running.
    def __crashHandler(self):
        log = ""
        time = 0
        for line in self.process.stdout:
            if True:
                EncoderLog(line)
            if self.running is None and self.running is not None:
                log += line
            if "fd=" in line:
                time += 1
                if time > 2:
                    self.running = True
        if self.running is True:
            warning("FFplay has stopped.")
            self.running = False
        else:
            warning("FFplay failed to start playback.")
            self.running = False
            info("Saving FFplay Crash to Log File.")
            logfile = open('ffplay_logfile.txt', 'w')
            import datetime
            now = datetime.datetime.now()
            logfile.write("\n")
            logfile.write("" + str(now.year) + ", " + str(now.day) + "/" + str(now.month) + " FFplay CRASH\n")
            del now
            del datetime
            logfile.write("\n")
            logfile.write(log)
        if self.crashFunction is not None:
            self.crashFunction()
        exit()  # It kinda of closes the thread...

    def stop_playback(self):
        info("Recording Stopped.")
        if self.process.poll() is None:
            verbose("SENT KILL TO FFMPEG.")
            try:
                self.process.kill()
                # wait until kill.
                self.process.wait()
            except subprocess:
                warning("There was a problem terminating FFplay. It might be because it already closed. Oh NO")
