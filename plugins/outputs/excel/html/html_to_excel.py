from functools import cached_property
import html.parser

from .text import Text
from .hyperlink import HyperLink

class HtmlToExcel(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = [ ]

    def parse(self, text):
        self.reset()
        self.feed(text)
        self.close()
        return self

    @property
    def is_empty(self):
        return len(self.nodes) == 0

    @property
    def last_node(self):
        return self.nodes[-1]

    def add_node(self, node):
        self.nodes.append(node)

    def append_to_last(self, text):
        self.last_node.append(text)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = next(attr[1] for attr in attrs if attr[0] == 'href')
            self.add_node(HyperLink(href))

    def handle_endtag(self, tag):
        self.last_node.close()

    def handle_data(self, data):
        stripped = ' '.join(data.split())
        if len(stripped) > 0:
            if self.is_empty or self.last_node.is_closed:
                self.add_node(Text(stripped))
            else:
                self.append_to_last(stripped)

    @cached_property
    def rendered(self):
        return '\n'.join(seg.rendered for seg in self.nodes if not seg.is_empty)
