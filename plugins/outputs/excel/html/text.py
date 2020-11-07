from .base_segment import BaseSegment

class Text(BaseSegment):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def append(self, text):
        self.text += text

    @property
    def is_empty(self):
        return len(self.text) == 0

    @property
    def rendered(self):
        return self.text
