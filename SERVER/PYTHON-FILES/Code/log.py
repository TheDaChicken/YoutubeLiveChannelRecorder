from colorama import Fore, init
import sys

Verbose = True  # Enables Debug Logs
Reply = True

init(autoreset=True)


# Sys.stdout.write is used to fix overlapping in printing.

def info(text):
    sys.stdout.write("{0}[INFO] {1}\n".format(Fore.LIGHTCYAN_EX, text))
    sys.stdout.flush()


def verbose(text):
    if Verbose is True:
        sys.stdout.write("{0}[VERBOSE] {1}\n".format(Fore.LIGHTRED_EX, text))
    sys.stdout.flush()


def warning(text):
    sys.stdout.write("{0}[WARNING] {1}\n".format(Fore.LIGHTRED_EX, text))
    sys.stdout.flush()


def crash_warning(text):
    sys.stdout.write("{0}[CRASH WARNING] {1}{2}\n".format(
        Fore.LIGHTYELLOW_EX, Fore.RESET, text))
    sys.stdout.flush()


def error_warning(text):
    sys.stdout.write("{0}[ERROR WARNING] {1}{2}\n".format(
        Fore.LIGHTYELLOW_EX, Fore.RESET, text))
    sys.stdout.flush()


def YoutubeReply(text):
    if Reply is True:
        sys.stdout.write("{0}[REPLY] {1}\n".format(Fore.LIGHTMAGENTA_EX, text))
    sys.stdout.flush()


def EncoderLog(text):
    sys.stdout.write("{0}[ENCODER] {1}{2}\n".format(
        Fore.LIGHTGREEN_EX, Fore.RESET, text))
    sys.stdout.flush()


def stopped(text):
    sys.stdout.write("{0}{1}\n".format(Fore.LIGHTRED_EX, text))
    sys.stdout.flush()
    from time import sleep
    sleep(10)
    sys.exit(1)


def note(text):
    sys.stdout.write("{0}[NOTE] {1}\n".format(Fore.LIGHTCYAN_EX, text))
    sys.stdout.flush()
