from time import sleep

from ClientCode.screenHandler import Screen
from ClientCode.log import info, warning
from .serverHandler import isServerOnline, server_reply
from colorama import Fore, init


class Sub_MainMenu(Screen):
    def getName(self):
        return "Sub-MainMenu"

    def getConsoleTitle(self):
        return None

    def onScreen(self):
        print("")
        print("What is the Server IP?")
        ip = input(":")
        print("What is the Server Port?")
        port = input(":")
        if port is '':
            port = '31311'
        info("{0}Checking for Server port {1} on {2}.".format(Fore.LIGHTCYAN_EX, ip, port))
        if isServerOnline(ip, port):
            screen = MainMenu(ip, port)
            info("Getting Server Info.")
            ok, serverInfo = screen.get_server_info()
            if not ok:
                print("")
                if screen.serverInfo == "Cannot connect to server":
                    warning("Lost Connection to the server!".format(ip, port))
                else:
                    print("{1}Error Response from Server: {0}".format(screen.serverInfo, Fore.LIGHTRED_EX))
                input("\nPress enter to go back to Selection.")
            screen.serverInfo = serverInfo
            self.next_screen = screen
        else:
            print("\n{2}Unable to Connect to port {1} on {0}!".format(ip, port, Fore.LIGHTRED_EX))
            input("\nPress enter to go back to Selection.")


