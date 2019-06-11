import argparse
from time import sleep
from Code import run_channel, check_internet, enable_debug
from Code.log import stopped, warning, disable_youtube_reply
from Code.serverHandler import run_server
from Code.dataHandler import createDataFile, loadData, doesDataExist

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Downloads Live streams when Youtube channels are live!')

    # noinspection PyTypeChecker
    parser.add_argument('-p', '--port', type=int, help='Port number', required=True, nargs='+', default=None)
    parser.add_argument('-r', '--disable-reply', action='store_true')
    parser.add_argument('-d', '--enable-debug', action='store_true')

    parser_args = parser.parse_args()

    channel_ids = []

    if not doesDataExist():
        createDataFile()

    data = loadData()
    channel_ids.extend(data['channel_ids'])
    del data

    if not check_internet():
        stopped("Not able to access the internet!")

    sleep(.2)

    if parser_args.disable_reply:
        disable_youtube_reply()

    if parser_args.enable_debug:
        enable_debug()

    for channel_id in channel_ids:
        run_channel(channel_id)
        sleep(.41)

    sleep(1)

    run_server(parser_args.port[0])

    if len(channel_ids) is 0:
        warning("None channels found added into this program!")
        warning("Connect to localhost on server port using this program's Client, to add channels!")

    del parser_args

    while True:  # Also needed for control+C to work.
        sleep(1)  # Hai! How about you doing? o_O
