class SharableHandler:
    def get(self, variable_name):
        try:
            return getattr(self, variable_name)
        except AttributeError:
            return None

    def set(self, variable_name, value):
        return setattr(self, variable_name, value)


class TemplateChannel(SharableHandler):
    EncoderClass = None

    def close_recording(self):
        if self.EncoderClass:
            self.EncoderClass.stop_recording()
