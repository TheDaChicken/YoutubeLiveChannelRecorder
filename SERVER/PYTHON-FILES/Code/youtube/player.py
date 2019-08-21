import os
from datetime import datetime
from threading import Thread
from time import sleep
import json

from ..dataHandler import CacheDataHandler
from ..encoder import Encoder
from ..log import stopped, warning, info
from ..utils.other import get_format_from_data, try_get
from ..utils.parser import parse_json
from ..utils.web import download_website, download_m3u8_formats
from ..utils.windowsNotification import show_windows_toast_notification


# from .channelClass import ChannelInfo


def openStream(channelClass, StreamInfo, sharedDataHandler=None):
    """

    Records Youtube Live Stream. This holds until live stream is over.
    Note: ChannelClass is meant to be self in ChannelInfo class.

    :type YoutubeStream: dict
    :type channelClass: ChannelInfo
    :type sharedDataHandler: CacheDataHandler
    """

    channelClass.title = StreamInfo['title']
    channelClass.description = StreamInfo['description']
    # Sets video_locations and thumbnail (if you have it enabled

    filename = channelClass.create_filename(channelClass.video_id)
    channelClass.video_location = os.path.join("RecordedStreams", '{0}.mp4'.format(filename))
    if sharedDataHandler:
        if sharedDataHandler.getValue('DownloadThumbnail'):
            channelClass.thumbnail_location = os.path.join("RecordedStreams", '{0}.jpg'.format(filename))

    channelClass.EncoderClass = Encoder()
    channelClass.recording_status = "Starting Recording."

    ok = channelClass.EncoderClass.start_recording(StreamInfo['HLSStreamURL'], channelClass.video_location)

    if not ok:
        channelClass.recording_status = "Failed To Start Recording."
        show_windows_toast_notification("Live Recording Notifications", "Failed to start record for " +
                                        channelClass.channel_name)
        while True:
            info("Holding until Stream is over.")
            array = channelClass.is_live()
            if array:
                sleep(channelClass.pollDelayMs / 1000)
            elif not array:
                if array is None:
                    warning("Internet Offline. :/")
                    sleep(channelClass.pollDelayMs / 1000)
                else:
                    warning("Recording failed, so it is unneeded for the recording to stop.")
                    sleep(channelClass.pollDelayMs / 1000 / 2)
                    channelClass.EncoderClass = None
                    channelClass.recording_status = None
                    return False

    channelClass.start_date = datetime.now()

    channelClass.recording_status = "Recording."

    show_windows_toast_notification("Live Recording Notifications", "{0} is live and is now "
                                                                    "recording. \n"
                                                                    "Recording at "
                                                                    "{1}{2}".format(channelClass.channel_name,
                                                                                    StreamInfo['stream_resolution'],
                                                                                    "\n[SPONSOR STREAM]" if channelClass
                                                                                    .sponsor_only_stream else ''))
    if sharedDataHandler:
        if sharedDataHandler.getValue('DownloadThumbnail') is True and channelClass.privateStream is not True:
            thread = Thread(target=channelClass.download_thumbnail, name=channelClass.channel_name)
            thread.daemon = True  # needed control+C to work.
            thread.start()

    # Adds to the temp upload list.
    if channelClass.video_id in channelClass.video_list:
        temp_dict = channelClass.video_list.get(channelClass.video_id)  # type: dict
        if 'file_location' in temp_dict:
            file_location = temp_dict['file_location']  # type: list
            file_location.append(channelClass.video_location)
    else:
        temp_youtube_stream = StreamInfo.copy()
        temp_youtube_stream.update({
            'start_date': channelClass.start_date
        })
        channelClass.video_list.update({
            channelClass.video_id: {
                'video_id': channelClass.video_id, 'video_data': temp_youtube_stream, 'channel_data': {
                    'channel_name': channelClass.channel_name,
                    'channel_id': channelClass.channel_id,
                },
                'file_location': [channelClass.video_location, ],
                'thumbnail_location': channelClass.thumbnail_location}
        })
        del temp_youtube_stream

    # Write YouTube Stream info to json.
    with open("{3} - '{4}' - {0}-{1}-{2}.json".format(channelClass.start_date.month, channelClass.start_date.day,
                                                      channelClass.start_date.year,
                                                      channelClass.channel_name, channelClass.video_id), 'w',
              encoding='utf-8') as f:
        json.dump({
            'video_id': channelClass.video_id, 'video_data': StreamInfo, 'channel_data': {
                'channel_name': channelClass.channel_name,
                'channel_id': channelClass.channel_id,
            },
        }, f, ensure_ascii=False, indent=4)

    if channelClass.TestUpload:
        sleep(10)
        sleep(channelClass.pollDelayMs / 1000 / 2)
        channelClass.EncoderClass.stop_recording()
        channelClass.EncoderClass = None
        return True

    offline = False
    while channelClass.stop_heartbeat is False:
        array = channelClass.is_live()
        if not array:
            if array is None:
                if offline is not True:
                    offline = True
                    channelClass.recording_status = "Internet Offline."
                    warning("Internet Offline. :/")
                    if channelClass.EncoderClass.running:
                        channelClass.EncoderClass.stop_recording()
                        warning("- Turning off Recording -")
                    else:
                        warning("- Recording Crashed -")
                    show_windows_toast_notification("Live Recording Notifications", "INTERNET WENT OFFLINE "
                                                                                    "DURING {0}'s live stream!".
                                                    format(channelClass.channel_name))
                sleep(channelClass.pollDelayMs / 1000)
            else:
                sleep(channelClass.pollDelayMs / 1000 + .9)
                channelClass.EncoderClass.stop_recording()
                channelClass.EncoderClass = None
                return True
        elif array:
            if channelClass.EncoderClass:
                if not channelClass.EncoderClass.running:
                    if offline:
                        offline = False
                        # Starts the recording back if internet was offline.
                        channelClass.recording_status = "Starting Recording."

                        channelClass.video_location = os.path.join("RecordedStreams",
                                                                   channelClass.
                                                                   create_filename(
                                                                       channelClass.video_id)
                                                                   + '.mp4')

                        channelClass.EncoderClass.start_recording(YoutubeStream['HLSStreamURL'],
                                                                  channelClass.video_location)

                        channelClass.recording_status = "Recording."
                        show_windows_toast_notification("Live Recording Notifications", "{0} is live "
                                                                                        "and is now recording. \n"
                                                                                        "Recording at "
                                                                                        "{1}{2}".
                                                        format(channelClass.channel_name,
                                                               YoutubeStream['stream_resolution'],
                                                               "\n[SPONSOR STREAM]" if channelClass.sponsor_only_stream
                                                               else ''))
                    else:
                        channelClass.recording_status = "Crashed."
                        show_windows_toast_notification("Live Recording Notifications", "FFMPEG CRASHED ON " +
                                                        channelClass.channel_name + "'s live stream! Retrying ...")
                        info("FFmpeg crashed. Restarting ... Uploading part that was recorded (if uploading is on).")
                        return False
                sleep(channelClass.pollDelayMs / 1000)


