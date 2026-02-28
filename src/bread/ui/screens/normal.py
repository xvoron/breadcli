from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import CenterMiddle
from textual.screen import Screen
from textual.widgets import Footer, Header, ProgressBar, Static

from bread.ui.views.line_view import LineReaderViewWidget


class NormalScreen(Screen):
    BINDINGS = [
        ("q", "app.quit", "Quit"),
        ("j", "down", "Down"),
        ("k", "up", "Up"),
        ("f", "page_down", "Page Down"),
        ("b", "page_up", "Page Up"),
        ("g", "top", "Top"),
        ("G", "bottom", "Bottom"),
        ("m", "toggle_mode", "Mode"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with CenterMiddle():
            yield ProgressBar(id="progress", total=100, show_eta=False, show_percentage=True)
            yield LineReaderViewWidget(controller=self.app.controller, id="reader")
        yield Footer()

    def on_mount(self) -> None:
        reader = self.query_one("#reader", LineReaderViewWidget)
        progress = self.query_one("#progress", ProgressBar)

        self.app.controller.set_viewport(reader.size.width, reader.size.height)
        reader._sync_virtual_size()
        progress.update(progress=reader.progress_percent(), total=100)

    # actions
    def action_down(self) -> None:
        self.query_one("#reader", LineReaderViewWidget).scroll_by(1)

    def action_up(self) -> None:
        self.query_one("#reader", LineReaderViewWidget).scroll_by(-1)

    def action_page_down(self) -> None:
        self.query_one("#reader", LineReaderViewWidget).page_by(+1)

    def action_page_up(self) -> None:
        self.query_one("#reader", LineReaderViewWidget).page_by(-1)

    def action_top(self) -> None:
        self.query_one("#reader", LineReaderViewWidget).scroll_to_top()

    def action_bottom(self) -> None:
        self.query_one("#reader", LineReaderViewWidget).scroll_to_bottom()

    def action_toggle_mode(self) -> None:
        # delegate to app (single place for mode switching)
        self.app.action_toggle_mode()

    # progress message from the view widget
    def on_line_reader_view_widget_progress_changed(
        self, message: LineReaderViewWidget.ProgressChanged
    ) -> None:
        chapter_info = self.app.controller.get_spine_info()
        self.query_one("#progress", ProgressBar).update(progress=message.percent, total=100)

