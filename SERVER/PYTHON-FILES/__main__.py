import argparse

from Code import ThreadHandler

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Downloads Live streams when Youtube channels are live!')

    # Argument Parser
    parser.add_argument('-p', '--port', type=int, help='Port number',
                        required=False, nargs='+', default=31311)
    parser.add_argument('-d', '--enable-debug', action='store_true')
    parser_args = parser.parse_args()

    threadHandler = ThreadHandler()
    threadHandler.debug_mode = parser_args.enable_debug
    threadHandler.serverPort = parser_args.port
