from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bread.app.commands import Command, PageLines, ScrollLines
from bread.app.controller import LayoutEngine
from bread.app.state import ReaderState, ReadMode


@dataclass
class ModelSlice:
    model: Any

    def total_lines(self) -> int:
        return self.model.total_lines()

    def line_at(self, i: int) -> str:
        return self.model.line_at(i) or ""


class NormalBookModelEngine(LayoutEngine):
    mode = ReadMode.NORMAL

    def __init__(self, model) -> None:
        self.model = model
        self._width = 80
        self._height = 24

    def set_viewport(self, width: int, height: int) -> None:
        self._width = max(20, width)
        self._height = max(1, height)
        self.model.set_width(self._width)

    def apply(self, state: ReaderState, command: Command) -> ReaderState:
        # Expect state.top_line_hint exists
        if isinstance(command, ScrollLines):
            state.top_line_hint = max(0, state.top_line_hint + command.delta)
        elif isinstance(command, PageLines):
            state.top_line_hint = max(0, state.top_line_hint + command.pages * self._height)
        return state

    def slice(self, state: ReaderState):
        return ModelSlice(self.model)
