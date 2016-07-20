from abc import ABCMeta


class State(metaclass=ABCMeta):
    def __init__(self):
        self.prev_state = None
        self.following_states = []
        self.error_state = None


class Notified(State):
    def __init__(self):
        super().__init__()


class DownloadingError(State):
    def __init__(self):
        super().__init__()


class Uploading(State):
    def __init__(self):
        super().__init__()


class Downloading(State):
    def __init__(self):
        super().__init__()
        self.prev_state = Notified
        self.error_state = DownloadingError
        self.following_states = None



