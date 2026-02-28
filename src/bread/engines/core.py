from abc import ABC, abstractmethod
from typing import Any, Callable

from bread.app.commands import Command
from bread.app.state import ReaderState, ReadMode
from bread.domain.ir import Block
from bread.domain.model import DocumentPosition


class LayoutEngine(ABC):
    mode: ReadMode

    def __init__(self, get_blocks_for_spine: Callable[[int], list[Block]]) -> None:
        self._get_blocks_for_spine = get_blocks_for_spine

        self._viewport_width = 80
        self._viewport_height = 24
        self._spine_count = 1

    def set_spine_count(self, count: int) -> None:
        """Set the total number of spines in the document. """
        self._spine_count = count

    @abstractmethod
    def set_viewport(self, width: int, height: int) -> None:
        pass

    @abstractmethod
    def apply(self, state: ReaderState, command: Command) -> ReaderState:
        pass

    @abstractmethod
    def seek_to(self, position: DocumentPosition) -> DocumentPosition:
        pass

    @abstractmethod
    def current_position(self, state: ReaderState) -> DocumentPosition:
        """Return the true current position as known by the engine.

        This may differ from state.position when state.position is stale
        (e.g. before the first command is dispatched after init or mode switch).
        """
        pass
