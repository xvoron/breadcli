
from typing import Any

from bread.app.commands import Command, ToggleMode
from bread.app.controller import LayoutEngine, ReaderController
from bread.app.state import ReaderState, ReadMode
from bread.domain.model import DocumentPosition


class DummyEngine(LayoutEngine):
    def __init__(self, mode):
        self.mode = mode
    def set_viewport(self, width: int, height: int) -> None:
        pass

    def apply(self, state: ReaderState, command: Command) -> ReaderState:
        return state

    def slice(self, state: ReaderState) -> Any:
        return None


def test_toggle_mode():
    ctrl = ReaderController(
        initial_position=DocumentPosition(0, 0, 0, 0),
        engines={
            ReadMode.NORMAL: DummyEngine("normal"),
            ReadMode.RSVP: DummyEngine("rsvp"),
            }
    )

    assert ctrl.state.mode == ReadMode.NORMAL
    ctrl.dispatch(ToggleMode())
    assert ctrl.state.mode == ReadMode.RSVP

