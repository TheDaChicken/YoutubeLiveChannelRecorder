# YoutubeLiveChannelRecorder
  Records Youtube Livestreams for a certain channel until removed!
  
## NOTE
  This is a server program. You will need to use the client in order to
  control this program.
  
  ALSO BOTH SERVER AND CLIENT WON'T WORK ON PYTHON VERSION 2.
  
  THIS PROGRAM IS TESTED AND WORKS BEST ON PYTHON VERSION 3.7.2.

## Inspiration
  
  This idea came from when I wanted to record livestreams from [Skeppy](https://www.youtube.com/channel/UCzMjRlKVO9XIqH_crIFpi6w).
  When he ends his livestreams, his deletes the recording. Meaning if I were to miss a livestream or want to watch and look back on it. I can't. Since I was unable to record them fast enough when I got the notification when he was live, I made the program to record it automatically!

## CREDITS
  
  Thanks to people of [youtube-dl!](https://https://github.com/ytdl-org/youtube-dl/)
  Youtube-dl helped me get a head start!

## SETUP SERVER
  To use the server-side, you need the required packages:
  ```
  colorama: Used for color.
  google-api-python-client: Used for youtube API.
  oauth2client: Used for youtube API. (May be installed with "google-api-python-client")
  httplib2: Used for youtube API. (May be installed with "google-api-python-client")
  PyYAML: data handling.
  flask: Web Server.
  gevent: Web Server.
  win10toast: Windows Toast Notifications [ONLY NEEDED IF ON WINDOWS]
  tzlocal: Used to get TimeZone.
  ```
  
  Download Youtube Live Chanenl Recorder [[MASTER]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/archive/master.zip)
  OR [[RELEASES]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/releases)
  
  Download FFMPEG: [[WINDOWS/macOS]](https://ffmpeg.zeranoe.com/builds/) [[LINUX]](https://ffmpeg.org/download.html#build-linux)
  
  Add FFMPEG to path. How to: [[WINDOWS]](https://windowsloop.com/install-ffmpeg-windows-10/)
  
  Extract Server files.
  
  run __main__.py in the server files folder with argument -p <port_name> to specify port.

## SETUP CLIENT
  To use the client, you need the required packages:
  ```
  colorama: Used for color.
  httplib2: Web.
  win10toast: Windows Toast Notifications [ONLY NEEDED IF ON WINDOWS]
  ```
  
  Download Youtube Live Chanenl Recorder [[MASTER]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/archive/master.zip)
  OR [[RELEASES]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/releases)
  
  Extract Client files.
  
  run channelarchiver_client.py in the client files folder. The client will then ask for ip and port.
