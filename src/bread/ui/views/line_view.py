from __future__ import annotations

from functools import wraps

from rich.segment import Segment
from textual.events import Resize
from textual.geometry import Size
from textual.message import Message
from textual.strip import Strip
from textual.widget import Widget

from bread.app.commands import PageLines, ScrollLines, ScrollToEnd, ScrollToStart
from bread.app.controller import ReaderController
from bread.engines.linewrap import LineWrappingLayoutEngine
from bread.ui.views.core import CoreReaderView


def notify_progress(func):
    """Decorator to notify progress after scrolling actions."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self._notify_progress()
        return result
    return wrapper


class LineReaderViewWidget(CoreReaderView[LineWrappingLayoutEngine]):
    """
    NORMAL-mode view widget (Widget + Line API).

    - Uses controller.current_slice() to fetch line data.
    - Maintains virtual_size so Textual has correct scroll ranges.
    - Uses controller.state.top_line_hint as the "top visible line".
    - Scroll actions dispatch Commands (ScrollLines/PageLines) to the controller.
    """

    DEFAULT_CSS = """
    LineReaderViewWidget {
        width: 80%;
        max-width: 100;
        height: 1fr;

        padding: 0 0;
        margin: 0 0;

        background: $background;
        color: $foreground;
    }
    """

    class ProgressChanged(Message):
        def __init__(self, sender: Widget, percent: int) -> None:
            super().__init__()
            self.set_sender(sender)
            self.percent = percent

    def __init__(self, controller: ReaderController, *args, **kwargs) -> None:
        super().__init__(
            controller=controller,
            engine=controller.normal_engine,
            *args,
            **kwargs,
        )

        self.show_vertical_scrollbar = False
        self.show_horizontal_scrollbar = False

        # Must be non-zero; updated on mount/resize/scroll_to_bottom.
        self.virtual_size = Size(1, 1)

    def _content_width(self) -> int:
        return max(self.size.width, 20)

    def _sync_virtual_size(self) -> None:
        w = self._content_width()
        total = max(int(self.engine.total_lines(self.controller.state)), 1)
        self.virtual_size = Size(w, total)

    def _notify_progress(self) -> None:
        self.post_message(self.ProgressChanged(self, self.progress_percent()))

    @notify_progress
    def on_mount(self) -> None:
        # Make engines aware of actual widget viewport
        self.controller.set_viewport(self._content_width(), self.size.height)
        self._sync_virtual_size()
        self.refresh()

    @notify_progress
    def on_resize(self, _: Resize) -> None:
        self.controller.set_viewport(self._content_width(), self.size.height)
        self._sync_virtual_size()
        self.refresh()

    @notify_progress
    def scroll_by(self, dy: int) -> None:
        self.controller.dispatch(ScrollLines(dy))
        self._sync_virtual_size()
        self.refresh()

    @notify_progress
    def page_by(self, pages: int) -> None:
        self.controller.dispatch(PageLines(pages))
        self._sync_virtual_size()
        self.refresh()

    @notify_progress
    def scroll_to_top(self) -> None:
        self.controller.dispatch(ScrollToStart())
        self._sync_virtual_size()
        self.refresh()

    @notify_progress
    def scroll_to_bottom(self) -> None:
        self.controller.dispatch(ScrollToEnd())
        self._sync_virtual_size()
        self.refresh()

    def progress_percent(self) -> int:
        return int(self.controller.get_global_progress() * 100)

    def render_line(self, y: int) -> Strip:
        global_line_index = self.engine.top_line + y
        line = self.engine.line_at(self.controller.state, global_line_index) or ""

        width = self.size.width
        if len(line) < width:
            line = line + (" " * (width - len(line)))
        else:
            line = line[:width]

        return Strip([Segment(line, self.rich_style)], cell_length=width)
