from colorama import Fore, init
import sys

Verbose = True  # Enables Debug Logs
Reply = True

init(autoreset=True)


def info(text):
    print(Fore.LIGHTCYAN_EX + "[INFO] " + "{}".format(text))


def verbose(text):
    if Verbose is True:
        print(Fore.LIGHTRED_EX + "[VERBOSE] " + "{}".format(text))


def warning(text):
    print(Fore.LIGHTRED_EX + "[WARNING] " + "{}".format(text))


def disable_youtube_reply():
    global Reply
    Reply = False


def YoutubeReply(text):
    if Reply is True:
        print(Fore.LIGHTMAGENTA_EX + "[REPLY] " + "{}".format(text))


def EncoderLog(text):
    print(Fore.LIGHTGREEN_EX + "[ENCODER] " + Fore.RESET + "{}".format(text))


def stopped(text):
    print(Fore.LIGHTRED_EX + "{}".format(text))
    from time import sleep
    sleep(10)
    sys.exit(1)


def note(text):
    print(Fore.LIGHTCYAN_EX + "[NOTE] " + "{}".format(text))
