from colorama import Fore, init
import sys

Verbose = True  # Enables Debug Logs
Reply = True

init(autoreset=True)


def info(text):
    sys.stdout.write(Fore.LIGHTCYAN_EX + "[INFO] " + "{}".format(text) + "\n")


def verbose(text):
    if Verbose is True:
        sys.stdout.write(Fore.LIGHTRED_EX + "[VERBOSE] " + "{}".format(text) + "\n")


def warning(text):
    sys.stdout.write(Fore.LIGHTRED_EX + "[WARNING] " + "{}".format(text) + "\n")


def disable_youtube_reply():
    global Reply
    Reply = False


def YoutubeReply(text):
    if Reply is True:
        sys.stdout.write(Fore.LIGHTMAGENTA_EX + "[REPLY] " + "{}".format(text) + "\n")


def EncoderLog(text):
    sys.stdout.write(Fore.LIGHTGREEN_EX + "[ENCODER] " + Fore.RESET + "{}".format(text) + "\n")


def stopped(text):
    sys.stdout.write(Fore.LIGHTRED_EX + "{}".format(text) + "\n")
    from time import sleep
    sleep(10)
    sys.exit(1)


def note(text):
    sys.stdout.write(Fore.LIGHTCYAN_EX + "[NOTE] " + "{}".format(text) + "\n")
