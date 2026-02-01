from __future__ import annotations

from textual.app import App

from bread.app.commands import SetWPM, ToggleMode, TogglePlay
from bread.app.controller import ReaderController
from bread.app.state import ReadMode

from bread.ui.screens.normal import NormalScreen
from bread.ui.screens.rsvp import RSVPScreen


class BreadReaderApp(App):
    def __init__(self, controller: ReaderController) -> None:
        super().__init__()
        self.controller = controller

    def on_mount(self) -> None:
        # Start in NORMAL mode
        self.push_screen(NormalScreen())

    def action_toggle_mode(self) -> None:
        self.controller.dispatch(ToggleMode())
        if self.controller.state.mode == ReadMode.RSVP:
            self.switch_screen(RSVPScreen())
        else:
            self.switch_screen(NormalScreen())

    def action_toggle_play(self) -> None:
        if self.controller.state.mode != ReadMode.RSVP:
            return
        self.controller.dispatch(TogglePlay())
        # Let the RSVP screen/widget update itself if it exists
        screen = self.screen
        if screen.query("#rsvp"):
            screen.query_one("#rsvp").sync_from_state()

    def action_slower(self) -> None:
        if self.controller.state.mode != ReadMode.RSVP:
            return
        self.controller.dispatch(SetWPM(self.controller.state.wpm - 25))
        if self.screen.query("#rsvp"):
            self.screen.query_one("#rsvp").sync_from_state()

    def action_faster(self) -> None:
        if self.controller.state.mode != ReadMode.RSVP:
            return
        self.controller.dispatch(SetWPM(self.controller.state.wpm + 25))
        if self.screen.query("#rsvp"):
            self.screen.query_one("#rsvp").sync_from_state()
