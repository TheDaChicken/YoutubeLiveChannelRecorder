import subprocess
from threading import Thread

from log import info, verbose, warning, EncoderLog


class FFplay:
    """

    FFplay Handler Class.

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
        self.__run_player(self.video_url)
        self.__hold()
        if not self.running:
            return False
        info("FFplay Started.")
        return True

    def __run_player(self, video_url):
        self.running = None
        verbose("Opening FFplay.")
        command = ["ffplay", "-loglevel", "verbose", "-x", "1280", "-y", "720", "-window_title",
                   "YouTubeLiveChannelRecoder - FFPLAY", "-i", video_url]
        if self.Headers:
            for header in self.Headers:
                command.extend(["-headers", '{0}: {1}'.format(header, self.Headers[header])])
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        stdin=subprocess.PIPE, universal_newlines=True)
        encoder_crash_handler = Thread(target=self.__crashHandler, name="FFPLAY Crash Handler.")
        encoder_crash_handler.daemon = True  # needed control+C to work.
        encoder_crash_handler.start()

    def __hold(self):
        while True:
            if self.running is not None:
                return None

    # Handles when FFMPEG Crashes and when it's fully running.
    def __crashHandler(self):
        log = []
        time = 0
        for line in self.process.stdout:
            if self.running is None:
                EncoderLog(line)
                log.append(line)
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
            logfile.write(''.join(line))
        if self.crashFunction is not None:
            self.crashFunction()
        exit()  # It kinda of closes the thread...

    def stop_playback(self):
        info("FFplay Stopped.")
        if self.process.poll() is None:
            verbose("SENT KILL TO FFplay.")
            try:
                self.process.kill()
                # wait until kill.
                self.process.wait()
            except subprocess:
                warning("There was a problem terminating FFplay. It might be because it already closed. Oh NO")


class VLC:
    """

    VLC Handler Class.

    :type video_url: str
    :type crashFunction: function
    """

    video_url = None
    process = None
    running = None
    crashFunction = None
    Headers = None
    VLCLocation = None

    def __init__(self, url, crashFunction=None, Headers=None, VLCLocation=None):
        self.video_url = url
        self.crashFunction = crashFunction
        self.Headers = Headers
        self.VLCLocation = VLCLocation

    def start_playback(self, videoURL=None):
        if videoURL is not None:
            self.video_url = videoURL
        self.__run_player(self.video_url)
        self.__hold()
        if not self.running:
            return False
        info("VLC Started.")
        return True

    def __run_player(self, video_url):
        self.running = None
        verbose("Opening VLC.")
        command = [self.VLCLocation if self.VLCLocation is not None else 'vlc',
                   video_url, ":http-user-agent={0}".format("WEB-CLIENT"),
                   "--meta-title=YouTubeLiveChannelRecoder"]
        if self.Headers:
            warning("HEADERS NOT SUPPORTED IN VLC.")
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        stdin=subprocess.PIPE, universal_newlines=True)
        encoder_crash_handler = Thread(target=self.__crashHandler, name="VLC Crash Handler.")
        encoder_crash_handler.daemon = True  # needed control+C to work.
        encoder_crash_handler.start()

    def __hold(self):
        while True:
            if self.running is not None:
                return None

    # Handles when FFMPEG Crashes and when it's fully running.
    def __crashHandler(self):
        log = []
        time = 0
        for line in self.process.stdout:
            if self.running is None:
                log.append(line)
                if "Running vlc with the default interface" in line:
                    self.running = True
        if self.running is True:
            self.running = False
            warning("VLC has stopped.")
        else:
            self.running = False
            warning("VLC failed to start playback.")
            info("Saving VLC Crash to Log File.")
            logfile = open('VLC_logfile.txt', 'w')
            import datetime
            now = datetime.datetime.now()
            logfile.write("\n")
            logfile.write("" + str(now.year) + ", " + str(now.day) + "/" + str(now.month) + " FFplay CRASH\n")
            del now
            del datetime
            logfile.write("\n")
            logfile.write(''.join(log))
        if self.crashFunction is not None:
            self.crashFunction()
        exit()  # It kinda of closes the thread...

    def stop_playback(self):
        info("VLC Stopped.")
        if self.process.poll() is None:
            verbose("SENT KILL TO VLC.")
            try:
                self.process.kill()
                # wait until kill.
                self.process.wait()
            except subprocess:
                warning("There was a problem terminating FFplay. It might be because it already closed. Oh NO")
