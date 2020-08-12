import gevent
from injector import inject
from werkzeug.exceptions import MethodNotAllowed

from Server.core import ProcessHandler
from Server.utils.webserver import get_ws_object
from Server.webserver.app import app


@app.route("/websockets/console")
@inject
def console(process_handler: ProcessHandler):
    ws = get_ws_object()
    if not ws:
        raise MethodNotAllowed(description="Incorrect Protocol.")
    process_handler.loggingBackend.load_temp(ws)
    process_handler.loggingBackend.register(ws)
    while not ws.closed:
        # Context switch while `ChatBackend.start` is running in the background.
        gevent.sleep(0.1)
