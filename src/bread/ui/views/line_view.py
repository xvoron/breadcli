from __future__ import annotations

from functools import wraps
from typing import Protocol

from rich.segment import Segment
from textual.events import Resize
from textual.geometry import Size
from textual.message import Message
from textual.strip import Strip
from textual.widget import Widget

from bread.app.commands import PageLines, ScrollLines
from bread.app.controller import ReaderController
from bread.app.state import ReaderState


class NormalLineSlice(Protocol):
    """What the NORMAL layout engine returns from controller.current_slice()."""
    def total_lines(self, state: ReaderState) -> int: ...
    def line_at(self, state: ReaderState, global_line_index: int) -> str: ...


def notify_progress(func):
    """Decorator to notify progress after scrolling actions."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self._notify_progress()
        return result
    return wrapper


class LineReaderViewWidget(Widget):
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
        super().__init__(*args, **kwargs)
        self.controller = controller

        self.show_vertical_scrollbar = False
        self.show_horizontal_scrollbar = False

        # Must be non-zero; updated on mount/resize/scroll_to_bottom.
        self.virtual_size = Size(1, 1)

    def _content_width(self) -> int:
        return max(self.size.width, 20)

    def _get_slice(self) -> NormalLineSlice:
        return self.controller.current_slice()

    def _sync_virtual_size(self) -> None:
        slice_obj = self._get_slice()
        w = self._content_width()
        total = max(int(slice_obj.total_lines(self.controller.state)), 1)
        self.virtual_size = Size(w, total)

        # Clamp top_line_hint to a legal range
        # Note: top_line_hint lives in state; engine updates it too.
        max_top = max(0, total - self.size.height)
        if self.controller.state.top_line_hint > max_top:
            self.controller.state.top_line_hint = max_top
        if self.controller.state.top_line_hint < 0:
            self.controller.state.top_line_hint = 0

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
        # Use dispatch so state stays consistent with engine logic
        # We emulate "go to line 0" as repeated scroll; simplest is to set hint + refresh.
        self.controller.state.top_line_hint = 0
        self._sync_virtual_size()
        self.refresh()

    @notify_progress
    def scroll_to_bottom(self) -> None:
        slice_obj = self._get_slice()
        total = max(int(slice_obj.total_lines(self.controller.state)), 1)
        self.virtual_size = Size(self._content_width(), total)
        self.controller.state.top_line_hint = max(0, total - self.size.height)
        self.refresh()

    def progress_percent(self) -> int:
        slice_obj = self._get_slice()
        total = max(int(slice_obj.total_lines(self.controller.state)), 1)
        max_top = max(1, total - self.size.height)
        return int((self.controller.state.top_line_hint / max_top) * 100)

    def render_line(self, y: int) -> Strip:
        slice_obj = self._get_slice()

        global_line_index = self.controller.state.top_line_hint + y
        line = slice_obj.line_at(self.controller.state, global_line_index) or ""

        width = self.size.width
        if len(line) < width:
            line = line + (" " * (width - len(line)))
        else:
            line = line[:width]

        return Strip([Segment(line, self.rich_style)], cell_length=width)
