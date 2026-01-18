from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import CenterMiddle
from textual.widgets import Footer, Header, ProgressBar

from bread.app.controller import ReaderController
from bread.app.state import ReadMode
from bread.domain.model import DocumentPosition
from bread.ui.views.line_view import LineReaderViewWidget

# You'll provide a NORMAL engine implementing LayoutEngine that returns a NormalLineSlice
# from slice(state). We'll show how to pass it in cleanly.


class BreadReaderApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("j", "down", "Down"),
        ("k", "up", "Up"),
        ("f", "page_down", "Page Down"),
        ("b", "page_up", "Page Up"),
        ("g", "top", "Top"),
        ("G", "bottom", "Bottom"),
    ]

    def __init__(self, controller: ReaderController) -> None:
        super().__init__()
        self.controller = controller

        self.reader = LineReaderViewWidget(controller=self.controller)
        self.progress = ProgressBar(total=100, show_eta=False, show_percentage=True)

    def compose(self) -> ComposeResult:
        yield Header()
        with CenterMiddle():
            yield self.progress
            yield self.reader
        yield Footer()

    def on_mount(self) -> None:
        # Ensure the controller knows actual viewport
        self.controller.set_viewport(self.reader.size.width, self.reader.size.height)
        self.reader._sync_virtual_size()  # internal, but fine for MVP
        self.progress.update(progress=self.reader.progress_percent(), total=100)

    # ---- actions ----

    def action_down(self) -> None:
        self.reader.scroll_by(1)

    def action_up(self) -> None:
        self.reader.scroll_by(-1)

    def action_page_down(self) -> None:
        self.reader.page_by(+1)

    def action_page_up(self) -> None:
        self.reader.page_by(-1)

    def action_top(self) -> None:
        self.reader.scroll_to_top()

    def action_bottom(self) -> None:
        self.reader.scroll_to_bottom()

    # ---- progress messages ----

    def on_line_reader_view_widget_progress_changed(
        self, message: LineReaderViewWidget.ProgressChanged
    ) -> None:
        self.progress.update(progress=message.percent, total=100)
