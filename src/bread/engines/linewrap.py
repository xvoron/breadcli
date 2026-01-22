import textwrap
from dataclasses import dataclass
from typing import Callable, Any

from bread.app.commands import Command, GoTo, PageLines, ScrollLines
from bread.app.controller import LayoutEngine
from bread.app.state import ReadMode, ReaderState
from bread.domain.ir import Block, BlockType
from bread.domain.model import DocumentPosition


@dataclass(frozen=True)
class WrappedLine:
    text: str
    position: DocumentPosition


class LineWrappingLayoutEngine(LayoutEngine):
    mode: ReadMode = ReadMode.NORMAL
    def __init__(self, get_blocks_for_spine: Callable[[int], list[Block]]) -> None:
        self._get_blocks_for_spine = get_blocks_for_spine

        self._viewport_width = 80
        self._viewport_height = 24

        self._cache_spine_index: int | None = None
        self._cache_width: int | None = None
        self._block_wrapped_lines: list[list[str]] = []
        self._block_line_offsets: list[list[int]] = []
        self._block_prefix_line_counts: list[int] = []
        self._total_lines: int = 0

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
        if self._cache_spine_index == spine_index and self._cache_width == self._viewport_width:
            return

        blocks = self._get_blocks_for_spine(spine_index)

        wrapped_lines: list[list[str]] = [] # Maybe WrappedLine?
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

    def _wrap_block(self, block: Block) -> tuple[list[str], list[int]]: # Maybe WrappedLine?
        width = max(self._viewport_width, 20)
        text = self._flatten_block_text(block)

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

    def _flatten_block_text(self, block: Block) -> str:
        if block.type in (BlockType.IMG, BlockType.TABLE):
            return f"[{block.type.value.upper()}]"

        if block.type == BlockType.PRE:
            return "".join((span.text for span in block.inlines))

        return "".join((span.text for span in block.inlines))

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

    def apply(self, state: ReaderState, command: Command) -> ReaderState:
        self._ensure_cache(state.position.spine)

        if isinstance(command, GoTo):
            new_state = ReaderState(**state.__dict__)
            new_state.position = command.position.clamp_non_negative()
            return new_state

        if isinstance(command, ScrollLines):
            new_state = ReaderState(**state.__dict__)
            new_state.top_line_hint = max(0, state.top_line_hint + command.delta)

            top_line = new_state.top_line_hint
            new_state.position = self.get_wrapped_line(state, top_line).position
            return new_state

        if isinstance(command, PageLines):
            new_state = ReaderState(**state.__dict__)
            delta = command.pages * self._viewport_height
            new_state.top_line_hint = max(0, state.top_line_hint + delta)

            top_line = new_state.top_line_hint
            new_state.position = self.get_wrapped_line(state, top_line).position
            return new_state

        return state

    def total_lines(self, state: ReaderState) -> int:
        return self.get_total_wrapped_lines(state)

    def line_at(self, state: ReaderState, i: int) -> str:
        return self.get_wrapped_line(state, i).text

    def slice(self, state: ReaderState) -> Any:
        """Return the lines to be displayed in the viewport.

        For NORMAL mode we don't return a precomputed slice; the widget will call
        get_total_wrapped_lines and get_wrapped_line for line-by-line rendering.
        """
        self._ensure_cache(state.position.spine)
        return self
