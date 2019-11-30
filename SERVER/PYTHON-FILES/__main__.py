import argparse
from time import sleep

from Code import ProcessHandler

if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(
            description='Downloads Live streams when Youtube channels are live!')

        # Argument Parser
        parser.add_argument('-p', '--port', type=int, help='Port number',
                            required=False, nargs='+', default=31311)
        parser.add_argument('-d', '--enable-debug', action='store_true')
        parser.add_argument('-e', '--enable-ffmpeg-logs', action='store_true')
        parser_args = parser.parse_args()

        threadHandler = ProcessHandler()
        threadHandler.debug_mode = parser_args.enable_debug
        threadHandler.serverPort = parser_args.port
        threadHandler.enable_ffmpeg_logs = parser_args.enable_ffmpeg_logs
        threadHandler.loadChannels()
        threadHandler.run_youtube_queue()
        threadHandler.run_server()  # holds
    except KeyboardInterrupt:
        pass
