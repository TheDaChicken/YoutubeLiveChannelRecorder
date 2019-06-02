import os
from threading import Thread
from time import sleep

from ..utils.web import download_website, download_m3u8_formats
from ..utils.parser import parse_json
from ..utils.youtube import get_yt_player_config
from ..utils.other import get_format_from_data
from ..utils.windowsNotification import show_windows_toast_notification
from ..dataHandler import DownloadThumbnail
from ..log import stopped, warning, info
from ..encoder import Encoder


# from .channelClass import ChannelInfo


def openStream(channelClass, recordingHeight=None, alreadyLIVE=False):
    """

    Records Youtube Live Stream. This holds until live stream is over.
    Note: ChannelClass is meant to be self in ChannelInfo class.

    :type alreadyLIVE: bool
    :type recordingHeight: str, int, None
    :type channelClass: ChannelInfo
    """

    YoutubeStream = getYoutubeStreamInfo(channelClass, alreadyLIVE=alreadyLIVE, recordingHeight=recordingHeight)

    channelClass.title = YoutubeStream['title']
    channelClass.description = YoutubeStream['description']
    # Sets video_locations and thumbnail (if you have it enabled

    filename = channelClass.create_filename(channelClass.video_id)
    channelClass.video_location = os.path.join("RecordedStreams", filename + '.mp4')
    if DownloadThumbnail() is True:
        channelClass.thumbnail_location = os.path.join("RecordedStreams", filename + '.jpg')

    channelClass.EncoderClass = Encoder(YoutubeStream['url'], channelClass.video_location)
    channelClass.recording_status = "Starting Recording."

    ok = channelClass.EncoderClass.start_recording()

    if not ok:
        channelClass.recording_status = "Failed To Start Recording."
        show_windows_toast_notification("Live Recording Notifications", "Failed to start record for " +
                                        channelClass.channel_name)
        while True:
            info("Holding until Stream is over.")
            array = channelClass.is_live()
            channelClass.live_streaming = array
            if array is None:
                warning("Internet Offline. :/")
                sleep(channelClass.pollDelayMs / 1000)
            elif array is True:
                sleep(channelClass.pollDelayMs / 1000)
            elif array is False:
                warning("Recording failed, so it is unneeded for the recording to stop.")
                sleep(channelClass.pollDelayMs / 1000 / 2)
                channelClass.EncoderClass = None
                channelClass.recording_status = None
                return False

    channelClass.recording_status = "Recording."

    show_windows_toast_notification("Live Recording Notifications", channelClass.channel_name + " is live and is now "
                                                                                                "recording. \n"
                                                                                                "Recording at "
                                    + YoutubeStream['stream_resolution'] +
                                    ("\n[SPONSOR STREAM]" if channelClass.privateStream else ''))

    if DownloadThumbnail() is True:
        thread = Thread(target=channelClass.download_thumbnail, name=channelClass.channel_name)
        thread.daemon = True  # needed control+C to work.
        thread.start()

    if channelClass.TestUpload:
        sleep(10)
        sleep(channelClass.pollDelayMs / 1000 / 2)
        channelClass.EncoderClass.stop_recording()
        channelClass.EncoderClass = None
        return True
    offline = False
    while True:
        if channelClass.EncoderClass.running is False:
            channelClass.recording_status = "Crashed."
            show_windows_toast_notification("Live Recording Notifications", "FFMPEG CRASHED ON " +
                                            channelClass.channel_name + " live stream! Retrying ...")
            info("FFmpeg crashed. Restarting ... Uploading part that was recorded (if uploading is on).")
            return False
        array = channelClass.is_live()
        channelClass.live_streaming = array
        if array is None:
            if offline is not True:
                offline = True
                channelClass.EncoderClass.stop_recording()
                warning("Internet Offline. :/")
                warning("- Turning off Recording -")
            sleep(channelClass.pollDelayMs / 1000)
        elif array is True:
            sleep(channelClass.pollDelayMs / 1000)
            if offline is True:
                offline = False
                # Starts the recording back if internet was offline.
                channelClass.EncoderClass.start_recording(videoLocation=os.path.join("RecordedStreams",
                                                                                     channelClass.create_filename(
                                                                                         channelClass.video_id)
                                                                                     + '.mp4'))
        elif array is False:
            sleep(channelClass.pollDelayMs / 1000 / 2)
            channelClass.EncoderClass.stop_recording()
            channelClass.EncoderClass = None
            return True


def getYoutubeStreamInfo(channelInfo, alreadyLIVE=None, recordingHeight=None):
    """

    Gets the stream info from channelClass.

    Looked at for reference:
    https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1675

    :type recordingHeight: str, int, None
    :type alreadyLIVE: bool
    :type channelInfo: ChannelInfo
    """
    try:
        from urllib.parse import urlencode, parse_qs
        from urllib.request import urlopen
    except ImportError:
        parse_qs = None  # Fixes a random PyCharm warning.
        stopped("Unsupported version of Python. You need Version 3 :<")

    if alreadyLIVE is False:
        video_info_website = download_website(
            'https://www.youtube.com/get_video_info?video_id={0}'.format(channelInfo.video_id))
        if video_info_website is None:
            return video_info_website
        video_info = parse_qs(video_info_website)
        player_response = parse_json(video_info.get('player_response')[0])
    else:
        video_website = download_website('https://www.youtube.com/channel/{0}/live'.format(channelInfo.channel_id))
        video_info = get_yt_player_config(video_website)['args']
        player_response = parse_json(video_info.get('player_response'))
    if player_response is None or "streamingData" not in player_response or "hlsManifestUrl" \
            not in player_response['streamingData']:
        warning("No StreamingData, Youtube bugged out!")
        return None
    manifest_url = str(player_response['streamingData']['hlsManifestUrl'])
    formats = download_m3u8_formats(manifest_url)
    if formats is None or len(formats) is 0:
        warning("There were no formats found! Even when the streamer is live.")
        return None

    f = get_format_from_data(formats, recordingHeight)
    youtube_stream_info = {
        'stream_resolution': '' + str(f['width']) + 'x' + str(f['height']),
        'url': f['url'],
        'title': video_info['title'],
        'description': player_response['videoDetails']['shortDescription'],
    }
    return youtube_stream_info
