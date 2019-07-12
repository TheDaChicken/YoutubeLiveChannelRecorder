import re
from random import randint

from ..log import verbose, warning
from ..utils.youtube import get_yt_player_config, get_yt_initial_data
from ..utils.other import try_get, getTimeZone

# HOLDS GLOBAL YOUTUBE VARIABLES AND OTHER HEARTBEAT FUNCTIONS


# GLOBAL YOUTUBE VARIABLES
page_build_label = None
page_cl = None
utf_offset = None
variants_checksum = None
account_playback_token = None
client_version = None
client_name = None
timezone = None
ps = None
sts = None
cbr = None
client_os = None
client_os_version = None
cpn = None


def set_global_youtube_variables(html_code=None):
    global account_playback_token
    global page_build_label
    global page_cl
    global variants_checksum
    global client_version
    global utf_offset
    global client_name
    global timezone
    global ps
    global sts
    global cbr
    global client_os
    global client_os_version
    global cpn

    if not account_playback_token and not page_build_label and not page_cl and not variants_checksum and not \
            client_version and not utf_offset and not client_name and not ps and not sts and not cbr:
        verbose("Getting Global YouTube Variables.")
        youtube_player_config = get_yt_player_config(html_code)
        youtube_initial_data = get_yt_initial_data(html_code)
        e_catcher = getServiceSettings(try_get(youtube_initial_data, lambda x: x['responseContext'][
            'serviceTrackingParams'], list), "ECATCHER")

        if not youtube_player_config:
            warning("Unable to get Youtube Player Config. Cannot find all Youtube Variables.")
        else:
            account_playback_token = try_get(youtube_player_config, lambda x: x['args']['account_playback_token'][:-1],
                                             str)
            ps = try_get(youtube_player_config, lambda x: x['args']['ps'], str)
            sts = try_get(youtube_player_config, lambda x: x['sts'], int)
            cbr = try_get(youtube_player_config, lambda x: x['args']['cbr'])
            client_os = try_get(youtube_player_config, lambda x: x['args']['cos'])
            client_os_version = try_get(youtube_player_config, lambda x: x['args']['cosver'])
            if account_playback_token is None:
                warning("Unable to find account playback token in the YouTube player config.")
            if ps is None:
                warning("Unable to find ps in the YouTube player config.")
            if sts is None:
                warning("Unable to find sts in the YouTube player config.")
            if cbr is None:
                warning("Unable to find cbr in the YouTube player config.")
            if client_os is None:
                warning("Unable to find Client OS in the YouTube player config.")
            if client_os_version is None:
                warning("Unable to find Client OS Version in the YouTube player config.")

        if not youtube_initial_data:
            warning("Unable to get Youtube Initial Data. Cannot find all Youtube Variables.")
        elif not e_catcher:
            warning("Unable to get ECATCHER service data in Youtube Initial Data. Cannot find all Youtube Variables.")
        else:
            params = try_get(e_catcher, lambda x: x['params'], list)
            page_build_label = getSettingsValue(params, 'innertube.build.label', name="Page Build Label")
            page_cl = getSettingsValue(params, 'innertube.build.changelist', name="Page CL")
            variants_checksum = getSettingsValue(params, 'innertube.build.variants.checksum', name="Variants Checksum")
            client_version = getSettingsValue(params, 'client.version', name="Client Version")
            utf_offset = get_utc_offset()
            client_name = getSettingsValue(params, 'client.name', name="Client Name")
            timezone = get_time_zone()


def getServiceSettings(serviceTrackingParamsList, service_nameLook):
    if serviceTrackingParamsList:
        for service in serviceTrackingParamsList:
            service_name = try_get(service, lambda x: x['service'], str)
            if service_name is not None and service_name in service_nameLook:
                return service
    return None


def getSettingsValue(ServiceSettings, settings_nameLook, name=None):
    for service in ServiceSettings:
        service_name = try_get(service, lambda x: x['key'], str)
        if service_name is not None and service_name in settings_nameLook:
            value = try_get(service, lambda x: x['value'], str)
            if name:
                if not value:
                    warning("Something happened when finding the " + name)
                    return None
            return value
    return None


def get_utc_offset():
    # Mostly from https://stackoverflow.com/a/16061385 but as been changed.
    from datetime import datetime
    utc_offset = int((round((datetime.now() - datetime.utcnow()).total_seconds())) / 60)
    return utc_offset


def get_time_zone():
    return getTimeZone()


def generate_cpn():
    """

    Looked at for reference:
    https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1531

    """
    CPN_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
    cpn = ''.join((CPN_ALPHABET[randint(0, 256) & 63] for _ in range(0, 16)))
    return cpn
