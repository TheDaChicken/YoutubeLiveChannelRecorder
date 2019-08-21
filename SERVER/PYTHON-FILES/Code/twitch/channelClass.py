from ..template.template_channelClass import ChannelInfo_template
from ..utils.web import download_website


class ChannelInfoTwitch(ChannelInfo_template):

    def __init__(self, channel_name, SharedVariables=None, cachedDataHandler=None, queue_holder=None):
        # TWITCH ONLY GOES BY CHANNEL NAME. NOT CHANNEL ID.
        self.channel_name = channel_name
        super().__init__(None, SharedVariables, cachedDataHandler, queue_holder)

    def loadVideoData(self):
        website_string = download_website('https://twitch.tv/{0}'.format(self.channel_name))
        if website_string is None:
            return [False, "Failed getting Twitch Data from the internet! "
                           "This means there is no good internet available!"]
        if website_string == 404:
            return [False, "Failed getting Twitch Data! \"{0}\" doesn't exist as a channel name!".format(
                self.channel_id)]
        with open("test_twitch_page.html", mode="w", encoding="utf8") as f:
            f.write(website_string)
            f.close()

    def start_heartbeat_loop(self):
        pass
