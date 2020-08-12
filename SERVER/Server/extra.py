import io
import logging
from os import mkdir
from typing import Any

import yaml
from flask import Request

from Server.logger import get_logger
from os.path import join, exists

from Server.definitions import DATA_FOLDER, RECORDING_FOLDER
from Server.utils.other import quality_str_int
from Server.utils.path import check_path_creatable
from Server.utils.web import create_session, CustomResponse, UserAgent


class DataHandler:
    file_name = "data.yml"
    defaults = {
        'Saved_Channels': {},
        'DownloadThumbnail': True,
        'RecordingResolution': 'original',
        'UploadLiveStreams': False,
        'UploadThumbnail': False,
        'UploadSettings': {
            None: {  # Default
                'CategoryID': 20,
                'description': [
                    'This is a automated video uploaded with "channelarchiver".',
                    'Author of Program: TheDaChicken.',
                    'Original Title: {TITLE}',
                    'Original Video Link: https://youtu.be/{VIDEO_ID}',
                    '',
                    '',
                    'Original Description:',
                    '',
                    '{DESCRIPTION}'
                ],
                'privacyStatus': 'unlisted',
                'tags': None,
                'title': '{CHANNEL_NAME} {VIDEO_ID} {START_DATE_MONTH}/{START_DATE_DAY}/{START_DATE_YEAR}'
            },
            "Skep": {
                'CategoryID': 20,
                'description': [
                    'This is a automated video uploaded with "channelarchiver".',
                    'Author of Program: TheDaChicken.',
                    'Original Title: {TITLE}',
                    'Original Video Link: https://youtu.be/{VIDEO_ID}',
                    '',
                    '',
                    'Original Description:',
                    '',
                    '{DESCRIPTION}'
                ],
                'privacyStatus': 'unlisted',
                'tags': "skeppy,streams",
                'title': '{CHANNEL_NAME} {VIDEO_ID} {START_DATE_MONTH}/{START_DATE_DAY}/{START_DATE_YEAR}'
            }
        },
        "RecordingSettings": {
            "FileNameFormat":
                "%(CHANNEL_NAME)s - '%(VIDEO_ID)s' - %(DATE_MONTH)s-%(DATE_DAY)s-%(DATE_YEAR)s.%(EXTENSION)s",
            "RecordingPath": RECORDING_FOLDER,
        },
    }

    logging_name = None  # type: str
    _cache = None

    def __init__(self, logging_name=None):
        self.logging_name = logging_name

    @staticmethod
    def check_data_folder():
        """
        Checks if Data Folder Exists and creates it
        """
        if exists(DATA_FOLDER) is False:
            mkdir(DATA_FOLDER)

    def load(self):
        """Loads the config.yml """
        self.check_data_folder()
        full_path = join(DATA_FOLDER, self.file_name)
        if exists(join(DATA_FOLDER, self.file_name)) is False:
            with io.open(full_path, 'w', encoding='utf-8') as outfile:
                outfile.write(yaml.dump(self.defaults))
            get_logger().info("Created Data.yml (Holds information like list of channels to check if live and record)")
            self._cache = self.defaults
        else:
            with open(full_path, 'r', encoding='utf-8') as stream:
                self._cache = yaml.load(stream, Loader=yaml.FullLoader)
        self.__checkValues__()

    def __checkValues__(self):
        """ Checks if Values are valid. """
        quality_name = self._cache.get("RecordingResolution")
        quality_number = quality_str_int(quality_name)
        if quality_number is None:
            get_logger(self.logging_name). \
                warning("Invalid quality \"{0}\". Using best quality instead as a safe-guard.".format(quality_name))
        recording_path = self.get_value("RecordingSettings.RecordingPath")
        if not check_path_creatable(recording_path):
            get_logger(self.logging_name).critical("Recording Path \"{0}\" is not creatable.".format(recording_path))

    def save(self):
        self.check_data_folder()
        full_path = join(DATA_FOLDER, self.file_name)
        with io.open(full_path, 'w', encoding='utf8') as outfile:
            outfile.write(yaml.dump(self._cache))

    def get_cache(self) -> dict:
        return self._cache

    def get_defaults(self) -> dict:
        return self.defaults

    def save_cache(self, _cache):
        self._cache = _cache
        self.save()

    def get_value(self, key: str, obj_=None) -> Any:
        key_list = key.split(".") or [key]
        if obj_:
            obj = obj_[0]
            key = "{0}.{1}".format(obj_[1], key)
        else:
            obj = self._cache
        while len(key_list) != 0:
            try:
                index = key_list.pop(0)
                obj = obj[index]
            except KeyError:
                get_logger(self.logging_name).warning(
                    "Unable to find {0} in data.yml. Using Default value.".format(key))
                return self.get_default_value(key)
        return obj

    def get_default_value(self, key: str) -> Any:
        key_list = key.split(".") or [key]
        obj = self.defaults
        while len(key_list) != 0:
            try:
                index = key_list.pop(0)
                obj = obj[index]
            except KeyError:
                get_logger(self.logging_name).critical("{0} is not in default!".format(key))
                return None
        return obj


class GlobalHandler:
    """Access Same Session etc on all threads
    """

    def __init__(self):
        # initialize_logger("Data Handler")
        self.session = create_session()
        self.data = DataHandler(logging_name="Data Handler")
        self.data.load()
        self.log_level = logging.DEBUG

    def set_log_level(self, log_level):
        self.log_level = log_level

    def get_log_level(self):
        return self.log_level

    def request(self, url, request_method="GET", headers=None, **kwargs) -> CustomResponse:
        if headers is None:
            headers = {}
        if 'User-Agent' not in headers:
            headers["User-Agent"] = UserAgent
        return self.session.request(request_method, url, stream=True, **kwargs)

    def get_cache_yml(self) -> DataHandler:
        return self.data
