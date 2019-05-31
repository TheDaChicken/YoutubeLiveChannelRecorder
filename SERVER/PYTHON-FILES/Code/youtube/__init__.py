import re

from ..log import verbose, warning
from ..utils.youtube import get_yt_player_config

# HOLDS GLOBAL YOUTUBE VARIABLES AND OTHER HEARTBEAT FUNCTIONS


# GLOBAL YOUTUBE VARIABLES
page_build_label = None
page_cl = None
utf_offset = None
variants_checksum = None
account_playback_token = None
client_version = None


def get_global_youtube_variables(html_code=None):
    global account_playback_token
    global page_build_label
    global page_cl
    global variants_checksum
    global client_version
    global utf_offset
    if account_playback_token is None:
        account_playback_token = get_playback_token(html_code=html_code)
    if page_build_label is None:
        page_build_label = get_page_build_label(html_code=html_code)
    if page_cl is None:
        page_cl = get_page_cl(html_code=html_code)
    if variants_checksum is None:
        variants_checksum = get_variants_checksum(html_code=html_code)
    if utf_offset is None:
        utf_offset = get_utc_offset()
    if client_version is None:
        client_version = get_client_version(html_code=html_code)


def get_playback_token(html_code=None):
    verbose("Getting Playback Token. [GLOBAL YOUTUBE]")
    html_code = str(html_code)
    account_playback_token_array = re.findall(r'"account_playback_token":"(.+?)="', html_code)
    if account_playback_token_array is None or len(account_playback_token_array) is 0:
        warning("Something happened when finding the account "
                "playback Token.")
        return None
    return account_playback_token_array[0]


# GLOBAL HEARTBEAT #
def get_page_build_label(html_code=None):
    verbose("Getting Page Build Label. [GLOBAL YOUTUBE]")
    html_code = str(html_code)
    page_build_label_array = re.findall(r"PAGE_BUILD_LABEL\":" + '"(.+?)",', html_code)
    if page_build_label_array is None or len(page_build_label_array) is 0:
        warning("Something happened when finding the Page Build Label.")
        return None
    return page_build_label_array[0]


def get_page_cl(html_code=None):
    verbose("Getting Page CL. [GLOBAL YOUTUBE]")
    html_code = str(html_code)
    page_cl_array = re.findall(r"PAGE_CL\":(.+?),", html_code)
    if page_cl_array is None or len(page_cl_array) is 0:
        warning("Something happened when finding the Page CL.")
        return None
    return page_cl_array[0]


def get_variants_checksum(html_code=None):
    verbose("Getting Variants Checksum. [GLOBAL YOUTUBE]")
    html_code = str(html_code)
    variants_checksum_array = re.findall("VARIANTS_CHECKSUM\":" + '"(.+?)"', html_code)
    if variants_checksum_array is None or len(variants_checksum_array) is 0:
        warning("Something happened when finding the Variants Checksum.")
        return None
    return variants_checksum_array[0]


def get_utc_offset():
    verbose("Getting UTC Offset. [GLOBAL YOUTUBE]")
    # Mostly from https://stackoverflow.com/a/16061385 but as been changed.
    from datetime import datetime
    utc_offset = int((round((datetime.now() - datetime.utcnow()).total_seconds())) / 60)
    return utc_offset


def get_client_version(html_code):
    verbose("Getting Client Version. [GLOBAL YOUTUBE]")
    html_code = str(html_code)
    client_version_array = re.findall(r'client_version":' + '"(.+?)"', html_code)
    if client_version_array is None or len(client_version_array) is 0:
        warning("Something happened when finding the Client Version.")
        return None
    return client_version_array[0]


def get_c_ver(html_code):
    verbose("Getting CVER. [GLOBAL HEARTBEAT]")
    html_code = str(html_code)
    yt_player = get_yt_player_config(html_code)
    if yt_player is None or 'args' not in yt_player or 'cver' not in yt_player['args']:
        warning("Unable to find the CVER.")
    return yt_player['args']['cver']