from flask import Flask

SERVER_NAME = "YoutubeLiveChannelRecorder"


class CustomFlask(Flask):
    def process_response(self, response):
        response.headers['Server'] = SERVER_NAME
        super(CustomFlask, self).process_response(response)
        return response


app = CustomFlask(__name__)

# try:
#     from flask_compress import Compress
#
#     Compress(app)
# except ImportError:
#     Compress = None

# def is_compress_installed():
#     return Compress is not None
