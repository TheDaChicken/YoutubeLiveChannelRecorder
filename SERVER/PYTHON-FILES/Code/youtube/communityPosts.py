import re

from ..utils.web import download_website
from ..utils.youtube import get_yt_initial_data, get_yt_player_config
from ..utils.other import try_get
from ..log import warning


def getCommunityTabInfo(tabList):
    """

    Gets Community Tab information from a list of all the Youtube Channel Tabs.
    For Example, Youtube Channel featured tab.

    :type tabList: list
    """
    for tab in tabList:
        tab = try_get(tab, lambda x: x['tabRenderer'], dict)
        if tab:
            title = try_get(tab, lambda x: x['title'], str)
            if title is not None and 'Community' in title:
                return tab
    return None


def getCommunityTabMessages(communityTabSectionRenderer):
    """

    Simplifies a list of all Community Tab Messages information to a simple list.

    :type communityTabSectionRenderer: list
    """

    def getMessage(communityTabMessageInfo):
        """

        Get full string message from backstagePostRenderer (Message Holder for community Messages).

        :type communityTabMessageInfo: dict
        """

        communityMessage = ""

        textHolder = try_get(communityTabMessageInfo, lambda x: x['contentText'], dict)
        if textHolder:
            if 'simpleText' in textHolder:
                communityMessage += try_get(textHolder, lambda x: x['simpleText'], str)
            else:
                textListHolder = try_get(textHolder, lambda x: x['runs'], list)
                if textListHolder:
                    for textHolder in textListHolder:
                        if 'navigationEndpoint' in textHolder:
                            # Due to Youtube simplifying URLS. This is used to grab all of the url.
                            fullUrl = try_get(textHolder, lambda x: x['navigationEndpoint'][
                                'urlEndpoint']['url'], str)
                            if fullUrl:
                                communityMessage += fullUrl
                        else:
                            partMessage = try_get(textHolder, lambda x: x['text'], str)
                            if partMessage:
                                communityMessage += partMessage
        return None if communityMessage == "" else communityMessage

    messages = []

    for communityMessageInfo in communityTabSectionRenderer:
        communityMessageInfo = try_get(communityMessageInfo, lambda x: x['backstagePostThreadRenderer'][
            'post']['backstagePostRenderer'], dict)
        if communityMessageInfo:
            message = {
                'postID': try_get(communityMessageInfo, lambda x: x['postId'], str),
                'authorText': try_get(communityMessageInfo, lambda x: x['authorText']['simpleText'], str),
                'contentText': getMessage(communityMessageInfo),
            }
            if message['contentText'] is not None:
                messages.append(message)

    return None if len(messages) == 0 else messages


def readCommunityPosts(channel_class):
    """

    Checks for unlisted youtube live stream links in sponsor only community tab.

    :type channel_class: ChannelInfo
    """

    def isValidYoutubeLiveStream(video_url):
        video_website = download_website(url)
        if video_url is None:
            warning("Internet Offline. :/")
            return None
        elif video_url is 404:
            warning("Found a video id or something but it returned a 404. What?")
            return False
        elif type(url) is str:
            yt_player_config = get_yt_player_config(video_website)
            if 'args' in yt_player_config:
                if "live_playback" in yt_player_config['args']:
                    return True
                return False
            warning("Found Youtube Player Config but it didn't contain anything needed "
                    "to check if it's a valid Youtube Live Stream.")
            return False

    headers = {"DNT": 1, "upgrade-insecure-requests": 1}
    url = 'https://www.youtube.com/channel/' + channel_class.channel_id + '/community'
    website = download_website(
        url,
        headers=headers)
    if type(website) is bool or website is None:
        return None

    youtubeInitialData = get_yt_initial_data(website)
    if youtubeInitialData is None:
        return None
    twoColumnBrowseResultsRenderer = try_get(youtubeInitialData, lambda x: x['contents'][
        'twoColumnBrowseResultsRenderer'], dict)
    tabs = try_get(twoColumnBrowseResultsRenderer, lambda x: x['tabs'], list)
    communityTab = getCommunityTabInfo(tabs)
    itemSectionRenderer = try_get(communityTab, lambda x: x['content']['sectionListRenderer']['contents'][
        0]['itemSectionRenderer']['contents'], list)
    communityTabMessages = getCommunityTabMessages(itemSectionRenderer)
    for communityTabMessage in communityTabMessages:
        message = communityTabMessage['contentText']
        # FIND ANY VIDEO ID IN MESSAGE
        video_id_array = re.findall(r'youtube.com\/watch\?v=(.+)|youtu.be\/(.+)', message)
        if video_id_array is None or len(video_id_array) == 0:
            return False
        else:
            boolean = isValidYoutubeLiveStream('https://youtube.com/watch?v=' + video_id_array[0])
            if boolean:
                channel_class.video_id = video_id_array[0]
                return True
            return False
