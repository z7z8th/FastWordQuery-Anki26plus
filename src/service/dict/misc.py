import re
import markdown

from ..base import WebService, export, register
from ... import context
from ...context import config

from html.parser import HTMLParser

class HTMLChecker(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = set()

        try:
            self.feed(text)
        except Exception:
            pass

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())

    def handle_endtag(self, tag):
        self.tags.add(tag.lower())

    def has_tag(self, tag: str = None) -> bool:
        # parser = HTMLChecker()

        if tag:
            return tag.lower() in self.tags

        return len(self.tags)


@register([u'杂项', u'Misc'], enabled=True)
class MiscNoteModifier(WebService):
    def __init__(self):
        super().__init__()

    @staticmethod
    def _markdown_to_html(x):
        if not HTMLChecker(x).has_tag('li'):
            x = markdown.markdown(x, extensions=["extra", "tables", "fenced_code"])
        return x    # if ('#' in x or '*' in x) else x

    @export([u'Markdown转成HTML', 'Markdown To HTML'])
    def fld_to_html(self, current_field_value):
        return self._markdown_to_html(current_field_value)
