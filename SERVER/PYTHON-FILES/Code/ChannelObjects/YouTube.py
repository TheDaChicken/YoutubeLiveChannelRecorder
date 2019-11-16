from Code.ChannelObjects import TemplateChannel
from utils.web import download_website


class YouTube(TemplateChannel):
    platform_name = "YOUTUBE"

    # VIDEO DETAILS
    video_id = None

    def __init__(self, channel_id):
        self.channel_id = channel_id

    def loadVideoData(self, video_id):
        if video_id is not None:
            website_string = download_website("https://www.youtube.com/watch?v={0}".
                                              format(video_id))
            self.video_id = video_id
        else:
            website_string = download_website("https://www.youtube.com/channel/{0}/live".
                                              format(self.channel_id))
        if website_string is None:
            return [False, "Failed getting Youtube Data from the internet! "
                           "This means there is no good internet available!"]
        if website_string == 404:
            return [False, "Failed getting Youtube Data! \"{0}\" doesn't exist as a channel id!".format(
                self.channel_id)]
