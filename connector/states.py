from abc import ABCMeta


class State(metaclass=ABCMeta):
    def __init__(self):
        self.prev_state = None
        self.following_states = []
