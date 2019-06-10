import os
from threading import Thread
from time import sleep

from ..utils.web import download_website, download_m3u8_formats
from ..utils.parser import parse_json
from ..utils.other import get_format_from_data, try_get
from ..utils.windowsNotification import show_windows_toast_notification
from ..dataHandler import DownloadThumbnail
from ..log import stopped, warning, info
from ..encoder import Encoder


# from .channelClass import ChannelInfo


def openStream(channelClass, YoutubeStream):
    """

    Records Youtube Live Stream. This holds until live stream is over.
    Note: ChannelClass is meant to be self in ChannelInfo class.

    :type YoutubeStream: dict
    :type channelClass: ChannelInfo
    """

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

    channelClass.recording_status = "Recording."

    show_windows_toast_notification("Live Recording Notifications", channelClass.channel_name + " is live and is now "
                                                                                                "recording. \n"
                                                                                                "Recording at "
                                    + YoutubeStream['stream_resolution'] +
                                    ("\n[SPONSOR STREAM]" if channelClass.sponsor_only_stream else ''))

    if DownloadThumbnail() is True and channelClass.privateStream is not True:
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
                    show_windows_toast_notification("Live Recording Notifications", "INTERNET WHEN OFFLINE DURING " +
                                                    channelClass.channel_name + "'s live stream!")
                sleep(channelClass.pollDelayMs / 1000)
            else:
                sleep(channelClass.pollDelayMs / 1000 / 2)
                channelClass.EncoderClass.stop_recording()
                channelClass.EncoderClass = None
                return True
        elif array:
            if not channelClass.EncoderClass.running:
                if offline:
                    offline = False
                    # Starts the recording back if internet was offline.
                    channelClass.recording_status = "Starting Recording."
                    channelClass.EncoderClass.start_recording(videoLocation=os.path.join("RecordedStreams",
                                                                                         channelClass.create_filename(
                                                                                             channelClass.video_id)
                                                                                         + '.mp4'))
                    channelClass.recording_status = "Recording."
                    show_windows_toast_notification("Live Recording Notifications",
                                                    channelClass.channel_name + " is live and is now "
                                                                                "recording. \n"
                                                                                "Recording at "
                                                    + YoutubeStream['stream_resolution'] +
                                                    ("\n[SPONSOR STREAM]" if channelClass.sponsor_only_stream else ''))
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
        stopped("Unsupported version of Python. You need Version 3 :<")

    video_info_website = download_website(
        'https://www.youtube.com/get_video_info?video_id={0}'.format(channelInfo.video_id))
    if video_info_website is None:
        return video_info_website
    video_info = parse_qs(video_info_website)
    player_response = parse_json(try_get(video_info, lambda x: x['player_response'][0], str))

    if player_response:
        if "streamingData" not in player_response:
            warning("No StreamingData, Youtube bugged out!")
            return None
        manifest_url = str(try_get(player_response, lambda x: x['streamingData']['hlsManifestUrl'], str))
        if not manifest_url:
            warning("Unable to find Manifest URL.")
            return None
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
    return None
