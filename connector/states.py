from abc import ABCMeta, abstractmethod


class State(metaclass=ABCMeta):

    @abstractmethod
    def run(self):
        pass


class BasicState(metaclass=ABCMeta, State):

    @abstractmethod
    def next_state(self):
        pass

    @abstractmethod
    def error_state(self):
        pass


class ErrorState(metaclass=ABCMeta, State):
    pass


class DownloadingError(ErrorState):
    def run(self):
        pass


class Downloading(BasicState):
    def run(self):
        pass

    def next_state(self):
        pass

    def error_state(self):
        pass
