from pathlib import Path

from bread.app.controller import ReaderController
from bread.app.state import ReadMode
from bread.domain.model import DocumentPosition
from bread.engines.linewrap import LineWrappingLayoutEngine
from bread.engines.rsvp import RSVPLayoutEngine
from bread.epub.book import EpubBook
from bread.parsing.html_to_ir import parse_html_to_ir
from bread.ui.app import BreadReaderApp

book = EpubBook(Path("./assets/test.epub"))

def get_blocks(spine_index: int):
    html = book.read_chapter_html(spine_index)
    return parse_html_to_ir(html)

engine_normal = LineWrappingLayoutEngine(get_blocks)
engine_rsvp = RSVPLayoutEngine(get_blocks)


controller = ReaderController(
    initial_position=DocumentPosition(spine=5, block=0, span=0, offset=0),
    engines={
        ReadMode.NORMAL: engine_normal,
        ReadMode.RSVP: engine_rsvp,
     },
)


if __name__ == "__main__":

    app = BreadReaderApp(controller)
    app.run()

