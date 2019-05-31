# YoutubeLiveChannelRecorder
  Records Youtube Livestreams for a certain channel until removed!
  
  NOTE: This is a server program. You can use this program outside hosted area
           
           (if port forward with specific port)
        
        Also, to control this program, you need to use the client.

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
  
  Download Latest Master [[Github]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/archive/master.zip)

  Download Latest Release [[Github]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/releases)
  
  Extract Server files.
  
  run __main__.py in the server files folder with argument -p <port_name> to specify port name.

## INSTALL CLIENT
  To use the client, you need the required packages:
  ```
  colorama: Used for color.
  ```
    
  Download Latest Master [[Github]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/archive/master.zip)
  
  Download Latest Release [[Github]](https://github.com/TheDaChicken/YoutubeLiveChannelRecorder/releases)
  
  Extract Client files.
  
  run channelarchiver_client.py in the client files folder. The client will then ask for ip and port.
