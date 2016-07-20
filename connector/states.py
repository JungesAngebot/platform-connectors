from abc import ABCMeta, abstractmethod


class State(metaclass=ABCMeta):
    """ Basic state class.
    The class offers only the run method for a state. This method is commonly used by every
    state of the state machine.
    """
    @abstractmethod
    def run(self):
        pass


class BasicState(metaclass=ABCMeta, State):
    """ Actual working state of the state machine.
    This type of state is ether a final state or an intermediate state.
    """
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
