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
    if text:
        print(Fore.LIGHTRED_EX + "{}".format(text))
    from time import sleep
    sleep(5)
    sys.exit(1)


def EncoderLog(text):
    sys.stdout.write(Fore.LIGHTGREEN_EX + "[ENCODER] " + Fore.RESET + "{}\n".format(text))
    sys.stdout.flush()


def note(text):
    print(Fore.LIGHTCYAN_EX + "[NOTE] " + "{}".format(text))


try:
    from threading import main_thread
except ImportError:
    stopped("Unsupported version of Python. You need Version 3 :<")
