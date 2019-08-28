import re

from ..utils.other import try_get
from ..utils.web import download_website

# HOLDS GLOBAL TWITCH VARIABLES.

# TWITCH YOUTUBE VARIABLES
client_id = None


def find_client_id(website_string, url_referer):
    def parse_numbered_list(string_numbered_list):
        def stringToNumber(string):
            try:
                return int(string)
            except ValueError:
                return None

        if '{' in string_numbered_list:
            string_numbered_list = try_get(re.findall(r'{(.+)\}', string_numbered_list), lambda x: x[0], str)
            if string_numbered_list:
                # CHECK IF FULLY ABLE TO PARSE OR SOMETHING.
                if ':' in string_numbered_list:
                    # CREATE DICT
                    dict_ = {}
                    for number_, side in re.findall(r'(.+?):\"(.+?)\",', string_numbered_list):
                        # CHECK IF SIDE IS NUMBER.
                        temp_ = stringToNumber(number_)
                        if temp_:
                            dict_.update({temp_: side})
                    return [True, dict_]
            return [False, "Unable to find \"}\". Unable to parse."]
        return [False, "Unable to find \"{\". Unable to parse."]

    global client_id
    if not client_id:
        assets_list = try_get(re.findall(r'assets[^>]*\((.+)\[r\]\|', website_string), lambda x: x[0], str)  # type: str
        if not assets_list:
            return [False, "Unable to get assets list."]
        okay, assets_list = parse_numbered_list(assets_list)
        if not okay:
            return [False, assets_list]
        # CHECK ASSETS LIST FOR twitch-player-ui
        asset_number = None
        for number in assets_list:
            asset_name = assets_list[number]
            if 'twitch-player-ui' in asset_name:
                asset_number = number
        if not asset_number:
            return [False, "Unable to find twitch player ui in assets list."]
        asset_identifier_list = try_get(re.findall(r'\)\+\"-\"\+(.+?)\[r\]\+', website_string), lambda x: x[1], str)
        okay, asset_identifier_list = parse_numbered_list(asset_identifier_list)
        if not okay:
            return [False, asset_identifier_list]
        asset_identifier = None
        for number in asset_identifier_list:
            if number == asset_number:
                asset_identifier = asset_identifier_list[number]
        if not asset_identifier:
            return [False,
                    "Unable to find number corresponding with twitch player ui"
                    " from assets list in asset identifier list."]
        # GET CLIENT ID.
        website_string = download_website('https://static.twitchcdn.net/assets/twitch-player-ui-{0}.js'.format(
            asset_identifier),
            headers={'DNT': 1, 'Origin': 'https://www.twitch.tv', 'Referer': url_referer, 'Sec-Fetch-Mode': 'cors'})
        if website_string == 404:
            return [False, "Unable to get identifier for getting twitch player ui. -- 404"]
        if website_string:
            client_id = try_get(re.findall(r'\"Client-ID\":\"(.+?)\".', website_string), lambda x: x[0], str)
            if not client_id:
                return [False, "Unable to find client id."]
    return [True, "OK"]
