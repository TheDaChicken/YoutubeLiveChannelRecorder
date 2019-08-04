import re

from ..utils.web import download_website, download_m3u8_formats
from ..utils.parser import parse_json
from ..utils.youtube import get_yt_initial_data, get_yt_player_config
from ..utils.other import try_get, get_format_from_data, get_highest_thumbnail
from ..log import warning

already_checked_video_ids = []


def is_live_sponsor_only_streams(channel_class, SharedVariables):
    """

    Checks for unlisted youtube live stream links in sponsor only community tab.
    This is to record "sponsor only" streams. Really, it's just a unlisted stream.

    :type channel_class: ChannelInfo
    """

    def loadVideoData():
        """

        This is used to grab video info from the Youtube site, like video_id, to check if already live,
        and the stream url if already live.
        Everything else would use heartbeat and get video info url.

        :return: Nothing. It edits the class.
        """
        html = download_website('https://www.youtube.com/watch?v=' + video_id)
        if html is None:
            return [False, "Failed getting Video Data from the internet! "
                           "This means there is no good internet available!"]
        if html == 404:
            return [False, "Failed getting Video Data! \"" +
                    video_id + "\" doesn't exist as a video id!"]
        yt_player_config = try_get(get_yt_player_config(html), lambda x: x['args'], dict)
        player_response = parse_json(try_get(yt_player_config, lambda x: x['player_response'], str))
        videoDetails = try_get(player_response, lambda x: x['videoDetails'], dict)
        if yt_player_config:
            if "live_default_broadcast" not in yt_player_config:
                return [False, "Found a Non-Valid Youtube Live Stream."]
            else:
                channel_class.video_id = try_get(videoDetails, lambda x: x['videoId'], str)
                if not channel_class.video_id:
                    return [False, "Unable to find video id in the YouTube player config!"]
        else:
            return [False, "Unable to find YT Player Config."]

        # TO AVOID REPEATING REQUESTS.
        if player_response:
            # playabilityStatus is legit heartbeat all over again..
            playabilityStatus = try_get(player_response, lambda x: x['playabilityStatus'], dict)
            if playabilityStatus is not None and "OK" in playabilityStatus['status']:
                if "streamingData" not in player_response:
                    return [False, "No StreamingData, Youtube bugged out!"]
                manifest_url = str(try_get(player_response, lambda x: x['streamingData']['hlsManifestUrl'], str))
                if not manifest_url:
                    return [False, "Unable to find Manifest URL."]
                formats = download_m3u8_formats(manifest_url)
                if formats is None or len(formats) is 0:
                    return [False, "There were no formats found! Even when the streamer is live."]
                f = get_format_from_data(formats, None)
                thumbnails = try_get(videoDetails, lambda x: x['thumbnail']['thumbnails'], list)
                if thumbnails:
                    channel_class.thumbnail_url = get_highest_thumbnail(thumbnails)
                channel_class.YoutubeStream = {
                    'stream_resolution': '' + str(f['width']) + 'x' + str(f['height']),
                    'HLSStreamURL': f['url'],
                    'title': try_get(videoDetails, lambda x: x['title'], str),
                    'description': videoDetails['shortDescription'],
                }

    CommunityPosts = readCommunityPosts(channel_class, SharedVariables=SharedVariables)
    if CommunityPosts:
        for communityTabMessage in CommunityPosts:
            dict_urls = communityTabMessage['contentText']['URLs']
            # FIND ANY VIDEO ID IN MESSAGE
            if dict_urls:
                for url in dict_urls:
                    video_id_object = re.search(r'youtu.be\/(.+)|youtube.com\/watch\?v=(.+)', url)
                    if video_id_object:
                        video_id_tuple = video_id_object.groups()
                        video_id = next(x for x in video_id_tuple if x is not None)
                        if video_id:
                            if video_id not in already_checked_video_ids:
                                already_checked_video_ids.append(video_id)
                                ok, message = loadVideoData()
                                if not ok:
                                    warning(message)
                                else:
                                    return True
                            # IF ALREADY CHECK IS TOO BIG
                            if len(already_checked_video_ids) is 5:
                                for video_id in already_checked_video_ids:
                                    already_checked_video_ids.remove(video_id)
    elif CommunityPosts is None:
        return None
    return False


def readCommunityPosts(channel_class, SharedVariables=None):
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

    def getCommunityTabListMessages(communityTabSectionRenderer):
        """

        Simplifies a list of all Community Tab Messages information to a simple dict.

        :type communityTabSectionRenderer: list
        """

        def getMessage(communityTabMessageInfo):
            """

            Gets full string message from backstagePostRenderer (Message Holder for community Messages).

            :type communityTabMessageInfo: dict
            """
            communityMessage = []
            communityURL = []

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
                                communityMessage.append(fullUrl)
                                if fullUrl:
                                    communityURL.append(fullUrl)
                            else:
                                partMessage = try_get(textHolder, lambda x: x['text'], str)
                                if partMessage:
                                    communityMessage.append(partMessage)
            community = {
                'communityMessage': ''.join(communityMessage),
                'URLs': communityURL
            }
            return community

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

    headers = {"DNT": 1, "upgrade-insecure-requests": 1}
    url = 'https://www.youtube.com/channel/' + channel_class.channel_id + '/community'
    website = download_website(
        url,
        headers=headers, SharedVariables=SharedVariables)
    if type(website) is bool or website is None:
        return None

    youtubeInitialData = get_yt_initial_data(website)
    if youtubeInitialData is None:
        warning("Unable to find Initial Data.")
        return False
    twoColumnBrowseResultsRenderer = try_get(youtubeInitialData, lambda x: x['contents'][
        'twoColumnBrowseResultsRenderer'], dict)
    tabs = try_get(twoColumnBrowseResultsRenderer, lambda x: x['tabs'], list)
    communityTab = getCommunityTabInfo(tabs)
    itemSectionRenderer = try_get(communityTab, lambda x: x['content']['sectionListRenderer']['contents'][
        0]['itemSectionRenderer']['contents'], list)
    communityTabMessages = getCommunityTabListMessages(itemSectionRenderer)
    return communityTabMessages
