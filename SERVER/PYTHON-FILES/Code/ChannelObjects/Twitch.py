from Code.ChannelObjects import TemplateChannel


class Twitch(TemplateChannel):
    platform_name = "TWITCH"

    def __init__(self, channel_name):
        self.channel_name = channel_name
