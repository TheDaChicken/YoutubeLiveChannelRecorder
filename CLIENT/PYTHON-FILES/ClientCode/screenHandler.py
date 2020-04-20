from abc import abstractmethod, ABC
from threading import Thread

from .utils.other import setTitle, clearScreen


class Screen(ABC):
    next_screen = None

    @staticmethod
    def clearScreen():
        return clearScreen()

    @abstractmethod
    def getName(self):
        return None

    @abstractmethod
    def getConsoleTitle(self):
        return None

    @abstractmethod
    def onScreen(self):
        pass


class ScreenHandler():
    currentScreen = None
    screenThread = None

    def setScreen(self, screenObject):
        """

        :type screenObject: Screen
        """
        self.currentScreen = screenObject

    def startScreenSystem(self):
        while True:
            clearScreen()
            if self.currentScreen.getConsoleTitle() is not None:
                setTitle(self.currentScreen.getConsoleTitle())
            self.currentScreen.onScreen()
            if self.currentScreen.next_screen is not None:
                self.currentScreen = self.currentScreen.next_screen
