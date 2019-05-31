import os
from threading import current_thread

from colorama import Fore, init
import sys

Verbose = True  # Enables Debug Logs

init(autoreset=True)


def verbose(text):
    if Verbose:
        print(Fore.LIGHTRED_EX + "[VERBOSE] " + "{}".format(text))


def info(text):
    print(Fore.LIGHTCYAN_EX + "[INFO] " + "{}".format(text))


def warning(text):
    print(Fore.LIGHTRED_EX + "[WARNING] " + "{}".format(text))


def YoutubeReply(text):
    print(Fore.LIGHTMAGENTA_EX + "[REPLY] " + "{}".format(text))


def stopped(text):
    print(Fore.LIGHTRED_EX + "{}".format(text))
    from time import sleep
    sleep(5)
    sys.exit(1)


def note(text):
    print(Fore.LIGHTCYAN_EX + "[NOTE] " + "{}".format(text))


try:
    from threading import main_thread
except ImportError:
    stopped("Unsupported version of Python. You need Version 3 :<")


class Logger(object):
    # Enable Output to a file
    Logs = True
    file_holder = {}

    def __init__(self):
        import sys
        self.terminal = sys.stdout
        if self.Logs is True:
            import os
            log_directory = os.path.join(os.path.dirname(__file__), "logs")
            if not os.path.exists(log_directory):
                os.makedirs(log_directory)
        # self.log = open(path, "a")

    def write(self, message):
        self.terminal.write(message)
        # self.log.write(message)
        if self.Logs is True:
            if current_thread() is not main_thread():
                f = self.file_holder.get(current_thread(), open(self.path(), "a"))
                f.write(message)
                self.file_holder[current_thread()] = f

    def flush(self):
        f = self.file_holder.get(current_thread(), open(self.path(), "a"))
        f.flush()

    @staticmethod
    def path():
        log_directory = os.path.join(os.path.dirname(__file__), "logs")
        path = os.path.join(log_directory, current_thread().getName() + '.txt')
        return path
