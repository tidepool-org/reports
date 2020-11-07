class BaseSegment():
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True

    @property
    def is_closed(self):
        return self.closed

    @property
    def is_empty(self):
        pass
