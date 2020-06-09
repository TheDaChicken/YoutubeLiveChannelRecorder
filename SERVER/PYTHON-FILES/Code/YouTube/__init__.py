import os
import traceback
from datetime import datetime
from random import randint
from threading import Thread
from time import sleep
from urllib.parse import urlencode, parse_qs

from Code.YouTube.utils import get_yt_player_config, get_yt_initial_data, get_endpoint_type, re
from Code.Templates.ChannelObject import TemplateChannel
from Code.utils.web import download_website
from Code.log import verbose, warning, info, crash_warning
from Code.utils.other import try_get, getTimeZone, get_format_from_data, get_highest_thumbnail, get_utc_offset
from Code.dataHandler import CacheDataHandler
from Code.utils.parser import parse_json
from Code.YouTube.heartbeat import is_live


class ChannelObject(TemplateChannel):
    platform_name = "YOUTUBE"

    # CHANNEL
    channel_id = None
    channel_name = None

    # SERVER VARIABLES
    queue_holder = None

    # WEBSITE Handling
    sharedCookieDict = None

    # YOUTUBE'S HEARTBEAT SYSTEM
    pollDelayMs = 8000
    sequence_number = 0
    broadcast_id = None
    last_heartbeat = None

    # STOP HEARTBEAT
    stop_heartbeat = False

    # USER
    sponsor_on_channel = False

    # VIDEO DETAILS
    video_id = None
    title = None
    description = None
    privateStream = False
    thumbnail_url = None
    dvr_enabled = False

    thumbnail_location = None

    # Scheduled Live Stream. [HEARTBEAT]
    live_scheduled = False
    live_scheduled_time = None  # type: datetime
    live_scheduled_timeString = None

    # PER-CHANNEL YOUTUBE VARIABLES
    cpn = None

    def __init__(self, channel_id, SettingDict, SharedCookieDict=None, cachedDataHandler=None,
                 queue_holder=None, globalVariables=None):
        """

        :type channel_id: str
        :type cachedDataHandler: CacheDataHandler
        :type SharedCookieDict: dict
        :type globalVariables: GlobalVariables
        """
        self.channel_id = channel_id
        super().__init__(channel_id, SettingDict, SharedCookieDict, cachedDataHandler, queue_holder, globalVariables)

    def loadVideoData(self, video_id=None):
        self.video_id = video_id
        if video_id:
            url = "https://www.youtube.com/watch?v={0}".format(video_id)
        else:
            url = "https://www.youtube.com/channel/{0}/live".format(self.channel_id)

        website_object = download_website(url, CookieDict=self.sharedCookieDict)
        # self.sharedCookieDict.update(websiteClass.cookies)
        if website_object.text is None:
            return [False, "Failed getting Youtube Data from the internet! "
                           "This means there is no good internet available!"]
        if website_object.status_code == 404:
            return [False, "Failed getting Youtube Data! \"{0}\" doesn't exist as a channel id!".format(
                self.channel_id)]
        website_string = website_object.text

        endpoint_type = get_endpoint_type(website_string)
        if endpoint_type:
            if endpoint_type == 'browse':
                array = re.findall(r'property="og:title" content="(.+?)"', website_string)
                if array:
                    channel_name = array[0]
                    warning("{0} has the live stream "
                            "currently unlisted or private, or only for members. "
                            "Using safeguard. This may not be the best to leave on.\n".format(channel_name))
                    self.channel_name = channel_name
                    self.video_id = None
                    self.privateStream = True
            else:
                if not endpoint_type == 'watch':
                    warning("Unrecognized endpoint type. Endpoint Type: {0}.".format(endpoint_type))
                verbose("Getting Video ID.")
                youtube_initial_data = get_yt_initial_data(website_string)
                yt_player_config = try_get(get_yt_player_config(website_string), lambda x: x, dict)
                player_response = parse_json(try_get(yt_player_config, lambda x: x['args']['player_response'], str))
                videoDetails = try_get(player_response, lambda x: x['videoDetails'], dict)
                if yt_player_config and videoDetails:
                    if "isLiveContent" in videoDetails and \
                            videoDetails['isLiveContent'] and \
                            ("isLive" in videoDetails or "isUpcoming" in videoDetails):
                        self.channel_name = try_get(videoDetails, lambda x: x['author'], str)
                        self.video_id = try_get(videoDetails, lambda x: x['videoId'], str)
                        self.privateStream = False
                        if not self.channel_id:
                            self.channel_id = try_get(videoDetails, lambda x: x['channelId'], str)
                    else:
                        return [False, "Found a stream, the stream seemed to be a non-live stream."]
                else:
                    return [False, "Unable to get yt player config, and videoDetails."]
                contents = try_get(youtube_initial_data,
                                   lambda x: x['contents']['twoColumnWatchNextResults']['results']['results'][
                                       'contents'], list)
                videoSecondaryInfoRenderer = try_get(
                    [content for content in contents if content.get("videoSecondaryInfoRenderer") is not None],
                    lambda x: x[0], dict).get("videoSecondaryInfoRenderer")
                channelImageFormats = try_get(videoSecondaryInfoRenderer, lambda x:
                x['owner']['videoOwnerRenderer']['thumbnail']['thumbnails'], list)
                if channelImageFormats is not None:
                    self.channel_image = max(channelImageFormats, key=lambda x: x.get("height")).get("url")
                if not self.privateStream:
                    # TO AVOID REPEATING REQUESTS.
                    if player_response:
                        # playabilityStatus is legit heartbeat all over again..
                        playabilityStatus = try_get(player_response, lambda x: x['playabilityStatus'], dict)
                        status = try_get(playabilityStatus, lambda x: x['status'], str)  # type: str
                        reason = try_get(playabilityStatus, lambda x: x['reason'], str)  # type: str
                        if playabilityStatus and status:
                            if 'OK' in status.upper():
                                if reason and 'ended' in reason:
                                    return [False, reason]

                                streamingData = try_get(player_response, lambda x: x['streamingData'], dict)
                                if streamingData:
                                    if 'licenseInfos' in streamingData:
                                        licenseInfo = streamingData.get('licenseInfos')
                                        drmFamilies = map(lambda x: x.get('drmFamily'), licenseInfo)
                                        return [False, "This live stream contains DRM and cannot be recorded.\n"
                                                       "DRM Families: {0}".format(', '.join(drmFamilies))]
                                    manifest_url = str(
                                        try_get(streamingData, lambda x: x['hlsManifestUrl'], str))
                                    if not manifest_url:
                                        return [False, "Unable to find HLS Manifest URL."]
                                    downloadOBJECT = download_website(manifest_url, CookieDict=self.sharedCookieDict)
                                    hls = downloadOBJECT.parse_m3u8_formats()
                                    if len(hls.formats) == 0:
                                        return [False, "There were no formats found! Even when the streamer is live."]
                                    format_ = get_format_from_data(
                                        hls, self.cachedDataHandler.getValue('recordingResolution'))
                                    if not videoDetails:
                                        videoDetails = try_get(player_response, lambda x: x['videoDetails'], dict)
                                    thumbnails = try_get(videoDetails, lambda x: x['thumbnail']['thumbnails'], list)
                                    if thumbnails:
                                        self.thumbnail_url = get_highest_thumbnail(thumbnails)
                                    self.dvr_enabled = try_get(videoDetails, lambda x: x['isLiveDvrEnabled'], bool)
                                    self.StreamFormat = format_
                                    self.title = try_get(videoDetails, lambda x: x['title'], str)
                                    self.description = videoDetails['shortDescription']
                                else:
                                    return [False, "No StreamingData, YouTube bugged out!"]
                            self.live_streaming = self.is_live(json=playabilityStatus)
                    # GET YOUTUBE GLOBAL VARIABLES
                    if self.globalVariables.get("checkedYouTubeVariables") is None:
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

                        def getServiceSettings(serviceTrackingParamsList, service_nameLook):
                            if serviceTrackingParamsList:
                                for service in serviceTrackingParamsList:
                                    service_name = try_get(service, lambda x: x['service'], str)
                                    if service_name is not None and service_name in service_nameLook:
                                        return service
                            return None

                        if self.globalVariables.get("alreadyChecked") is False or self.globalVariables.get(
                                "alreadyChecked") is None:
                            verbose("Getting Global YouTube Variables.")
                            e_catcher = getServiceSettings(try_get(youtube_initial_data, lambda x: x['responseContext'][
                                'serviceTrackingParams'], list), "ECATCHER")
                            account_playback_token = try_get(yt_player_config,
                                                             lambda x: x['args']['account_playback_token'][:-1], str)
                            ps = try_get(yt_player_config, lambda x: x['args']['ps'], str)
                            cbr = try_get(yt_player_config, lambda x: x['args']['cbr'])
                            client_os = try_get(yt_player_config, lambda x: x['args']['cos'])
                            client_os_version = try_get(yt_player_config, lambda x: x['args']['cosver'])
                            if account_playback_token is None:
                                warning("Unable to find account playback token in the YouTube player config.")
                            if ps is None:
                                warning("Unable to find ps in the YouTube player config.")
                            if cbr is None:
                                warning("Unable to find cbr in the YouTube player config.")
                            if client_os is None:
                                warning("Unable to find Client OS in the YouTube player config.")
                            if client_os_version is None:
                                warning("Unable to find Client OS Version in the YouTube player config.")
                            self.globalVariables.set("checkedYouTubeVariables", None)
                            if not youtube_initial_data:
                                warning("Unable to get Youtube Initial Data. Cannot find all Youtube Variables.")
                            elif e_catcher is None:
                                warning("Unable to get ECATCHER service data in Youtube Initial Data. "
                                        "Cannot find all Youtube Variables.")
                            else:
                                params = try_get(e_catcher, lambda x: x['params'], list)
                                page_build_label = getSettingsValue(params, 'innertube.build.label',
                                                                    name="Page Build Label")
                                page_cl = getSettingsValue(params, 'innertube.build.changelist', name="Page CL")
                                variants_checksum = getSettingsValue(params, 'innertube.build.variants.checksum',
                                                                     name="Variants Checksum")
                                client_version = getSettingsValue(params, 'client.version', name="Client Version")
                                client_name = getSettingsValue(params, 'client.name', name="Client Name")
                                self.globalVariables.set("page_build_label", page_build_label)
                                self.globalVariables.set("page_cl", page_cl)
                                self.globalVariables.set("client_version", client_version)
                                self.globalVariables.set("client_name", client_name)
                                self.globalVariables.set("variants_checksum", variants_checksum)
                            self.globalVariables.set("ps", ps)
                            self.globalVariables.set("cbr", cbr)
                            self.globalVariables.set("client_os", client_os)
                            self.globalVariables.set("client_os_version", client_os_version)
                            self.globalVariables.set("account_playback_token", account_playback_token)
                            self.globalVariables.set("utf_offset", get_utc_offset())
                            self.globalVariables.set("timezone", getTimeZone())
                            self.globalVariables.set("alreadyChecked", True)

        # ONLY WORKS IF LOGGED IN
        self.sponsor_on_channel = self.get_sponsor_channel(html_code=website_string)

        self.cpn = self.generate_cpn()
        return [True, "OK"]

    @staticmethod
    def getServiceSettings(serviceTrackingParamsList, service_nameLook):
        if serviceTrackingParamsList:
            for service in serviceTrackingParamsList:
                service_name = try_get(service, lambda x: x['service'], str)
                if service_name is not None and service_name in service_nameLook:
                    return service
        return None

    @staticmethod
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

    @staticmethod
    def generate_cpn():
        """
        Looked at for reference:
        https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1531
        """
        CPN_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        return ''.join((CPN_ALPHABET[randint(0, 256) & 63] for _ in range(0, 16)))

    def get_sponsor_channel(self, html_code=None):
        # from .. import is_google_account_login_in
        if True:
            verbose("Checking if account sponsored {0}.".format(self.channel_name))
            if html_code is None:
                html_code = download_website("https://www.youtube.com/channel/{0}/live".format(self.channel_id),
                                             CookieDict=self.sharedCookieDict)
                if html_code is None:
                    return None
            html_code = str(html_code)
            array = re.findall('/channel/{0}/membership'.format(self.channel_id), html_code)
            if array:
                return True
            return False
        # return False

    def get_video_info(self):
        """
        Gets the stream info from channelClass.
        Looked at for reference:
        https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1675
        """
        url_arguments = {'html5': 1, 'video_id': self.video_id}
        if self.globalVariables.get("ps") is not None:
            url_arguments.update({'ps': self.globalVariables.get("ps")})
        url_arguments.update({'eurl': ''})
        url_arguments.update({'hl': 'en_US'})
        if self.globalVariables.get("client_name") is not None:
            url_arguments.update({'c': self.globalVariables.get("client_name")})
        if self.globalVariables.get("cbr") is not None:
            url_arguments.update({'cbr': self.globalVariables.get("cbr")})
        if self.globalVariables.get("client_version") is not None:
            url_arguments.update({'cver': self.globalVariables.get("client_version")})
        if self.globalVariables.get("client_os") is not None:
            url_arguments.update({'cos': self.globalVariables.get("client_os")})
        if self.globalVariables.get("client_os_version") is not None:
            url_arguments.update({'cosver': self.globalVariables.get("client_os_version")})
        if self.cpn is not None:
            url_arguments.update({'cpn': self.cpn})

        downloadClass = download_website(
            'https://www.youtube.com/get_video_info?{0}'.format(
                urlencode(url_arguments)), CookieDict=self.sharedCookieDict)
        video_info_website = downloadClass.text

        video_info = parse_qs(video_info_website)
        player_response = parse_json(try_get(video_info, lambda x: x['player_response'][0], str))
        if player_response:
            video_details = try_get(player_response, lambda x: x['videoDetails'], dict)
            if "streamingData" not in player_response:
                warning("No StreamingData, Youtube bugged out!")
                return None
            manifest_url = str(try_get(player_response, lambda x: x['streamingData']['hlsManifestUrl'], str))
            if not manifest_url:
                warning("Unable to find HLS Manifest URL.")
                return None
            downloadOBJECT = download_website(manifest_url, CookieDict=self.sharedCookieDict)
            if downloadOBJECT.status_code != 200:
                return None
            hls = downloadOBJECT.parse_m3u8_formats()
            if len(hls.formats) == 0:
                warning("There were no formats found! Even when the streamer is live.")
                return None
            return {
                'formats': hls,
                'manifest_url': manifest_url,
                'video_details': video_details,
            }
        return None

    def channel_thread(self):
        if self.StreamFormat is not None:
            if self.start_recording(self.StreamFormat, StartIndex0=self.enableDVR):
                if self.TestUpload is True:
                    warning("Test Upload Enabled For {0}".format(self.channel_name))
                    sleep(10)
                    self.EncoderClass.stop_recording()
                    self.add_youtube_queue()
                    exit(0)

        if self.live_streaming is not None:
            sleep(self.pollDelayMs / 1000)
        try:
            while self.stop_heartbeat is False:
                # LOOP
                self.live_streaming = self.is_live()
                # HEARTBEAT ERROR
                if self.live_streaming == -1:
                    # IF CRASHED.
                    info("Error on Heartbeat on {0}! Trying again ...".format(self.channel_name))
                    sleep(1)
                # INTERNET OFFLiNE.
                elif self.live_streaming is None:
                    warning("INTERNET OFFLINE")
                    sleep(2.4)
                # FALSE
                elif self.live_streaming is False:
                    # TURN OFF RECORDING IF FFMPEG IS STILL ALIVE.
                    if self.EncoderClass.running is True:
                        x = Thread(target=self.stop_recording)
                        x.daemon = True
                        x.start()
                    if self.privateStream is False:
                        info("{0} is not live!".format(self.channel_name))
                        sleep(self.pollDelayMs / 1000)
                    else:
                        info("{0}'s channel live streaming is currently private/unlisted!".format(
                            self.channel_name))
                        sleep(self.pollDelayMs / 1000)
                # LIVE
                elif self.live_streaming is True:
                    # IF FFMPEG IS NOT ALIVE THEN TURN ON RECORDING.
                    if self.EncoderClass.running is not True:
                        video_details = self.get_video_info()
                        formats = video_details.get("formats")
                        videoDetails = video_details.get("video_details")
                        format_ = get_format_from_data(
                            formats, self.cachedDataHandler.getValue('recordingResolution'))
                        self.StreamFormat = format_
                        self.title = try_get(videoDetails, lambda x: x['title'], str)
                        self.description = try_get(videoDetails, lambda x: x['shortDescription'], str)
                        self.dvr_enabled = try_get(videoDetails, lambda x: x['isLiveDvrEnabled'], bool)
                        x = Thread(target=self.start_recording, args=(format_,))
                        x.daemon = True
                        x.start()
                    sleep(self.pollDelayMs / 1000)
                # REPEAT (END OF LOOP)
        except:
            self.crashed_traceback = traceback.format_exc()
            crash_warning("{0}:\n{1}".format(self.channel_name, traceback.format_exc()))

    def is_live(self, json=None):
        if self.DebugMode is True:
            self.last_heartbeat = datetime.now()
        if self.privateStream:
            self.loadVideoData()
            return False
        boolean_live = is_live(self, json=json, CookieDict=self.sharedCookieDict,
                               globalVariables=self.globalVariables)
        return boolean_live

    def close(self):
        super().close()
        self.stop_heartbeat = True


