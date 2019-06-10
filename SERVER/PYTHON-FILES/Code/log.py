from colorama import Fore, init
import sys

Verbose = True  # Enables Debug Logs
Reply = True

init(autoreset=True)


# Sys.stdout.write is used to fix overlapping in printing.

def info(text):
    sys.stdout.write(Fore.LIGHTCYAN_EX + "[INFO] " + "{}".format(text) + "\n")
    sys.stdout.flush()


def verbose(text):
    if Verbose is True:
        sys.stdout.write(Fore.LIGHTRED_EX + "[VERBOSE] " + "{}".format(text) + "\n")
    sys.stdout.flush()


def warning(text):
    sys.stdout.write(Fore.LIGHTRED_EX + "[WARNING] " + "{}".format(text) + "\n")
    sys.stdout.flush()


def disable_youtube_reply():
    global Reply
    Reply = False


def YoutubeReply(text):
    if Reply is True:
        sys.stdout.write(Fore.LIGHTMAGENTA_EX + "[REPLY] " + "{}".format(text) + "\n")
    sys.stdout.flush()


def EncoderLog(text):
    sys.stdout.write(Fore.LIGHTGREEN_EX + "[ENCODER] " + Fore.RESET + "{}".format(text) + "\n")
    sys.stdout.flush()


def stopped(text):
    sys.stdout.write(Fore.LIGHTRED_EX + "{}".format(text) + "\n")
    sys.stdout.flush()
    from time import sleep
    sleep(10)
    sys.exit(1)


def note(text):
    sys.stdout.write(Fore.LIGHTCYAN_EX + "[NOTE] " + "{}".format(text) + "\n")
    sys.stdout.flush()
