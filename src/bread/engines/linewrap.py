import textwrap
from dataclasses import dataclass
from typing import Any, Callable

from bread.app.commands import (
    Command,
    GoTo,
    PageLines,
    ScrollLines,
    ScrollToEnd,
    ScrollToStart,
)
from bread.app.state import ReaderState, ReadMode
from bread.domain.ir import Block, BlockType, flatten_block_text
from bread.domain.model import DocumentPosition
from bread.engines.core import LayoutEngine


@dataclass(frozen=True)
class WrappedLine:
    text: str
    position: DocumentPosition


class LineWrappingLayoutEngine(LayoutEngine):
    mode: ReadMode = ReadMode.NORMAL

    def __init__(self, get_blocks_for_spine: Callable[[int], list[Block]]) -> None:
        super().__init__(get_blocks_for_spine)

        self._cache_spine_index: int | None = None
        self._cache_width: int | None = None
        self._block_wrapped_lines: list[list[str]] = []
        self._block_line_offsets: list[list[int]] = []
        self._block_prefix_line_counts: list[int] = []
        self._total_lines: int = 0

        self._top_line: int = 0
        # The canonical DocPos to restore _top_line from after every cache rebuild.
        # Updated by seek_to and after every scroll command.
        self._scroll_anchor: DocumentPosition = DocumentPosition(0, 0, 0, 0)

    @property
    def top_line(self) -> int:
        return self._top_line

    @top_line.setter
    def top_line(self, value: int) -> None:
        self._top_line = max(0, value)

    def set_viewport(self, width: int, height: int) -> None:
        self._viewport_width = max(20, width)
        self._viewport_height = max(1, height)

        if self._cache_width != self._viewport_width:
            self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        self._cache_spine_index = None
        self._cache_width = None
        self._block_wrapped_lines = []
        self._block_line_offsets = []
        self._block_prefix_line_counts = []
        self._total_lines = 0

    def _ensure_cache(self, spine_index: int) -> None:
        if (
            self._cache_spine_index == spine_index
            and self._cache_width == self._viewport_width
        ):
            return

        blocks = self._get_blocks_for_spine(spine_index)

        wrapped_lines: list[list[str]] = []
        line_offsets: list[list[int]] = []
        prefix: list[int] = []

        running = 0
        for block in blocks:
            block_lines, offsets = self._wrap_block(block)
            wrapped_lines.append(block_lines)
            line_offsets.append(offsets)

            running += len(block_lines) + 1
            prefix.append(running)

        self._cache_spine_index = spine_index
        self._cache_width = self._viewport_width
        self._block_wrapped_lines = wrapped_lines
        self._block_line_offsets = line_offsets
        self._block_prefix_line_counts = prefix
        self._total_lines = running if running > 0 else 1

        # Always recompute _top_line from the scroll anchor using the fresh layout.
        # This makes seek_to and resize both correct regardless of timing.
        if self._scroll_anchor.spine == spine_index:
            self._top_line = self._compute_top_line(self._scroll_anchor)
        else:
            self._top_line = 0

    def _wrap_block(self, block: Block) -> tuple[list[str], list[int]]:
        width = max(self._viewport_width, 20)
        text = flatten_block_text(block)

        if block.type == BlockType.PRE:
            raw_lines = text.splitlines() or [""]
            wrapped: list[str] = []
            offsets: list[int] = []
            cursor = 0
            for line in raw_lines:
                parts = textwrap.wrap(line, width=width) or [""]
                scan = 0
                for part in parts:
                    idx = line.find(part, scan)
                    if idx < 0:
                        idx = scan
                    offsets.append(cursor + idx)
                    wrapped.append(part)
                    scan = idx + len(part)
                cursor += len(line) + 1
            return wrapped, offsets

        text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
        while "  " in text:
            text = text.replace("  ", " ")

        wrapped = textwrap.wrap(text, width=width) or [""]

        offsets: list[int] = []
        scan = 0
        for line in wrapped:
            idx = text.find(line, scan)
            if idx < 0:
                idx = scan
            offsets.append(idx)
            scan = idx + len(line)

        return wrapped, offsets


    def get_total_wrapped_lines(self, state: ReaderState) -> int:
        self._ensure_cache(state.position.spine)
        return self._total_lines

    def get_wrapped_line(self, state: ReaderState, global_line_index: int) -> WrappedLine:
        self._ensure_cache(state.position.spine)

        if global_line_index < 0:
            global_line_index = 0
        if global_line_index >= self._total_lines:
            global_line_index = self._total_lines - 1

        block_index = 0
        while (
            block_index < len(self._block_prefix_line_counts)
            and global_line_index >= self._block_prefix_line_counts[block_index]
        ):
            block_index += 1

        if block_index >= len(self._block_prefix_line_counts):
            return WrappedLine("", state.position)

        block_start = self._block_prefix_line_counts[block_index - 1] if block_index > 0 else 0
        local = global_line_index - block_start

        lines = self._block_wrapped_lines[block_index]
        offsets = self._block_line_offsets[block_index]

        if local == len(lines):
            return WrappedLine(
                "",
                DocumentPosition(
                    spine=state.position.spine,
                    block=block_index,
                    span=0,
                    offset=0,
                ),
            )

        local = max(0, min(local, len(lines) - 1))
        offset_in_block_text = offsets[local] if local < len(offsets) else 0

        return WrappedLine(
            lines[local],
            DocumentPosition(
                spine=state.position.spine,
                block=block_index,
                span=0,
                offset=offset_in_block_text,
            ),
        )

    def _compute_top_line(self, position: DocumentPosition) -> int:
        """Compute _top_line from a DocPos using already-built cache data.
        Safe to call from within _ensure_cache (does NOT call _ensure_cache).
        """
        if position.block <= 0 or not self._block_prefix_line_counts:
            return 0
        idx = min(position.block - 1, len(self._block_prefix_line_counts) - 1)
        line = self._block_prefix_line_counts[idx]
        max_top = max(0, self._total_lines - self._viewport_height)
        return min(line, max_top)

    def _set_top_line(self, line: int, state: ReaderState) -> DocumentPosition:
        """Set _top_line and sync _scroll_anchor. Returns new DocPos."""
        self._top_line = line
        pos = self.get_wrapped_line(state, self._top_line).position
        self._scroll_anchor = pos
        return pos

    def apply(self, state: ReaderState, command: Command) -> ReaderState:
        self._ensure_cache(state.position.spine)
        new_state = ReaderState(**state.__dict__)

        if isinstance(command, GoTo):
            new_pos = command.position.clamp_non_negative()
            self._scroll_anchor = new_pos
            self._top_line = self._compute_top_line(new_pos)
            new_state.position = new_pos
            return new_state

        if isinstance(command, ScrollLines):
            max_top = max(0, self._total_lines - self._viewport_height)
            new_state.position = self._set_top_line(
                max(0, min(self._top_line + command.delta, max_top)), state
            )
            return new_state

        if isinstance(command, PageLines):
            max_top = max(0, self._total_lines - self._viewport_height)
            delta = command.pages * self._viewport_height
            new_state.position = self._set_top_line(
                max(0, min(self._top_line + delta, max_top)), state
            )
            return new_state

        if isinstance(command, ScrollToStart):
            new_state.position = self._set_top_line(0, state)
            return new_state

        if isinstance(command, ScrollToEnd):
            new_state.position = self._set_top_line(
                max(0, self._total_lines - self._viewport_height), state
            )
            return new_state

        return state

    def total_lines(self, state: ReaderState) -> int:
        return self.get_total_wrapped_lines(state)

    def line_at(self, state: ReaderState, i: int) -> str:
        return self.get_wrapped_line(state, i).text

    def current_position(self, state: ReaderState) -> DocumentPosition:
        """True current position based on _top_line, not stale state.position."""
        self._ensure_cache(state.position.spine)
        return self.get_wrapped_line(state, self._top_line).position

    def seek_to(self, position: DocumentPosition) -> DocumentPosition:
        self._scroll_anchor = position
        # Eagerly update _top_line if the cache is already valid for this spine.
        # If not, _ensure_cache will recompute it from _scroll_anchor on rebuild.
        if (
            self._cache_spine_index == position.spine
            and self._cache_width == self._viewport_width
        ):
            self._top_line = self._compute_top_line(position)
        return position
