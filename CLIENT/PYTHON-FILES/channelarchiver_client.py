import os
import platform
import re
from time import sleep

from ServerFunctions import check_server, get_server_info, add_channel, remove_channel, youtube_fully_login, \
    youtube_fully_logout, listRecordings, playbackRecording, downloadRecording, get_server_settings, swap_settings, \
    get_youtube_api_info, youtube_login, youtube_logout, test_upload, update_data_cache, add_video_id
from utils import stringToInt
from log import info, stopped, warning, EncoderLog, Fore

serverIP = None
serverPort = None

# Windows ToastNotifier
if platform.release() is '10':
    try:
        from win10toast import ToastNotifier

        toaster = ToastNotifier()
    except ImportError:
        warning("win10toast isn't installed!"
                "Since you are using Windows 10, you can use that!")
        ToastNotifier = None
        toaster = None
else:
    toaster = None


#
#
#
#
# THIS IS VERY POORLY CODED BUT IT WORKS.
#
#
#

def setTitle(title):
    if platform.release() is '10':
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(title)


def clearScreen():
    os.system('cls' if os.name == "nt" else 'clear')


# Windows Notification
def show_windows_toast_notification(title, description):
    if toaster is not None:
        toaster.show_toast(title, description, icon_path='python.ico')


if __name__ == '__main__':
    print("")
    print("What is the Server IP?")
    serverIP = input(":")
    print("What is the Server Port?")
    serverPort = input(":")
    if serverPort is '':
        serverPort = '31311'
    info("Checking for Server port " + serverPort + " on " + serverIP)
    if not check_server(serverIP, serverPort):
        stopped("Server is not running! Try checking again.")
    else:
        setTitle('YoutubeLiveChannelRecorder [Connected to Server: ' + serverIP + " Port: " + serverPort + "]")
        info("Server Running.")
        info("Getting Server Info.")
        ok, serverInfo = get_server_info(serverIP, serverPort)
        if not ok:
            stopped("Error Response from Server: " + serverInfo)
        Screen = "Main"
        while True:
            if Screen is "Main":
                channel_info = serverInfo.get('channelInfo')
                youtube = serverInfo.get('youtube')
                youtubeAPI = serverInfo.get('youtubeAPI')
                if youtubeAPI:
                    uploadQueue = youtubeAPI.get('uploadQueue')

                loopNumber = 1
                clearScreen()
                print("")
                if len(channel_info['channel']) is 0:
                    print(Fore.LIGHTMAGENTA_EX + "No Channels currently added in the list.")
                else:
                    print("{0}List of Channels:\n".format(Fore.LIGHTMAGENTA_EX))
                    for channel_id in channel_info['channel']:
                        channelInfo = channel_info['channel'][channel_id]
                        channel_name = channelInfo.get('name')
                        is_alive = channelInfo['is_alive']

                        message = ["    {0}{1}: {2}{3}".format(Fore.LIGHTCYAN_EX, str(loopNumber),
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
                            HLSOutputStream = channelInfo.get('HLSOutputStream')
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
                                if HLSOutputStream:
                                    message.append("{0} [STREAM WATCHABLE IN HLS]".format(Fore.LIGHTYELLOW_EX,
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
                        # USING JOIN INSTEAD OF += ON STRING BECAUSE JOIN IS FASTER.
                        print(''.join(message))
                        loopNumber += 1
                if uploadQueue and uploadQueue.get('enabled'):
                    is_alive = uploadQueue.get('is_alive')
                    if is_alive:
                        status = '{0}{1}'.format(Fore.LIGHTRED_EX, uploadQueue.get('status'))
                    elif is_alive is None:
                        status = '{0}Starting up.'.format(Fore.LIGHTRED_EX)
                    elif is_alive is False:
                        status = '{0}Crashed.'.format(Fore.LIGHTYELLOW_EX)
                    print("\n{0}YouTube Upload Queue:".format(Fore.LIGHTMAGENTA_EX))
                    print("    {0}Status: {1}".format(Fore.LIGHTGREEN_EX, status))

                print("\n 1) Refresh Channel List.\n 2) Add Channel\n 3) Remove Channel\n 4) Change Settings")
                if 'YoutubeLogin' in youtube and youtube['YoutubeLogin'] is False:
                    print(" 5) " + Fore.LIGHTRED_EX + "Login to Youtube (FOR SPONSOR ONLY STREAMS) [VERY BUGGY] "
                                                      "")
                else:
                    print(" 5) " + Fore.LIGHTRED_EX + "Logout of Youtube.")
                print(" 6) {0}View Recordings.".format(Fore.LIGHTYELLOW_EX))
                print(" 7) Add Channel (USING VIDEO ID).")
                if toaster is not None and 'localhost' not in serverIP:
                    print(" N) Holds console, shows Windows 10 Toast Notification every time a stream goes live.")
                print("  - Type a specific number to do the specific action. - ")
                option = input(":")
                if option is "1":  # Just Refresh
                    info("Getting Server Info.")
                    ok, reply = get_server_info(serverIP, serverPort)
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        print("")
                        input("Press enter to go back to Selection.")
                    else:
                        serverInfo = reply
                elif option is "2":  # ADDING CHANNELS
                    print("To Find The Channel_IDs USE THIS: ")
                    print("https://commentpicker.com/youtube-channel-id.php")
                    temp_channel_id = input("Channel ID: ")
                    ok, reply = add_channel(serverIP, serverPort, temp_channel_id)
                    del temp_channel_id
                    print("")
                    print("")
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                    else:
                        print(Fore.LIGHTGREEN_EX + "Channel has now been added.")
                    print("")
                    input("Press enter to go back to Selection.")
                    # Refresh
                    info("Getting Server Info.")
                    ok, reply = get_server_info(serverIP, serverPort)
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        print("")
                        input("Press enter to go back to Selection.")
                    else:
                        serverInfo = reply
                elif option is "3":  # REMOVE CHANNELS (BETA ON SERVER)
                    print("  To Find The Channel_IDs USE THIS: ")
                    print("  https://commentpicker.com/youtube-channel-id.php")
                    temp_channel_id = input("Channel ID: ")
                    ok, reply = remove_channel(serverIP, serverPort, temp_channel_id)
                    del temp_channel_id
                    print("")
                    print("")
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                    else:
                        print(Fore.LIGHTGREEN_EX + "Channel has now been removed.")
                    print("")
                    input("Press enter to go back to Selection.")
                    # Refresh
                    info("Getting Server Info.")
                    ok, reply = get_server_info(serverIP, serverPort)
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        print("")
                        input("Press enter to go back to Selection.")
                    else:
                        serverInfo = reply
                elif option is "4":
                    info("Getting Server Settings")
                    ok, reply = get_server_settings(serverIP, serverPort)
                    info("Getting Youtube API Info")
                    ok2, reply2 = get_youtube_api_info(serverIP, serverPort)
                    if not ok:
                        print("")
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        print("")
                        input("Press enter to go back to Selection.")
                    elif not ok2:
                        print("")
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply2)
                        print("")
                        input("Press enter to go back to Selection.")
                    else:
                        server_settings = reply
                        server_youtube_api_info = reply2
                        Screen = "Settings"
                elif option is "N":  # WINDOWS 10 TOAST Notification HOLD
                    info("Now Checking.")
                    Screen = "NotificationHold"
                elif option is "5":
                    if channel_info['YoutubeLogin'] is False:
                        print("")
                        print("")
                        print("")
                        username_google = input("Username/Email: ")
                        print("")
                        print("")
                        password_google = input("Password: ")
                        print("")
                        print("")
                        sleep(.4)
                        print("")
                        print(Fore.LIGHTRED_EX + "Logging in...")
                        sleep(.3)
                        print("")
                        ok, reply = youtube_fully_login(serverIP, serverPort, username_google, password_google)
                        if not ok:
                            if not ok:
                                print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        else:
                            print(Fore.LIGHTGREEN_EX + "Login Successful!")
                        print("")
                        print("")
                        sleep(.3)
                        print("")
                        input("Press enter to go back to Selection.")
                        print("")
                        info("Getting Server Info.")
                        ok, reply = get_server_info(serverIP, serverPort)
                        if not ok:
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                            print("")
                            input("Press enter to go back to Selection.")
                        else:
                            serverInfo = reply
                    elif channel_info['YoutubeLogin'] is True:
                        print("")
                        print("")
                        print("")
                        print("")
                        print(Fore.LIGHTRED_EX + "Logging out...")
                        ok, reply = youtube_fully_logout(serverIP, serverPort)
                        if not ok:
                            if not ok:
                                print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        else:
                            print(Fore.LIGHTGREEN_EX + "Logout Successful!")
                        print("")
                        print("")
                        input("Press enter to go back to Selection.")
                        print("")
                        info("Getting Server Info.")
                        ok, reply = get_server_info(serverIP, serverPort)
                        if not ok:
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                            print("")
                            input("Press enter to go back to Selection.")
                        else:
                            serverInfo = reply
                elif option is "6":
                    Screen = "View-Recording"
                elif option is "7":
                    print("")
                    temp_channel_id = input("Video ID: ")
                    ok, reply = add_video_id(serverIP, serverPort, temp_channel_id)
                    del temp_channel_id
                    print("")
                    print("")
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                    else:
                        print(Fore.LIGHTGREEN_EX + "Video ID has now been added.")
                    print("")
                    input("Press enter to go back to Selection.")
                    # Refresh
                    info("Getting Server Info.")
                    ok, reply = get_server_info(serverIP, serverPort)
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        print("")
                        input("Press enter to go back to Selection.")
                    else:
                        serverInfo = reply
            elif Screen is "Settings":
                clearScreen()
                print("")
                print(Fore.LIGHTMAGENTA_EX + "List of Settings:")
                print("")
                loopNumber = 1
                server_settings_amount = len(server_settings)
                server_settings_list = list(map(str, server_settings))
                for server_setting_name in server_settings_list:
                    if server_settings.get(server_setting_name):
                        message = ["    {0}{1}: {2}{3}: {4}{5}{6} [SWITCH]".format(Fore.LIGHTCYAN_EX, str(loopNumber),
                                                                                   Fore.WHITE,
                                                                                   server_setting_name,
                                                                                   Fore.LIGHTMAGENTA_EX,
                                                                                   str(server_settings.get(
                                                                                       server_setting_name).get(
                                                                                       'value')),
                                                                                   Fore.LIGHTCYAN_EX)]
                        if 'description' in server_settings.get(server_setting_name):
                            message.append("\n         {0}{1}".format(Fore.WHITE,
                                                                      server_settings.get(
                                                                          server_setting_name).get('description')))
                        loopNumber += 1
                        print(''.join(message))
                if server_youtube_api_info:
                    message = ["    {0}{1}: {2}{3}: {4}{5}{6} ".format(Fore.LIGHTCYAN_EX, str(loopNumber),
                                                                       Fore.WHITE,
                                                                       'YouTube Account USING YOUTUBE API',
                                                                       Fore.LIGHTRED_EX,
                                                                       str(server_youtube_api_info.get(
                                                                           'YoutubeAccountLogin-in').get(
                                                                           'value')),
                                                                       Fore.LIGHTYELLOW_EX)]
                    if server_youtube_api_info.get('YoutubeAccountLogin-in').get('value'):
                        message.append('[SIGN OUT ({0})]'.format(server_youtube_api_info.get('YoutubeAccountName').
                                                                 get('value')))
                    else:
                        message.append('[LOGIN]')
                    if 'description' in server_youtube_api_info.get('YoutubeAccountLogin-in'):
                        message.append("\n         {0}{1}".format(Fore.WHITE,
                                                                  server_youtube_api_info.get(
                                                                      'YoutubeAccountLogin-in').get('description')))
                    print(''.join(message))
                    loopNumber += 1
                    message = ["    {0}{1}: {2}{3} {4}[ADDS CHANNEL ID TO TEST UPLOAD LIST]"
                               "\n         "
                               "{5}{6}Records a channel for a few seconds. Then tries uploading that through the "
                               "YouTube API.".format(
                        Fore.LIGHTCYAN_EX, str(loopNumber), Fore.WHITE, 'Test Upload', Fore.LIGHTRED_EX,
                        Fore.LIGHTYELLOW_EX, Fore.LIGHTRED_EX, Fore.WHITE)]
                    print(''.join(message))
                loopNumber += 1
                message = ["    {0}{1}: {2}{3} ".format(Fore.LIGHTCYAN_EX, str(loopNumber),
                                                        Fore.WHITE,
                                                        'Refresh Data File Cache',
                                                        Fore.LIGHTRED_EX,
                                                        Fore.LIGHTYELLOW_EX),
                           '{0}[REFRESH]'.format(Fore.LIGHTRED_EX),
                           "\n         {0}{1}".format(Fore.WHITE,
                                                      "Refreshes the cache created from the data.yml file.")]
                print(''.join(message))
                print("  - Type a specific number to do the specific action. - ")
                option = stringToInt(input(":"))
                if option:
                    if option < server_settings_amount or option == server_settings_amount:
                        ok, reply = swap_settings(serverIP, serverPort, server_settings_list[option - 1])
                        if not ok:
                            print("")
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                            print("")
                            input("Press enter to go back to Selection.")
                        info("Getting Server Settings")
                        ok, reply = get_server_settings(serverIP, serverPort)
                        if not ok:
                            print("")
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                            print("")
                            input("Press enter to go back to Selection.")
                        else:
                            server_settings = reply  # type: dict
                    elif option == (server_settings_amount + 1):
                        if not server_youtube_api_info.get('YoutubeAccountLogin-in').get('value'):
                            ok, reply = youtube_login(serverIP, serverPort)
                            print("")
                            print("")
                            if not ok:
                                print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                                print("")
                                input("Press enter to go back to Selection.")
                            else:
                                print(Fore.LIGHTRED_EX + "Go to this URL IN YOUR BROWSER: " + reply)
                                print("   "
                                      "On Windows, you should be able to copy the url "
                                      "by selecting the url and right clicking.")
                                print("")
                                input("Press enter to go back to Selection.")
                                print("")
                        else:
                            print("")
                            print("")
                            print("Signing out...")
                            ok, reply = youtube_logout(serverIP, serverPort)
                            if not ok:
                                print("")
                                print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                                sleep(3.5)
                        ok, reply = get_server_settings(serverIP, serverPort)
                        ok2, reply2 = get_youtube_api_info(serverIP, serverPort)
                        if not ok:
                            print("")
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                            print("")
                            input("Press enter to go back to Selection.")
                        elif not ok2:
                            print("")
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply2)
                            print("")
                            input("Press enter to go back to Selection.")
                        else:
                            server_settings = reply  # type: dict
                            server_youtube_api_info = reply2  # type: dict
                    elif option == (server_settings_amount + 2):
                        if server_youtube_api_info:
                            if not server_youtube_api_info.get('YoutubeAccountLogin-in').get('value'):
                                print("")
                                warning("There is no YouTube Account Logged into the YouTube API.\nIts best to use "
                                        "Test Upload with a YouTube Account Logged into the YouTube API.")
                                input("Press enter to keep going.")
                                print("")
                                print("")
                        print("To Find The Channel_IDs USE THIS: ")
                        print("https://commentpicker.com/youtube-channel-id.php")
                        temp_channel_id = input("Channel ID: ")
                        ok, reply = test_upload(serverIP, serverPort, temp_channel_id)
                        del temp_channel_id
                        print("")
                        print("")
                        if not ok:
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        else:
                            print(Fore.LIGHTGREEN_EX + "Channel has now been added.")
                        print("")
                        input("Press enter to go back to Selection.")
                        # Refresh
                        ok, reply = get_server_settings(serverIP, serverPort)
                        ok2, reply2 = get_youtube_api_info(serverIP, serverPort)
                        if not ok:
                            print("")
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                            print("")
                            input("Press enter to go back to Selection.")
                        elif not ok2:
                            print("")
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply2)
                            print("")
                            input("Press enter to go back to Selection.")
                        else:
                            server_settings = reply  # type: dict
                            server_youtube_api_info = reply2  # type: dict
                    elif option == (server_settings_amount + 3):
                        print("")
                        print("")
                        sleep(.5)
                        print(Fore.LIGHTRED_EX + "Updating the cache..")
                        ok, reply = update_data_cache(serverIP, serverPort)
                        if not ok:
                            print("")
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                            print("")
                            input("Press enter to go back to Selection.")
                else:
                    print(Fore.LIGHTRED_EX + "That is not a number!")
                    print("")
                    input("Press enter to go back to Selection.")
            elif Screen is "View-Recording":
                print("")
                ok, recordingList = listRecordings(serverIP, serverPort)
                if not ok:
                    print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                    print("")
                    input("Press enter to go back to Selection.")
                if len(recordingList) is 0:
                    print("{0} No Recordings Available!".format(Fore.LIGHTRED_EX))
                    print("")
                    input("Press enter to go back to Selection.")
                    info("Getting Server Info.")
                    ok, reply = get_server_info(serverIP, serverPort)
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        print("")
                        input("Press enter to go back to Selection.")
                    else:
                        channel_info = reply
                    del recordingList
                    Screen = "Main"
                else:
                    loopNumber = 1
                    print(Fore.LIGHTMAGENTA_EX + "List of Recordings:")
                    print("")
                    for recording in recordingList:
                        print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + recording)
                        loopNumber += 1
                    print("")
                    print(" 1) Play a Recording.")
                    print(" 2) Download a Recording.")
                    print("  - Type a specific number to do the specific action. - ")
                    option = input(":")
                    is_number = False
                    number = 0
                    if option is "1" or option is "2":
                        print("")
                        print("Type the number corresponding with the recording.")
                        print("")
                        recording_number = input("Recording Number: ")
                        print("")
                        try:
                            number = int(recording_number)
                            is_number = True
                        except ValueError:
                            print(Fore.LIGHTRED_EX + "That is not a number!")
                            sleep(3.5)
                    if is_number:
                        recording = recordingList[number - 1]
                        print("{0} Selected Recording: {1}".format(Fore.LIGHTMAGENTA_EX, recording))
                        sleep(1)
                        if option is "1":
                            print("")
                            print("{0} Starting Playback.".format(Fore.LIGHTMAGENTA_EX))
                            ffplay_class = playbackRecording(serverIP, serverPort, recording)
                            while True:
                                if not ffplay_class.running:
                                    break
                        if option is "2":
                            print("")
                            from os import path, getcwd

                            stream_output_location = path.join(getcwd(), recording)
                            if os.path.isfile(stream_output_location):
                                print("{0} File with the stream name already exists! Want to override?".format(
                                    Fore.LIGHTMAGENTA_EX))
                                print("")
                                answer_input = input(" YES/NO:")
                                if "NO" in answer_input or "no" in answer_input or "n" in answer_input:
                                    break
                                print("")
                            print("{0} Starting Download.".format(Fore.LIGHTMAGENTA_EX))
                            ffmpeg_class = downloadRecording(serverIP, serverPort, recording)
                            last_line = None
                            encoder_logs = False
                            try:
                                import keyboard
                            except ImportError:
                                keyboard = None
                            while True:
                                if ffmpeg_class.running:
                                    if keyboard:
                                        if not encoder_logs:
                                            if keyboard.is_pressed('q'):
                                                print("{0} Switched To Encoder Logs.".format(Fore.LIGHTGREEN_EX))
                                                encoder_logs = True
                                    if last_line is not ffmpeg_class.last_line:
                                        if last_line is not None:
                                            if encoder_logs:
                                                EncoderLog(last_line)
                                            else:
                                                frames = re.search(r'frame= (.+) f|frame=(.+) f', last_line)
                                                frames_tuple = frames.groups()
                                                frames = next(x for x in frames_tuple if x is not None)
                                                time = re.findall(r'time=(.+) b', last_line)
                                                clearScreen()
                                                print("")
                                                print("")
                                                print("===================")
                                                print("")
                                                print(
                                                    "    {0}DOWNLOADED FRAMES: {1}".format(Fore.LIGHTMAGENTA_EX,
                                                                                           frames
                                                                                           if frames is not None else
                                                                                           'Unknown'))
                                                print("    {0}DOWNLOADED VIDEO TIME: {1}".format(Fore.LIGHTMAGENTA_EX,
                                                                                                 time[0] if len(
                                                                                                     time) is not 0
                                                                                                 else 'Unknown'))
                                                print("")
                                                if not keyboard:
                                                    print("    {0}INSTALL KEYBOARD USING PIP TO SWITCH TO ENCODER LOGS."
                                                          .format(Fore.LIGHTRED_EX))
                                                else:
                                                    print("    {0}HOLD Q FOR A SECOND TO SWITCH TO "
                                                          "FFMPEG LOGS. (ENCODER LOGS)"
                                                          .format(Fore.LIGHTYELLOW_EX))
                                                print("===================")
                                                print("")
                                                print("")
                                        last_line = ffmpeg_class.last_line
                                        sleep(.2)
                                else:
                                    break
            elif Screen is "NotificationHold":
                channel_info_last = channel_info
                ok, reply = get_server_info(serverIP, serverPort)
                if not ok:
                    print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                    print("")
                else:
                    serverInfo = reply
                channel_info = serverInfo.get('channelInfo')
                for channel in channel_info['channels']:
                    channelInfo = channel_info['channel'][channel]
                    channelInfo_last = channel_info_last['channel'][channel]
                    if channelInfo['live'] is True and channelInfo_last['live'] is not True:
                        show_windows_toast_notification("Live Recording Notifications",
                                                        channelInfo['name'] + " is live and is now "
                                                                              "being recorded.")
                sleep(5)
