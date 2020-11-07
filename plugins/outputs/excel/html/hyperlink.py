import re
from .base_segment import BaseSegment

class HyperLink(BaseSegment):
    def __init__(self, url, text = None):
        super().__init__()
        self.url = url
        self.text = text

    def append(self, text):
        self.text = text

    @property
    def pretty_link(self):
        text = re.sub(r"""https://docs.google.+""", r"Google Document", self.text)
        return re.sub(r"""https://tidepool.atlassian.net/browse/(.+)""", r"\1", text)

    @property
    def is_empty(self):
        return False

    @property
    def rendered(self):
        return self.pretty_link
