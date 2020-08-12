from datetime import datetime
from typing import Optional

from Server.logger import get_logger

try:
    from gevent.pywsgi import WSGIServer
    from gevent.pywsgi import WSGIHandler


    class web_server(WSGIServer):
        pass

except ImportError:
    get_logger().warning("Get gevent package for a more protected web server.")

    web_server = None
    WSGIHandler = None

try:
    from geventwebsocket.handler import WebSocketHandler


    class websocket_handler(WebSocketHandler):
        def log_request(self):
            if '101' not in str(self.status):
                message = format_request(self)
                self.logger.info(message)

except ImportError:
    get_logger().warning("Get gevent package for websockets.")

    websocket_handler = None


def format_request(wsHandler: WSGIHandler):
    client_address = wsHandler.client_address[0] \
        if isinstance(wsHandler.client_address, tuple) else wsHandler.client_address
    request_method = wsHandler.command
    status_code = (wsHandler._orig_status or wsHandler.status or '000').split()[0]
    path = wsHandler.path
    string = ["%s - %s %s" % (client_address, request_method, path)]
    user_agent = wsHandler.headers.get("User-Agent")
    string.append(" [STATUS CODE %s]" % status_code)
    if user_agent is not None and 'Android' in user_agent:
        string.append(" [ANDROID REQUEST]")

    return "".join(string)
