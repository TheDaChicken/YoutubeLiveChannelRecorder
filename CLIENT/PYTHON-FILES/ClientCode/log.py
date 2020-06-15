from colorama import Fore, init
import sys

Verbose = True  # Enables Debug Logs
Reply = True

init(autoreset=True)


def info(text):
    sys.stdout.write("{0}[INFO] {1}\n".format(Fore.LIGHTCYAN_EX, text))


def verbose(text):
    if Verbose is True:
        sys.stdout.write("{0}[VERBOSE] {1}\n".format(Fore.LIGHTRED_EX, text))

def warning(text):
    print(Fore.LIGHTRED_EX + "[WARNING] " + "{}".format(text))


def stopped(text):
    sys.stdout.write("{0}{1}\n".format(Fore.LIGHTRED_EX, text))
    from time import sleep
    sleep(10)
    sys.exit(1)
