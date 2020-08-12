import logging
from flask_injector import FlaskInjector, request
from werkzeug.exceptions import HTTPException

from Server.core import ProcessHandler
from Server.logger import get_logger
from Server.utils.webserver import json_dump
from Server.webserver.app import app, SERVER_NAME
from flask import has_request_context, request
from Server.webserver.custom import web_server, websocket_handler
import Server.webserver.pages
import Server.webserver.websocket

status_code_messages = {
    404: "Unable to find resource.",
    405: "Method not allowed!",
    500: "Internal Server Error"
}


@app.errorhandler(404)
def resource_not_found(error):
    response = error.get_response()
    description = error.description
    response.data = json_dump(
        {'errors': [
            {
                "status": 404,
                "message": description,
            }
        ]}
    )
    response.content_type = "application/json; charset=utf-8"
    return response


@app.errorhandler(HTTPException)
def handle_http_stuff(error: HTTPException):
    status_code = error.code
    description = error.description
    response = error.get_response()
    response.data = json_dump(
        {'errors': [
            {
                "status": status_code,
                "message": description,
            }
        ]}
    )
    response.content_type = "application/json; charset=utf-8"
    return response


def is_websocket_supported():
    return websocket_handler is not None


def run_server(process_handler: ProcessHandler, port: int, host='0.0.0.0'):
    def configure(binder):
        binder.bind(ProcessHandler, to=process_handler, scope=request)

    logger = get_logger('Web Server')
    logger.setLevel(logging.INFO)
    if websocket_handler is not None:
        websocket_handler.logger = property(lambda self: logger)

    modules = [configure]
    # Initialize Flask-Injector.
    FlaskInjector(app=app, modules=modules)
    if web_server:
        geventOpt = {'GATEWAY_INTERFACE': 'CGI/1.1',
                     'SERVER_SOFTWARE': SERVER_NAME,
                     'SCRIPT_NAME': '',
                     'wsgi.version': (1, 0),
                     'wsgi.multithread': True,
                     'wsgi.multiprocess': True,
                     'wsgi.run_once': False}
        http_server = web_server((host, port), app, log=logger, handler_class=websocket_handler, environ=geventOpt)
        process_handler.server_started(port)
        http_server.serve_forever()
    else:
        process_handler.server_started(port)
        app.run(host=host, port=port, threaded=True)
