import io
import os
from .log import info, warning
import yaml

data_yml_path = os.path.join(os.getcwd(), "Data", "data.yml")
data_yml_dir = os.path.join(os.getcwd(), "Data")


def createDataFile():
    # Default Yaml Settings
    data = {
        'channel_ids': [],
        'DownloadThumbnail': True,
        'recordingHeight': 'original',
        'UploadLiveStreams': False,
        'UploadThumbnail': False,
        'UploadSettings': {
            None: {
                'CategoryID': 20,
                'description': [
                    'This is a automated description uploaded with "channelarchiver".',
                    'Author of Program: TheDaChicken.',
                    'Original Title: %VIDEO_ID%',
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
        return True
    else:
        return False


def loadData():
    if not os.path.isfile(data_yml_path):
        warning("Unable to find data.yml! Should have been created unless being ran remotely.")
        return None
    with open(data_yml_path, 'r') as stream:
        yaml_config = yaml.load(stream, Loader=yaml.FullLoader)
    return yaml_config


def doesDataExist():
    return os.path.isfile(data_yml_path)


def saveData(data):
    with io.open(data_yml_path, 'w', encoding='utf8') as outfile:
        outfile.write(yaml.dump(data))


def save_credentials(credentials):
    yaml_config = loadData()
    yaml_config.update({
        'credentials': credentials
    })
    saveData(yaml_config)


def get_credentials():
    yaml_config = loadData()
    if 'credentials' in yaml_config:
        return yaml_config['credentials']
    return None


def clear_credentials():
    yaml_config = loadData()
    if 'credentials' in yaml_config:
        del yaml_config['credentials']
        del yaml_config['youtube_account_username']
        saveData(yaml_config)
        return True
    return False


def save_username(username):
    yaml_config = loadData()
    yaml_config.update({
        'youtube_account_username': username
    })
    saveData(yaml_config)


def get_username():
    yaml_config = loadData()
    if 'youtube_account_username' in yaml_config:
        return yaml_config['youtube_account_username']
    return None


# This allows quick changing settings without restarting server.
def UploadSettings():
    yaml_config = loadData()
    return yaml_config['UploadSettings']


def UploadThumbnail():
    yaml_config = loadData()
    return yaml_config['UploadThumbnail']


def UploadVideos():
    yaml_config = loadData()
    return yaml_config['UploadLiveStreams']


def DownloadThumbnail():
    yaml_config = loadData()
    return yaml_config['DownloadThumbnail']


def get_upload_settings(channel_name):
    upload_settings = UploadSettings()
    if channel_name in upload_settings:
        return upload_settings[channel_name]
    return upload_settings[None]


def add_channel_config(channel_id):
    data = loadData()
    data['channel_ids'].append(channel_id)
    saveData(data)


def remove_channel_config(channel_id):
    data = loadData()
    data['channel_ids'].remove(channel_id)
    saveData(data)


def get_recordingHeight():
    data = loadData()
    return data['recordingHeight']
