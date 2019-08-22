import re

from ..utils.web import download_website
from ..utils.other import try_get
from ..log import warning

# HOLDS GLOBAL TWITCH VARIABLES.

# TWITCH YOUTUBE VARIABLES
client_id = None


def find_client_id(website_string, url_referer):
    global client_id
    if not client_id:
        some_identifier = try_get(re.findall(r'111:\"(.+?)\",', website_string), lambda x: x[3], str)
        if not some_identifier:
            return [False, "Unable to get some_identifier."]
        warning(some_identifier)
        # FIND CLIENT ID.
        website_string = download_website('https://static.twitchcdn.net/assets/twitch-player-ui-{0}.js'.format(
            some_identifier),
            headers={'DNT': 1, 'Origin': 'https://www.twitch.tv', 'Referer': url_referer, 'Sec-Fetch-Mode': 'cors'})
        if website_string == 404:
            return [False, "404.. oh my gopodness"]
        if website_string:
            client_id = try_get(re.findall(r'\"Client-ID\":\"(.+?)\".', website_string), lambda x: x[0], str)
            if not client_id:
                return [False, "Unable to find client id."]
    return [True, "OK"]
