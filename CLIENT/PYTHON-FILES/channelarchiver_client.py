import os
import platform
import re
from time import sleep

from log import info, stopped, warning, EncoderLog
from colorama import Fore
from ServerFunctions import check_server, get_channel_info, add_channel, remove_channel, get_settings, swap_settings, \
    get_youtube_settings, get_youtube_info, youtube_login, youtube_logout, test_upload, youtube_fully_login, \
    youtube_fully_logout, listRecordings, playbackRecording, downloadRecording

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
        ok, channel_info = get_channel_info(serverIP, serverPort)
        if not ok:
            stopped("Error Response from Server: " + channel_info)
        Screen = "Main"
        while True:
            if Screen is "Main":
                loopNumber = 1
                clearScreen()
                print("")
                if len(channel_info['channels']) is 0:
                    print(Fore.LIGHTMAGENTA_EX + "No Channels currently added in the list.")
                else:
                    print(Fore.LIGHTMAGENTA_EX + "List of Channels:")
                    print("")
                    for channel_id in channel_info['channels']:
                        channelInfo = channel_info['channel'][channel_id]
                        channel_name = channelInfo.get('name')
                        is_alive = channelInfo['is_alive']

                        message = ["    {0}{1}: {2}{3}".format(Fore.LIGHTCYAN_EX, str(loopNumber),
                                                               Fore.WHITE,
                                                               channel_name if channel_name is not None else channel_id)]
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
                            if live is None:
                                message.append("{0} [INTERNET OFFLINE]".format(Fore.LIGHTBLUE_EX))
                            elif live is True:
                                message.append("{0} [LIVE]".format(Fore.LIGHTRED_EX))
                                message.append("{0} Status: {1}".format(Fore.LIGHTRED_EX,
                                                                        recording_status if recording_status is not None
                                                                        else 'UNKNOWN.'))
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
                        # USING JOIN INSTEAD OF += ON STRING BECAUSE JOIN IS FASTER.
                        print(''.join(message))
                        loopNumber += 1
                print("")
                print(" 1) Refresh Channel List.")
                print(" 2) Add Channel")
                print(" 3) Remove Channel")
                print(" 4) Change Settings")
                if 'YoutubeLogin' in channel_info and channel_info['YoutubeLogin'] is False:
                    print(" 5) " + Fore.LIGHTRED_EX + "Login to Youtube (FOR SPONSOR ONLY STREAMS) [VERY BUGGY] "
                                                      "")
                else:
                    print(" 5) " + Fore.LIGHTRED_EX + "Logout of Youtube.")
                print(" 6) {0}View Recordings.".format(Fore.LIGHTYELLOW_EX))
                if toaster is not None and 'localhost' not in serverIP:
                    print(" N) Holds console, shows Windows 10 Toast Notification every time a stream goes live.")
                print("  - Type a specific number to do the specific action. - ")
                option = input(":")
                if option is "1":  # Just Refresh
                    info("Getting Server Info.")
                    ok, reply = get_channel_info(serverIP, serverPort)
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        print("")
                        input("Press enter to go back to Selection.")
                    else:
                        channel_info = reply
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
                    ok, reply = get_channel_info(serverIP, serverPort)
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        print("")
                        input("Press enter to go back to Selection.")
                    else:
                        channel_info = reply
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
                    ok, reply = get_channel_info(serverIP, serverPort)
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        print("")
                        input("Press enter to go back to Selection.")
                    else:
                        channel_info = reply
                elif option is "4":
                    Screen = "Settings"
                elif option is "N":  # WINDOWS 10 TOAST Notification HOLD
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
                        ok, reply = get_channel_info(serverIP, serverPort)
                        if not ok:
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                            print("")
                            input("Press enter to go back to Selection.")
                        else:
                            channel_info = reply
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
                        ok, reply = get_channel_info(serverIP, serverPort)
                        if not ok:
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                            print("")
                            input("Press enter to go back to Selection.")
                        else:
                            channel_info = reply
                elif option is "6":
                    Screen = "View-Recording"
            elif Screen is "Settings":
                print("")
                print("1) Upload Settings")
                print("2) Boolean Settings")
                option = input(":")
                if option is "2":
                    info("Getting Settings.")
                    ok, settings = get_settings(serverIP, serverPort)
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + settings)
                        print("")
                        input("Press enter to go back to Selection.")
                    elif settings == 404:
                        warning("It seems this server doesn't support getQuickSettings.")
                        sleep(2.5)
                    else:
                        Screen = "BooleanSettings"
                if option is "1":
                    info("Getting Settings.")
                    ok, settings = get_youtube_settings(serverIP, serverPort)
                    ok2, info = get_youtube_info(serverIP, serverPort)
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + settings)
                        print("")
                        input("Press enter to go back to Selection.")
                    elif not ok2:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + info)
                        print("")
                        input("Press enter to go back to Selection.")
                    elif settings == 404 or info == 404:
                        warning("It seems this server doesn't support UploadSettings.")
                        sleep(2.5)
                    else:
                        Screen = "UploadSettings"
            elif Screen is "BooleanSettings":
                clearScreen()
                print("")
                print("")
                print(Fore.LIGHTGREEN_EX + "List of Settings:")
                setting_array = []
                loopNumber = 1
                for setting in settings['settings']:
                    print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + setting +
                          Fore.LIGHTRED_EX + ": " + str(settings['settings'][setting]) + Fore.LIGHTYELLOW_EX +
                          " [SWITCH BOOLEAN]")
                    setting_array.append(setting)
                    loopNumber += 1
                print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.LIGHTRED_EX + "EXIT" +
                      Fore.LIGHTRED_EX + ": " + " " + Fore.LIGHTYELLOW_EX + " [EXITS TO THE MAIN MENU]")
                exit_number = len(setting_array) + 1
                print("")
                print(Fore.LIGHTBLUE_EX + "  Type a setting number to do the specific action provided.")
                option = input(":")
                is_number = True
                try:
                    int(option)
                except ValueError:
                    print(Fore.LIGHTRED_EX + "That is not a number!")
                    is_number = False
                    sleep(3.5)
                if is_number:
                    option = int(option)
                    if option == exit_number:
                        Screen = "Main"
                    else:
                        is_good_index = True
                        try:
                            setting = setting_array[option - 1]
                        except IndexError:
                            print(Fore.LIGHTRED_EX + "Sorry, that number is out of range of the numbers listed!")
                            sleep(3.5)
                            is_good_index = False
                        if is_good_index:
                            ok, reply = swap_settings(serverIP, serverPort, setting)
                            print("")
                            print("")
                            if not ok:
                                print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                                sleep(3.5)
                            if reply == 404:
                                print(Fore.LIGHTRED_EX + "Sorry, the Server, doesn't support that type of setting"
                                                         " to be changed!")
                                sleep(3.5)
                            else:
                                info("Getting Settings.")
                                ok, settings = get_settings(serverIP, serverPort)
                                if not ok:
                                    print(Fore.LIGHTRED_EX + "Error Response from Server: " + settings)
                                    print("")
                                    input("Press enter to go back to Selection.")
            elif Screen is "UploadSettings":
                clearScreen()
                print("")
                print(Fore.LIGHTMAGENTA_EX + "List of Settings:")

                print("")

                if info['info']['YoutubeAccountLogin-in']:
                    print("    " + Fore.LIGHTCYAN_EX + str(1) + ": " + Fore.WHITE + "YoutubeAccount USING YOUTUBE API" +
                          Fore.LIGHTRED_EX + ": " + str(info['info']['YoutubeAccountLogin-in'])
                          + Fore.LIGHTYELLOW_EX + " [SIGN OUT (" + info['info']['YoutubeAccountName'] + ")]")
                else:
                    if settings['settings']['UploadLiveStreams']:
                        print("    " + Fore.LIGHTCYAN_EX + str(1) + ": " + Fore.WHITE + "YoutubeAccount" +
                              Fore.LIGHTRED_EX + ": " + str(info['info']['YoutubeAccountLogin-in'])
                              + Fore.LIGHTYELLOW_EX + " [LOGIN-IN] " + Fore.LIGHTRED_EX +
                              "[NEEDED FOR UploadLiveStreams TO WORK]")
                    else:
                        print("    " + Fore.LIGHTCYAN_EX + str(1) + ": " + Fore.WHITE + "YoutubeAccount" +
                              Fore.LIGHTRED_EX + ": " + str(info['info']['YoutubeAccountLogin-in'])
                              + Fore.LIGHTYELLOW_EX + " [LOGIN-IN] " + Fore.LIGHTRED_EX +
                              "[UploadLiveStreams NEEDS TO BE ENABLED FOR THIS TO WORK]")
                print("")
                if info['info']['YoutubeAccountLogin-in']:
                    print("    " + Fore.LIGHTCYAN_EX + str(2) + ": " + Fore.WHITE + "TestUpload" +
                          Fore.LIGHTRED_EX + ": " + ""
                          + Fore.LIGHTYELLOW_EX + "[RECORDS A CHANNEL FOR A FEW SECONDS]")
                else:
                    print("    " + Fore.LIGHTCYAN_EX + str(2) + ": " + Fore.WHITE + "TestUpload" +
                          Fore.LIGHTRED_EX + ": " + ""
                          + Fore.LIGHTRED_EX + "[DISABLED. NEED YOUTUBE ACCOUNT LOGIN-IN]")
                loopNumber = 3
                for setting in settings['settings']:
                    print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.WHITE + setting +
                          Fore.LIGHTRED_EX + ": " + str(settings['settings'][setting]) + Fore.LIGHTYELLOW_EX +
                          " [SWITCH BOOLEAN]")
                    loopNumber += 1

                print("    " + Fore.LIGHTCYAN_EX + str(loopNumber) + ": " + Fore.LIGHTRED_EX + "EXIT" +
                      Fore.LIGHTRED_EX + ": " + " " + Fore.LIGHTYELLOW_EX + " [EXITS TO THE MAIN MENU]")
                print("")
                print(Fore.LIGHTBLUE_EX + "    Type a setting number to do the specific action provided.")
                option = input(":")
                is_number = True
                try:
                    int(option)
                except ValueError:
                    print(Fore.LIGHTRED_EX + "That is not a number!")
                    is_number = False
                    sleep(3.5)
                if is_number:
                    option = int(option)
                    if option == 1:
                        if not info['info']['YoutubeAccountLogin-in']:
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
                        ok, settings = get_youtube_settings(serverIP, serverPort)
                        ok2, info = get_youtube_info(serverIP, serverPort)
                        if not ok:
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + settings)
                            print("")
                            input("Press enter to go back to Selection.")
                        elif not ok2:
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + info)
                            print("")
                            input("Press enter to go back to Selection.")
                    if option == 2:
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
                        ok, settings = get_youtube_settings(serverIP, serverPort)
                        ok2, info = get_youtube_info(serverIP, serverPort)
                        if not ok:
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + settings)
                            print("")
                            input("Press enter to go back to Selection.")
                        elif not ok2:
                            print(Fore.LIGHTRED_EX + "Error Response from Server: " + info)
                            print("")
                            input("Press enter to go back to Selection.")
                    if option > 2:
                        sn = len(settings['settings']) + 2
                        if sn + 1 == option:
                            # Refresh
                            ok, reply = get_channel_info(serverIP, serverPort)
                            if not ok:
                                print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                                print("")
                                input("Press enter to go back to Selection.")
                            else:
                                channel_info = reply
                                Screen = "Main"
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
                    ok, reply = get_channel_info(serverIP, serverPort)
                    if not ok:
                        print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                        print("")
                        input("Press enter to go back to Selection.")
                    else:
                        channel_info = reply
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
                                                    "    {0}DOWNLOADED FRAMES: {1}".format(Fore.LIGHTMAGENTA_EX, frames
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
                ok, reply = get_channel_info(serverIP, serverPort)
                if not ok:
                    print(Fore.LIGHTRED_EX + "Error Response from Server: " + reply)
                    print("")
                else:
                    channel_info = reply
                for channel in channel_info['channels']:
                    channelInfo = channel_info['channel'][channel]
                    channelInfo_last = channel_info_last['channel'][channel]
                    if channelInfo['live'] is True and channelInfo_last['live'] is not True:
                        show_windows_toast_notification("Live Recording Notifications",
                                                        channelInfo['name'] + " is live and is now "
                                                                              "being recorded.")
                sleep(5)
