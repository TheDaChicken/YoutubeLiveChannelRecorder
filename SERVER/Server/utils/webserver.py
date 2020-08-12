import time
from datetime import datetime
from threading import RLock
from typing import Any
from uuid import uuid4, uuid1

from expiringdict import ExpiringDict

try:
    from geventwebsocket.websocket import WebSocket
except ImportError:
    class WebSocket:
        pass

from Server.channels.common import Channel
from Server.channels.youtube import YouTubeVideoInformation
from Server.utils.parser import json

from flask import make_response, request, Response


def json_dump(data: dict) -> str:
    dumped = json.dumps(data, indent=2)
    return dumped


def make_json_response(data, code=None, headers=None) -> Response:
    content_type = 'application/json; charset=utf-8'
    dumped = json_dump(data)
    if headers:
        headers.update({'Content-Type': content_type})
    else:
        headers = {'Content-Type': content_type}
    response = make_response(dumped, code, headers)
    return response


def get_ws_object() -> WebSocket:
    if request.environ.get('wsgi.websocket'):
        ws = request.environ['wsgi.websocket']
        return ws


class Session:
    def __init__(self, obj: Any, obj_name: str):
        self.created_time = datetime.utcnow()
        self.session_uuid = uuid1()
        self.object = obj
        self.obj_name = obj_name

    def __str__(self):
        return str(self.session_uuid)


class SessionHandler:
    def __init__(self):
        self.sessions = ExpiringDict(max_len=100, max_age_seconds=60)

    def create_session(self, channel_object: Channel, obj_name: str) -> Session:
        s = Session(channel_object, obj_name)
        string_uuid = str(s)
        self.sessions.__setitem__(string_uuid, s, set_time=s.created_time.timestamp())
        return s

    def get_session_from_obj_name(self, obj_name) -> Session or None:
        iter = list(filter(
            lambda x: self.sessions.get(x) is not None and self.sessions.get(x).obj_name == obj_name, self.sessions))
        if len(iter) == 0:
            return None
        self.sessions.items_with_timestamp()
        return self.sessions.get(iter[0])

    def get_session(self, uuid: str) -> Session:
        return self.sessions.get(uuid)

    def remove_session(self, uuid: str):
        del self.sessions[uuid]


def create_channel_item(channel: Channel, include=None) -> dict:
    include_list = ["brief"]  # default
    if isinstance(include, str):
        include_list = include.split(",")

    information = channel.get_information()
    data = {
        "type": "channel#%s" % information.get_platform().lower(),
        "platform": information.get_platform(),
    }
    brief = {"channelDetails": {
        "channelIdentifier": information.get_channel_identifier(),
        "channelName": information.get_channel_name(),
        "channelImage": information.get_channel_image(),
    }, "liveInt": information.get_video_information().get_live_status()}

    extra = {}

    video_info = information.get_video_information()
    if isinstance(video_info, YouTubeVideoInformation):
        live_scheduled_timestamp = 0
        if video_info.get_lived_scheduled_time():
            live_scheduled_timestamp = video_info.get_lived_scheduled_time().timestamp()
        brief["liveScheduled"] = {
            "enabled": video_info.is_scheduled(),
            "startTime": live_scheduled_timestamp,
        }
        brief["livePrivate"] = video_info.get_private_stream()
        last_heartbeat_timestamp = 0
        if video_info.get_last_heartbeat():
            last_heartbeat_timestamp = video_info.get_last_heartbeat().timestamp()
        extra["lastHeartbeat"] = last_heartbeat_timestamp

    if "brief" in include_list:
        data["brief"] = brief
    if "extra" in include_list:
        data["extra"] = extra
    return data


def create_search_channel_item(info: dict, include=None):
    include_list = ["brief"]  # default
    if isinstance(include, str):
        include_list = include.split(",")
    data = {
        "type": "channel_search#%s" % info.get("platform").lower(),
        "platform": info.get("platform"),
    }

    brief = {
        "channelDetails": {
            "channelIdentifier": info.get("channel_identifier"),
            "channelName": info.get("channel_name"),
            "channelImage": info.get("channel_image"),
            "followerCount": info.get("follower_count"),
        }
    }

    if "brief" in include_list:
        data["brief"] = brief

    return data
