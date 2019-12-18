import io
from os import getcwd, mkdir
from os.path import exists, join

import yaml

from Code.log import info


class CacheDataHandler:
    yml_name = "data.yml"
    _cache = None
    defaults = {
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
        }
    }

    def loadDataFile(self):
        data_folder = join(getcwd(), "Data")
        if not exists(data_folder):
            mkdir(data_folder)
        if not exists(join(data_folder, self.yml_name)):
            with io.open(join(data_folder, self.yml_name), 'w', encoding='utf8') as outfile:
                outfile.write(yaml.dump(self.defaults))
            info("Created Data.yml (Holds information like list of channels to check if live and record)")
            self._cache = self.defaults
        else:
            with open(join(data_folder, self.yml_name), 'r', encoding='utf8') as stream:
                self._cache = yaml.load(stream, Loader=yaml.FullLoader)

    def saveData(self):
        data_folder = join(getcwd(), "Data")
        with io.open(join(data_folder, self.yml_name), 'w', encoding='utf8') as outfile:
            outfile.write(yaml.dump(self._cache))

    def __init__(self):
        self.loadDataFile()

    def updateCache(self):
        self.loadDataFile()

    def updateValue(self, key_name, value):
        self._cache.update({
            key_name: value,
        })
        self.saveData()

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
        self.saveData()

    def removeValueList(self, key_name, value):
        if value in self._cache.get(key_name):
            self._cache.get(key_name).remove(value)
            self.saveData()

    def setValue(self, key_name, value):
        self._cache.update({
            key_name: value
        })
        self.saveData()

    def deleteKey(self, key_name):
        del self._cache[key_name]
        self.saveData()

    def getDict(self):
        return self._cache
