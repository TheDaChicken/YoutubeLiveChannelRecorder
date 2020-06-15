import os


def clearScreen():
    os.system('cls' if os.name == "nt" else 'clear')


def setTitle(title):
    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(title)
