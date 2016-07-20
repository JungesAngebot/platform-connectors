class DownloadingError:
    def run(self):
        pass


class Downloading:

    def __init__(self):
        self.error_state = DownloadingError
        self.next_state = Uploading

    def _next_state(self, video):
        self.next_state().run(None)

    def run(self):
        pass

    def on_error(self):
        self.error_state().run()


class Uploading:
    def run(self, video):
        pass