def searchChannels(search, CookieDict):
    def formatChannel(channelContent):
        channelRenderer = channelContent.get("channelRenderer")
        channel_image = None
        channelImageFormats = try_get(channelRenderer, lambda x: x['thumbnail']['thumbnails'], list)
        if channelImageFormats is not None:
            channel_image = "https:{0}".format(max(channelImageFormats, key=lambda x: x.get("height")).get("url"))
        channel = {
            'channel_identifier': try_get(channelRenderer, lambda x: x['channelId'], str),
            'channel_name': try_get(channelRenderer, lambda x: x['title']['simpleText'], str),
            'follower_count': try_get(channelRenderer, lambda x: x['subscriberCountText']['simpleText'], str),
            'channel_image': channel_image,
            'platform': 'YOUTUBE'
        }
        return channel

    def formatDidYouMean(didYouMeanContent):
        didYouMeanRenderer = didYouMeanContent.get("didYouMeanRenderer")
        didYouMean = {
            'didYouMean': try_get(didYouMeanRenderer, lambda x: x['didYouMean']['runs'][0]['text'], str),
            'correctedQuery': try_get(didYouMeanRenderer, lambda x: x['correctedQuery']['runs'][0]['text'], str)
        }
        return didYouMean

    # For some stupid reason, YouTube will only provide Searches on BR Content Encoding
    downloadOBJECT = download_website(
        "https://www.youtube.com/results?{0}".format(urlencode({'search_query': search, 'sp': 'EgIQAg%3D%3D'})),
        headers={
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': '*/*',
        }, CookieDict=CookieDict)
    if downloadOBJECT.response_headers.get('Content-Encoding') == 'br':
        # Check for support for that.
        try:
            import brotli
        except ImportError:
            return [False, 'No Support for BR Content Encoding on Server. Required Packages: requests, brotlipy.']
    websiteString = downloadOBJECT.text
    youtube_initial_data = get_yt_initial_data(websiteString)
    if youtube_initial_data is None:
        return [False, 'Unable to find YouTube initial data.']
    contents = try_get(youtube_initial_data,
                       lambda x: x['contents']['twoColumnSearchResultsRenderer']['primaryContents'][
                           'sectionListRenderer']['contents'], list)
    if contents is None:
        return [False, 'Unable to find contents.']
    itemSectionRenderer = try_get(
        [content for content in contents if content.get("itemSectionRenderer") is not None] or [],
        lambda x: x[0], dict).get("itemSectionRenderer")
    if itemSectionRenderer is None:
        return [False, 'Unable to find itemSectionRenderer.']
    contents = itemSectionRenderer.get("contents")
    if itemSectionRenderer is None:
        return [False, "Unable to find itemSectionRenderer contents."]
    channels = list(map(formatChannel, [x for x in contents if 'channelRenderer' in x]))
    response = {
        'channels': channels
    }
    didYouMean = list(map(formatDidYouMean, [x for x in contents if 'didYouMeanRenderer' in x]))
    if len(didYouMean) > 0:
        response.update({'didYouMean': didYouMean})
    return [True, response]
