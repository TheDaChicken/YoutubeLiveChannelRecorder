import re

from ..log import verbose, warning
from ..utils.youtube import get_yt_player_config, get_yt_initial_data
from ..utils.other import try_get

# HOLDS GLOBAL YOUTUBE VARIABLES AND OTHER HEARTBEAT FUNCTIONS


# GLOBAL YOUTUBE VARIABLES
page_build_label = None
page_cl = None
utf_offset = None
variants_checksum = None
account_playback_token = None
client_version = None
client_name = None


def set_global_youtube_variables(html_code=None):
    global account_playback_token
    global page_build_label
    global page_cl
    global variants_checksum
    global client_version
    global utf_offset
    global client_name

    if not account_playback_token and not page_build_label and not page_cl and not variants_checksum and not \
            client_version and not utf_offset and not client_name:
        youtube_player_config = get_yt_player_config(html_code)
        youtube_initial_data = get_yt_initial_data(html_code)
        e_catcher = getServiceSettings(try_get(youtube_initial_data, lambda x: x['responseContext'][
            'serviceTrackingParams'], list), "ECATCHER")

        if not youtube_player_config:
            warning("Unable to find Youtube Player Config. Cannot find all Youtube Variables.")
        else:
            verbose("Getting Playback Token. [GLOBAL YOUTUBE]")
            account_playback_token = try_get(youtube_player_config, lambda x: x['args']['account_playback_token'][:-1], str)
            if account_playback_token is None:
                warning("Something happened when finding the account "
                        "playback Token.")

        if not youtube_initial_data:
            warning("Unable to find Youtube Initial Data. Cannot find all Youtube Variables.")
        elif not e_catcher:
            warning("Unable to find ECATCHER service data in Youtube Initial Data. Cannot find Youtube Variables.")
        else:
            params = try_get(e_catcher, lambda x: x['params'], list)
            page_build_label = getSettingsValue(params, 'innertube.build.label', name="Page Build Label")
            page_cl = getSettingsValue(params, 'innertube.build.changelist', name="Page CL")
            variants_checksum = getSettingsValue(params, 'innertube.build.variants.checksum', name="Variants Checksum")
            client_version = getSettingsValue(params, 'client.version', name="Client Version")
            utf_offset = get_utc_offset()
            client_name = getSettingsValue(params, 'client.name', name="Client Name")


def getServiceSettings(serviceTrackingParamsList, service_nameLook):
    for service in serviceTrackingParamsList:
        service_name = try_get(service, lambda x: x['service'], str)
        if service_name is not None and service_name in service_nameLook:
            return service
    return None


def getSettingsValue(ServiceSettings, settings_nameLook, name=None):
    if name:
        verbose("Getting " + name + ". [GLOBAL YOUTUBE]")
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
    verbose("Getting UTC Offset. [GLOBAL YOUTUBE]")
    # Mostly from https://stackoverflow.com/a/16061385 but as been changed.
    from datetime import datetime
    utc_offset = int((round((datetime.now() - datetime.utcnow()).total_seconds())) / 60)
    return utc_offset
