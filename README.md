# YoutubeLiveChannelRecorder
  Records Youtube Livestreams for a certain channel until removed!
  
## NOTE
  This is a server program. You will need to use the client in order to
  control this program.
  
  ALSO BOTH SERVER AND CLIENT ONLY WORKS ON PYTHON 3.

## INSTALL SERVER
  To use the server-side, you need the required packages:
  ```
  colorama: Used for color.
  google-api-python-client: Used for youtube API.
  oauth2client: Used for youtube API. (May be installed with "google-api-python-client")
  httplib2: Used for youtube API. (May be installed with "google-api-python-client")
  PyYAML: data handling.
  flask: Web Server.
  gevent: Web Server.
  ```
  
  Download Files [[MASTER]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/archive/master.zip)
  [[RELEASES]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/releases)
  
  Download FFMPEG: [[WINDOWS/macOS]](https://ffmpeg.zeranoe.com/builds/) [[LINUX]](https://ffmpeg.org/download.html#build-linux)
  
  Add FFMPEG to path. How to: [[WINDOWS]](https://windowsloop.com/install-ffmpeg-windows-10/)
  
  Extract Server files.
  
  run __main__.py in the server files folder with argument -p <port_name> to specify port name.

## INSTALL CLIENT
  To use the client, you need the required packages:
  ```
  colorama: Used for color.
  ```
  
  Download Files [[MASTER]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/archive/master.zip)
  [[RELEASES]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/releases)
  
  Extract Client files.
  
  run channelarchiver_client.py in the client files folder. The client will then ask for ip and port.

## CREDITS
  
  Thanks to people with [youtube-dl!](https://https://github.com/ytdl-org/youtube-dl/)
  Youtube-dl helped me get a head start!
 