def getYoutubeStreamInfo(channelInfo, recordingHeight=None):
    """

    Gets the stream info from channelClass.

    Looked at for reference:
    https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1675

    :type recordingHeight: str, int, None
    :type channelInfo: ChannelInfo
    """
    try:
        from urllib.parse import urlencode, parse_qs
        from urllib.request import urlopen
    except ImportError:
        parse_qs = None  # Fixes a random PyCharm warning.
        urlencode = None
        stopped("Unsupported version of Python. You need Version 3 :<")

    url_arguments = {'html5': 1, 'video_id': channelInfo.video_id}
    from . import client_name, client_version, ps, sts, cbr, client_os, client_os_version
    if ps is not None:
        url_arguments.update({'ps': ps})
    url_arguments.update({'eurl': ''})
    url_arguments.update({'hl': 'en_US'})
    if sts is not None:
        url_arguments.update({'sts': sts})
    if client_name is not None:
        url_arguments.update({'c': client_name})
    if cbr is not None:
        url_arguments.update({'cbr': cbr})
    if client_version is not None:
        url_arguments.update({'cver': client_version})
    if client_os is not None:
        url_arguments.update({'cos': client_os})
    if client_os_version is not None:
        url_arguments.update({'cosver': client_os_version})
    if channelInfo.cpn is not None:
        url_arguments.update({'cpn': channelInfo.cpn})

    video_info_website = download_website(
        'https://www.youtube.com/get_video_info?{0}'.format(
            urlencode(url_arguments)))
    if video_info_website is None:
        return video_info_website
    video_info = parse_qs(video_info_website)
    player_response = parse_json(try_get(video_info, lambda x: x['player_response'][0], str))
    video_details = try_get(player_response, lambda x: x['videoDetails'], dict)

    if player_response:
        if "streamingData" not in player_response:
            warning("No StreamingData, Youtube bugged out!")
            return None
        manifest_url = str(try_get(player_response, lambda x: x['streamingData']['hlsManifestUrl'], str))
        if not manifest_url:
            warning("Unable to find HLS Manifest URL.")
            return None
        formats = download_m3u8_formats(manifest_url)
        if formats is None or len(formats) is 0:
            warning("There were no formats found! Even when the streamer is live.")
            return None
        f = get_format_from_data(formats, recordingHeight)
        youtube_stream_info = {
            'stream_resolution': '{0}x{1}'.format(str(f['width']), str(f['height'])),
            'HLSManifestURL': manifest_url,
            'DashManifestURL': str(try_get(player_response, lambda x: x['streamingData']['dashManifestUrl'], str)),
            'HLSStreamURL': f['url'],
            'title': try_get(video_details, lambda x: x['title'], str),
            'description': try_get(video_details, lambda x: x['shortDescription'], str),
            'video_id': channelInfo.video_id
        }
        return youtube_stream_info
    return None
