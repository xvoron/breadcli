from abc import ABC, abstractmethod
from typing import Any, Callable

from bread.app.commands import Command, ToggleMode
from bread.app.state import ReaderState, ReadMode
from bread.domain.ir import Block
from bread.domain.model import DocumentPosition


class LayoutEngine(ABC):
    mode: ReadMode

    def __init__(self, get_blocks_for_spine: Callable[[int], list[Block]]) -> None:
        self._get_blocks_for_spine = get_blocks_for_spine

        self._viewport_width = 80
        self._viewport_height = 24

    @abstractmethod
    def set_viewport(self, width: int, height: int) -> None:
        pass

    @abstractmethod
    def apply(self, state: ReaderState, command: Command) -> ReaderState:
        pass

    @abstractmethod
    def slice(self, state: ReaderState) -> Any:
        pass


class ReaderController:
    def __init__(
        self,
        initial_position: DocumentPosition,
        engines: dict[ReadMode, LayoutEngine]
    ) -> None:
        self.state = ReaderState(
            position=initial_position,
            mode = ReadMode.NORMAL
        )
        self.engines = engines
        self.viewport_width = 80
        self.viewport_height = 24

        for engine in self.engines.values():
            engine.set_viewport(self.viewport_width, self.viewport_height)

    def set_viewport(self, width: int, height: int) -> None:
        self.viewport_width = max(20, width)
        self.viewport_height = max(1, height)

        for engine in self.engines.values():
            engine.set_viewport(width, height)

    def dispatch(self, cmd: Command) -> None:
        if isinstance(cmd, ToggleMode):
            self._toggle_mode()
            return

        engine = self.engines[self.state.mode]

        new_state = engine.apply(self.state, cmd)
        new_state.position = new_state.position.clamp_non_negative()

        self.state = new_state

    def _toggle_mode(self) -> None:
        self.state.playing = False
        self.state.mode = (
            ReadMode.RSVP
            if self.state.mode == ReadMode.NORMAL
            else ReadMode.NORMAL
        )

    def current_slice(self) -> Any:
        return self.engines[self.state.mode].slice(self.state)
