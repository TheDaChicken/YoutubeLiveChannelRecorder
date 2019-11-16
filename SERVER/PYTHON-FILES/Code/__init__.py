from multiprocessing.managers import BaseManager


class ThreadHandler:
    channels_dict = {}

    debug_mode = False
    serverPort = 31311

    def __init__(self):
        # Create Shared Variables
        BaseManager.register("")

    def loadChannels(self):
        pass
