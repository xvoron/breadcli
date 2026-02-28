from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import CenterMiddle
from textual.screen import Screen
from textual.widgets import Footer, Header, ProgressBar, Static

from bread.ui.views.rsvp import RSVPReaderViewWidget


class RSVPScreen(Screen):
    BINDINGS = [
        ("q", "app.quit", "Quit"),
        ("m", "toggle_mode", "Mode"),
        ("space", "toggle_play", "Play/Pause"),
        ("h", "slower", "Slower"),
        ("l", "faster", "Faster"),
    ]

    def compose(self) -> ComposeResult:
        self.stats = Static(id="stats")
        self.rsvp_progress = ProgressBar(total=100, show_eta=False, id="rsvp_progress")

        yield Header()
        with CenterMiddle():
            yield RSVPReaderViewWidget(controller=self.app.controller, id="rsvp")
            yield self.stats
            yield self.rsvp_progress
        yield Footer()

    def on_mount(self) -> None:
        rsvp = self.query_one("#rsvp", RSVPReaderViewWidget)
        self.app.controller.set_viewport(rsvp.size.width, rsvp.size.height)
        rsvp.sync_from_state()

        progress = rsvp.progress_percent()
        self.rsvp_progress.update(progress=progress, total=100)

    def on_rsvp_reader_view_widget_ticked(self, _: RSVPReaderViewWidget.Ticked) -> None:
        state = self.app.controller.state
        self.stats.update(f"{state.wpm} WPM")

        rsvp = self.query_one("#rsvp", RSVPReaderViewWidget)
        progress = rsvp.progress_percent()
        self.rsvp_progress.update(progress=progress, total=100)

    def action_toggle_mode(self) -> None:
        self.app.action_toggle_mode()

    def action_toggle_play(self) -> None:
        self.app.action_toggle_play()

    def action_slower(self) -> None:
        self.app.action_slower()

    def action_faster(self) -> None:
        self.app.action_faster()
