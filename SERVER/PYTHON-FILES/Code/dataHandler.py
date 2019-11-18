import io
import os
from Code.log import info, warning
import yaml

data_yml_path = os.path.join(os.getcwd(), "Data", "data.yml")
data_yml_dir = os.path.join(os.getcwd(), "Data")


class CacheDataHandler:
    """

    Used to cache stuff in data handler

    """
    _cache = None

    def __init__(self):
        setupDataFile()
        self._cache = loadDataFile()

    def updateCache(self):
        self._cache = loadDataFile()

    def updateValue(self, key_name, value):
        self._cache.update({
            key_name: value,
        })
        saveData(self._cache)

    def getValue(self, key_name):
        """

        returns value from key_name

        :type key_name: str
        """
        return self._cache.get(key_name)

    def addValueList(self, key_name, value):
        if key_name not in self._cache:
            self._cache.update({key_name: []})
        self._cache.get(key_name).append(value)
        saveData(self._cache)

    def removeValueList(self, key_name, value):
        if value in self._cache.get(key_name):
            self._cache.get(key_name).remove(value)
            saveData(self._cache)

    def setValue(self, key_name, value):
        self._cache.update({
            key_name: value
        })
        saveData(self._cache)

    def deleteKey(self, key_name):
        del self._cache[key_name]
        saveData(self._cache)

    def getDict(self):
        return self._cache


def setupDataFile():
    # Default Yaml Settings
    if not os.path.isfile(data_yml_path):
        data = {
            'channel_ids': [],
            'DownloadThumbnail': True,
            'recordingResolution': 'original',
            'UploadLiveStreams': False,
            'UploadThumbnail': False,
            'UploadSettings': {
                None: {
                    'CategoryID': 20,
                    'description': [
                        'This is a automated video uploaded with "channelarchiver".',
                        'Author of Program: TheDaChicken.',
                        'Original Title: {TITLE}',
                        'Original Video Link: https://youtu.be/{VIDEO_ID}',
                        'The Original Video Link may be deleted.',
                        'NOTE: When a streamer goes offline, and comes back online, 2 videos will uploaded.',
                        '',
                        '',
                        'Original Description:',
                        '',
                        '{DESCRIPTION}'
                    ],
                    'privacyStatus': 'unlisted',
                    'tags': None,
                    'title': '{CHANNEL_NAME} {VIDEO_ID} {START_DATE_MONTH}/{START_DATE_DAY}/{START_DATE_YEAR}'
                }
            },
        }
        if os.path.exists(data_yml_dir) is False:
            os.mkdir(data_yml_dir)
        if os.path.isfile(data_yml_path) is False:
            with io.open(data_yml_path, 'w', encoding='utf8') as outfile:
                outfile.write(yaml.dump(data))
            info("Created Data.yml (Holds information like list of channels to check if live and record)")


def loadDataFile():
    if not os.path.isfile(data_yml_path):
        warning(
            "Unable to find data.yml! Should have been created unless ran remotely.")
        return None
    with open(data_yml_path, 'r') as stream:
        yaml_config = yaml.load(stream, Loader=yaml.FullLoader)
    return yaml_config


def saveData(data):
    with io.open(data_yml_path, 'w', encoding='utf8') as outfile:
        outfile.write(yaml.dump(data))