class MainMenu(Screen):
    serverInfo = None

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def get_server_info(self):
        function_name = 'serverInfo'
        arguments = {}
        return server_reply(self.ip, self.port, function_name, arguments)

    def getPlatforms(self):
        function_name = 'platforms'
        arguments = {}
        return server_reply(self.ip, self.port, function_name, arguments)

    def add_channel(self, SessionID, platform, dvr_recording):
        function_name = "addChannel/{0}".format(platform)
        arguments = {'SessionID': SessionID, 'dvr_recording': dvr_recording, "test_upload": True}
        return server_reply(self.ip, self.port, function_name, {}, data=arguments, RequestMethod='POST')

    def remove_channel(self, channel_identifier):
        function_name = "removeChannel"
        arguments = {'channel_identifier': channel_identifier}
        return server_reply(self.ip, self.port, function_name, arguments)

    def get_channel_info(self, channel_identifier, platform_name):
        function_name = "getChannel/{0}".format(platform_name)
        arguments = {'channel_identifier': channel_identifier}
        return server_reply(self.ip, self.port, function_name, arguments)

    def getName(self):
        return "MainMenu"

    def getConsoleTitle(self):
        return 'YoutubeLiveChannelRecorder ' \
               '[Connected to Server: {0} Port: {1}]'.format(self.ip, self.port)

    @staticmethod
    def formatChannelInfo(channelInfo, number):
        channel_id = channelInfo.get('channel_identifier')
        channel_name = channelInfo.get('name')
        is_alive = channelInfo['is_alive']
        # USING JOIN INSTEAD OF += ON STRING BECAUSE JOIN IS FASTER.
        message = ["    {0}{1}: {2}{3}".format(Fore.LIGHTCYAN_EX, str(number),
                                               Fore.WHITE,
                                               channel_name
                                               if channel_name is not None else channel_id)]
        
        if channel_name is None:
            if 'error' in channelInfo:
                message.append("{0} [FAILED GETTING YOUTUBE DATA]".format(Fore.LIGHTRED_EX))
            else:
                message.append("{0} [GETTING YOUTUBE DATA]".format(Fore.LIGHTRED_EX))
        elif is_alive:
            live = channelInfo.get('live')
            recording_status = channelInfo.get('recording_status')
            broadcastId = channelInfo.get('broadcastId')
            last_heartbeat = channelInfo.get('last_heartbeat')
            privateStream = channelInfo.get('privateStream')
            sponsor_on_channel = channelInfo.get('sponsor_on_channel')
            live_scheduled = channelInfo.get('live_scheduled')
            video_id = channelInfo.get('video_id')
            if live is None:
                message.append("{0} [INTERNET OFFLINE]".format(Fore.LIGHTBLUE_EX))
            elif live is True:
                message.append("{0} [LIVE]".format(Fore.LIGHTRED_EX))
                message.append("{0} Status: {1}".format(Fore.LIGHTRED_EX,
                                                        recording_status if recording_status is not None
                                                        else 'UNKNOWN.'))
                if video_id:
                    message.append("{0} [VIDEO ID: {1}]".format(Fore.LIGHTMAGENTA_EX, video_id))
                if broadcastId:
                    message.append("{0} [RECORDING BROADCAST ID: {1}]".format(Fore.LIGHTYELLOW_EX,
                                                                              broadcastId))
            elif live is False:
                if privateStream is True:
                    message.append("{0} [PRIVATE]".format(Fore.LIGHTRED_EX))
                    if sponsor_on_channel is True:
                        message.append(
                            " [SPONSOR MODE (CHECKS COMMUNITY TAB FOR SPONSOR ONLY STREAMS)]")
                elif live_scheduled is True:
                    live_scheduled_time = channelInfo.get('live_scheduled_time')
                    message += "{0} [SCHEDULED AT {1} (AT SERVER\'S TIMEZONE)]".format(
                        Fore.LIGHTGREEN_EX, live_scheduled_time)
                else:
                    message.append("{0} [NOT LIVE]".format(Fore.LIGHTCYAN_EX))
                    if last_heartbeat:
                        message.append("{0} [LAST HEARTBEAT: {1}]".format(Fore.LIGHTYELLOW_EX,
                                                                          last_heartbeat))
            elif live is 1:
                message.append("{0} [ERROR ON HEARTBEAT]".format(Fore.LIGHTRED_EX))
            elif not is_alive:
                message.append("{0} [CRASHED]".format(Fore.LIGHTYELLOW_EX))
            return message
        return message

    def onScreen(self):
        channelList = self.serverInfo.get('channelInfo')
        print("")
        if len(channelList['channel']) is 0:
            print("{0}No Channels currently added in the list.".format(Fore.LIGHTMAGENTA_EX))
        else:
            print("{0}List of Channels:\n".format(Fore.LIGHTMAGENTA_EX))
            loopNumber = 1
            for channel_id in channelList['channel']:
                channelInfo = channelList['channel'][channel_id]
                print(''.join(self.formatChannelInfo(channelInfo, loopNumber)))
                loopNumber += 1
        print("")
        print("\n 1) Refresh Channel List.\n 2) Add Channel\n 3) Remove Channel\n 4) Change Settings")
        print("  - Type a specific number to do the specific action. - ")
        option = input(":")
        if option is "1":  # Just Refresh
            info("Getting Server Info.")
            okay, serverInfo = self.get_server_info()
            if not okay:
                if serverInfo == "Cannot connect to server":
                    print("{0}Unable to connect to server.".format(Fore.LIGHTRED_EX))
                else:
                    print("{1}Error Response from Server: {0}".format(serverInfo, Fore.LIGHTRED_EX))
                input("\nPress enter to go back to Selection.")
            else:
                self.serverInfo = serverInfo
        elif option is "2":
            info("Getting Platforms.")
            okay, platforms = self.getPlatforms()
            if not okay:
                print("")
                if platforms == "Cannot connect to server":
                    print("{0}Unable to connect to server.".format(Fore.LIGHTRED_EX))
                    return
                else:
                    print("{1}Error Response from Server: {0}".format(platforms, Fore.LIGHTRED_EX))
                    print("")
                    platforms = ['YOUTUBE']
            print("\n\n  Platform List:")
            print("  {0}".format(', '.join(platforms)))
            platform = input("Platform: ")
            print("")
            if platform.lower() not in list(map(lambda x: x.lower(), platforms)):
                print("{0}Unknown Platform: {1}".format(Fore.LIGHTRED_EX, platform))
                input("\nPress enter to go back to Selection.")
                return
            else:
                print("  To Find The Channel_IDs (for YouTube) USE THIS: ")
                print("  https://commentpicker.com/youtube-channel-id.php")
                channel_id = input("Channel Identifier: ")
                ok, channelInfo = self.get_channel_info(channel_id, platform)
                if not ok:
                    print("")
                    print("\n{0}Error Response from Server: {1}\n".format(Fore.LIGHTRED_EX, channelInfo))
                    input("Press enter to go back to Selection.")
                else:
                    SessionID = channelInfo.get('SessionID')
                    if channelInfo.get('alreadyList') is True:
                        print("")
                        print("\n{0}Error Response from Server: {1}\n".format(
                            Fore.LIGHTRED_EX, "Channel Already in List!"))
                        input("Press enter to go back to Selection.")
                    else:
                        record_dvr = False
                        if channelInfo.get('dvr_enabled') is True:
                            print("{0}[BETA]\n{1}"
                                  "      This channel is streaming and has DVR enabled. \n"
                                  "      Would you want to download the DVR? \n"
                                  "      This will allow to download the whole stream "
                                  "if the stream's DVR starts at the beginning of the stream.".format(Fore.LIGHTRED_EX, Fore.LIGHTWHITE_EX))
                            booleanString = input('Boolean [Yes, No]:')
                            if 'y' in booleanString.lower():
                                print("\nEnabling Downloading DVR for {0} for this channel instance.".format(channelInfo.get('channel_name')))
                                record_dvr = True
                        ok, message = self.add_channel(SessionID, platform, record_dvr)
                        print("\n")
                        if not ok:
                            print("{0}Error Response from Server: {1}".format(Fore.LIGHTRED_EX, message))
                        else:
                            print("{0}Channel has now been added.".format(Fore.LIGHTGREEN_EX))
                        input("\nPress enter to go back to Selection.")
                        sleep(1)
                        # Refresh
                        info("Getting Server Info.")
                        ok, reply = self.get_server_info()
                        if not ok:
                            print("{0}Error Response from Server: {1}".format(Fore.LIGHTRED_EX, reply))
                            print("")
                            input("Press enter to go back to Selection.")
                        else:
                            self.serverInfo = reply
        elif option is "3":
            print("  To Find The Channel_IDs (for YouTube) USE THIS: ")
            print("  https://commentpicker.com/youtube-channel-id.php")
            channel_identifier = input("Channel Identifier: ")
            ok, reply = self.remove_channel(channel_identifier)
            print("\n")
            if not ok:
                print("{0}Error Response from Server: {1}".format(Fore.LIGHTRED_EX, reply))
            else:
                print("{0}Channel has now been removed.".format(Fore.LIGHTGREEN_EX))
            input("\nPress enter to go back to Selection.")
            # Refresh
            info("Getting Server Info.")
            ok, reply = self.get_server_info()
            if not ok:
                print("{0}Error Response from Server: {1}".format(Fore.LIGHTRED_EX, reply))
                print("")
                input("Press enter to go back to Selection.")
            else:
                self.serverInfo = reply


