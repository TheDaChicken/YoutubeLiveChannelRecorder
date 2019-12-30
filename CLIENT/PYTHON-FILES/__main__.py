from Code.screenHandler import ScreenHandler
from Code.screens import Sub_MainMenu

if __name__ == '__main__':
    screenHandler = ScreenHandler()
    screenHandler.setScreen(Sub_MainMenu())
    screenHandler.startScreenSystem()
