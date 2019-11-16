from colorama import Fore, init
import sys

Verbose = True  # Enables Debug Logs
Reply = True

init(autoreset=True)


# Sys.stdout.write is used to fix overlapping in printing.

def info(text):
    sys.stdout.write("{0}[INFO] {1}\n".format(Fore.LIGHTCYAN_EX, text))


def verbose(text):
    if Verbose is True:
        sys.stdout.write("{0}[VERBOSE] {1}\n".format(Fore.LIGHTRED_EX, text))


def warning(text):
    sys.stdout.write("{0}[WARNING] {1}\n".format(Fore.LIGHTRED_EX, text))


def crash_warning(text):
    sys.stdout.write("{0}[CRASH WARNING] {1}{2}\n".format(
        Fore.LIGHTYELLOW_EX, Fore.RESET, text))


def error_warning(text):
    sys.stdout.write("{0}[ERROR WARNING] {1}{2}\n".format(
        Fore.LIGHTYELLOW_EX, Fore.RESET, text))


def reply(text):
    if Reply is True:
        sys.stdout.write("{0}[REPLY] {1}\n".format(Fore.LIGHTMAGENTA_EX, text))


def TwitchSent(text):
    if Reply is True:
        sys.stdout.write("{0}[SENT TO TWITCH] {1}\n".format(Fore.LIGHTWHITE_EX, text))


def EncoderLog(text):
    sys.stdout.write("{0}[ENCODER] {1}{2}\n".format(
        Fore.LIGHTGREEN_EX, Fore.RESET, text))


def stopped(text):
    sys.stdout.write("{0}{1}\n".format(Fore.LIGHTRED_EX, text))
    from time import sleep
    sleep(10)
    sys.exit(1)


def note(text):
    sys.stdout.write("{0}[NOTE] {1}\n".format(Fore.LIGHTCYAN_EX, text))

