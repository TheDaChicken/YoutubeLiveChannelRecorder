import datetime

from flask import request
from werkzeug.exceptions import BadRequest, InternalServerError

from Server.core import ProcessHandler
from Server.utils.other import try_get
from Server.utils.webserver import make_json_response, create_channel_item, create_search_channel_item
from Server.webserver.app import app
from Server.webserver.exceptions import NotModified


@app.route("/")
def index(process_handler: ProcessHandler):
    date_obj = process_handler.get_server_uptime()
    return make_json_response({
        "data": [
            {
                "type": "server#status",
                "status": "OK",
                "uptime": date_obj.timestamp(),
            }
        ]
    })


@app.route("/platforms/list")
def platform_list(process_handler: ProcessHandler):
    """ Lists platforms
    Has a bit of cache.
    """

    def platform_item(platform_name: str):
        return {
            "type": "server#platform",
            "name": platform_name
        }

    response = make_json_response(
        {"data": list(map(platform_item, process_handler.platforms))})
    response.cache_control.private = True
    response.cache_control.max_age = 1200
    response.expires = datetime.datetime.utcnow() + datetime.timedelta(1)
    response.add_etag()
    etag = response.get_etag()[0].strip()
    if request.if_none_match and request.if_none_match.contains(etag):
        raise NotModified()
    return response


@app.route("/channels/grab", methods=["POST"])
def channel_info(process_handler: ProcessHandler):
    """ Used to grab information to check the status before adding.
    """
    post = request.get_json()
    platform_name = try_get(post, lambda x: x['platform'], str)  # type: str
    if platform_name is None:
        raise BadRequest(description="No platform specified.")
    elif platform_name.upper() not in process_handler.platforms:
        raise BadRequest(description='%s is an invalid platform.' % platform_name)
    channel_identifier = try_get(post, lambda x: x['channel_identifier'], str)  # type: str
    if channel_identifier is None:
        raise BadRequest(description="POST data is invalid.")
    if channel_identifier in process_handler.channels_dict:
        raise BadRequest(description="Channel given is already in the list of channels!")
    session_obj = process_handler.sessions.get_session_from_obj_name(channel_identifier)
    if session_obj is None:  # Create new Session
        channel = process_handler.create_safe_class(channel_identifier, platform=platform_name)
        result, message = channel.load_channel_data()
        if not result:
            raise InternalServerError(description=message)
        session_obj = process_handler.sessions.create_session(channel, channel_identifier)
    else:
        channel = session_obj.object
    session = {  # Session for adding channels without getting information again
        "id": str(session_obj),
        "createdTime": session_obj.created_time.timestamp(),
    }
    data = create_channel_item(channel)

    response = make_json_response(
        {"data": [data], "session": [session]}
    )
    response.last_modified = session_obj.created_time
    response.expires = session_obj.created_time + datetime.timedelta(seconds=60)
    return response


@app.route("/channels/list", methods=["GET"])
def get_channels(process_handler: ProcessHandler):
    def channel_item(arg):
        return create_channel_item(arg, include)

    args = request.args  # type: dict
    include = args.get("include")

    channels = list(map(channel_item, process_handler.get_channels()))
    response = make_json_response({"data": channels})
    response.add_etag()
    etag = response.get_etag()[0].strip()
    if request.if_none_match and request.if_none_match.contains(etag):
        raise NotModified()
    return response


@app.route("/channels/add", methods=["POST"])
def add_channel(process_handler: ProcessHandler):
    post = request.get_json()
    platform_name = try_get(post, lambda x: x['platform'], str)  # type: str
    if platform_name is None:
        raise BadRequest(description="No platform specified.")
    elif platform_name.upper() not in process_handler.platforms:
        raise BadRequest(description='%s is an invalid platform.' % platform_name)
    channel_identifier = try_get(post, lambda x: x['channel_identifier'], str)  # type: str
    session_id = try_get(post, lambda x: x['session_id'], str)  # type: str
    if not (session_id or channel_identifier):
        raise BadRequest(description="POST data is invalid.")
    if session_id:
        session_obj = process_handler.sessions.get_session(session_id)
        if session_obj is None:
            raise BadRequest(description="Invalid session.")

    return "no"


@app.route("/channels/search", methods=["POST"])
def search_channel(process_handler: ProcessHandler):
    def channel_search_item(arg):
        return create_search_channel_item(arg)

    post = request.get_json()
    platform_name = try_get(post, lambda x: x['platform'], str)  # type: str
    if platform_name is None:
        raise BadRequest(description="No platform specified.")
    elif platform_name.upper() not in process_handler.platforms:
        raise BadRequest(description='%s is an invalid platform.' % platform_name)
    query = try_get(post, lambda x: x['query'], str)  # type: str
    if query is None:
        raise BadRequest(description="No query specified in request.")
    if query == '':
        raise BadRequest(description="Query is empty.")
    result, message = process_handler.search_channel(query, platform_name)
    if result is False:
        raise InternalServerError(description=message)
    if isinstance(message, list):
        channels = list(map(channel_search_item, message))
        response = make_json_response({"data": channels})
        return response
    raise InternalServerError(description="search_channel didn't return list!")
