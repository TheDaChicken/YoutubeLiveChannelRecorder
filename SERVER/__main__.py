from gevent import monkey
monkey.patch_all()

import argparse
from time import sleep

from Server.core import ProcessHandler
from Server import logger
from Server.webserver import run_server, is_websocket_supported

if __name__ == '__main__':
    # Argument Parser
    parser = argparse.ArgumentParser(
        description='Downloads Live streams when Youtube channels are live!')
    parser.add_argument('-p', '--port', type=int, help='Port number',
                        required=False, nargs='+', default=31311)
    parser.add_argument('-d', '--enable-debug', action='store_true')
    parser.add_argument('-e', '--enable-encoding-logs', action='store_true', help="Prints Encoder Logs.")
    parser_args = parser.parse_args()

    processHandler = ProcessHandler()
    if parser_args.enable_encoding_logs:
        # SET Default log level
        processHandler.set_log_level(logger.ENCODER)
    if is_websocket_supported():
        processHandler.initialize_back_logger()  # initialize logger to websocket
    processHandler.initialize_logger_listener()
    processHandler.initialize_logger()  # initialize logger in this current thread.
    processHandler.load_channels()
    # result, message = processHandler.run_channel("UCF3KMM3QLVEfnFPI8AbLUJA")
    # processHandler.run_channel('UCbyS9AQt6KE0XUuGqXya90A')
    # a = processHandler.create_proxy_dict({"channel_identifier": "UC-SK9mJ7TCw_zjdi5AQJoEQ"})
    # a.load_channel_data()
    run_server(processHandler, 31311)
    while True:
        sleep(100)
