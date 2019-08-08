# YoutubeLiveChannelRecorder
  Records Youtube Livestreams for given channels automatically! Technically this program doesn't record, it downloads the stream, but whatever.
  
### NOTE
  This is a server program. You will need to use the client in order to control this program.
  This program is tested on PYTHON VERSION 3.7.2.
  This program does not work anything below PYTHON VERSION 3.

### LIMITATIONS (AS OF RIGHT NOW)
  Resolution/fps changes in stream causes YouTube to buffer waiting for the client (or whatever) to grab a new manifest url. As FFmpeg is an external program, you cannot really easily see if a resolution/fps change has occured, and then grab a new manifest url and start recording again.

### Inspiration
  
  This idea came from when I wanted to record livestreams from [Skeppy](https://www.youtube.com/channel/UCzMjRlKVO9XIqH_crIFpi6w).
  When he ends his livestreams, his deletes the recording. Meaning if I were to miss a livestream or want to watch and look back on it. I can't. Since sometimes I am unable to watch Skeppy's streams he was live, I made the program to record it automatically so I can watch it later! (NOTE SKEPPY LIVE STREAMS MOSTLY ON HIS SECOND CHANNEL, [SKEP](https://www.youtube.com/channel/UCviw1uSMHnTFm9RQvacw6Mw))

### CREDITS
  
  Thanks to people of [youtube-dl!](https://github.com/ytdl-org/youtube-dl/)
  Some code came from youtube-dl.

### EXAMPLE STREAM RECORDINGS (ORIGINAL DELETED) 
  
  https://youtu.be/MQP8aqw7-Ko (SKEP CHANNEL 6/15/19)
  
  https://youtu.be/Ao1ZkJ8XwjE (SKEP CHANNEL 6/22/19)

### SETUP SERVER
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

### SETUP CLIENT
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
