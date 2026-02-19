import bisect
import re
from dataclasses import dataclass
from typing import Any, Callable

from bread.app.commands import Command, GoTo, RSVPNext, SetWPM, TogglePlay
from bread.app.controller import LayoutEngine
from bread.app.state import ReaderState, ReadMode
from bread.domain.ir import Block, BlockType
from bread.domain.model import DocumentPosition


@dataclass(frozen=True)
class RSVPToken:
    text: str
    marks: frozenset[str]
    position: DocumentPosition


_OPEN = r"""["'“‘(\[{<]"""
_CLOSE = r"""[.,!?;:…]+|["'”’)\]}>]+"""
_WORD_CORE = r"""[^\W_]+"""
_WORD = rf"""{_WORD_CORE}(?:[’']+{_WORD_CORE})*(?:-{_WORD_CORE}(?:[’']+{_WORD_CORE})*)*"""

_TOKEN_RE = re.compile(
    rf"""
    (?:{_OPEN})*     # opening punctuation attached to the word
    {_WORD}          # core word (Unicode)
    (?:{_CLOSE})*    # closing punctuation attached to the word
    """,
    re.VERBOSE,
)


class RSVPLayoutEngine(LayoutEngine):
    mode: ReadMode = ReadMode.RSVP

    def __init__(self, get_blocks_for_spine: Callable[[int], list[Block]]) -> None:
        super().__init__(get_blocks_for_spine)

        self._cache_spine_index: int | None = None
        self._cache_tokens: list[RSVPToken] = []

    def set_viewport(self, width: int, height: int) -> None:
        self._viewport_width = max(20, width)
        self._viewport_height = max(1, height)

    def _ensure_tokens(self, spine: int) -> None:
        if self._cache_spine_index == spine:
            return
        blocks = self._get_blocks_for_spine(spine)
        tokens: list[RSVPToken] = []
        for block_idx, block in enumerate(blocks):
            if block.type in (BlockType.IMG, BlockType.TABLE, BlockType.PRE):
                tokens.append(RSVPToken(
                    text=f"[{block.type.value.upper()}]",
                    marks=frozenset(),
                    position=DocumentPosition(
                        spine=spine,
                        block=block_idx,
                        span=0,
                        offset=0,
                    ),
                ))
                continue
            for span_idx, span in enumerate(block.inlines):
                for match in _TOKEN_RE.finditer(span.text):
                    tokens.append(RSVPToken(
                        text=match.group(),
                        marks=span.marks,
                        position=DocumentPosition(
                            spine=spine,
                            block=block_idx,
                            span=span_idx,
                            offset=match.start(),
                        ),
                    ))
        self._cache_spine_index = spine
        self._cache_tokens = tokens or [
            RSVPToken(
                text="", marks=frozenset(), position=DocumentPosition(spine, 0, 0, 0)
            )
        ]

    def apply(self, state: ReaderState, command: Command) -> ReaderState:
        self._ensure_tokens(state.position.spine)

        new_state = ReaderState(**state.__dict__)
        if isinstance(command, GoTo):
            new_state.position = command.position.clamp_non_negative()
            return new_state

        if isinstance(command, TogglePlay):
            new_state.playing = not new_state.playing
            return new_state

        if isinstance(command, SetWPM):
            new_state.wpm = max(50, min(2000, command.wpm))
            return new_state

        if isinstance(command, RSVPNext):
            n = len(self._cache_tokens)
            if n == 0:
                return new_state

            current_idx = self._token_idx_for(state)
            new_idx = max(0, min(current_idx + command.delta, n - 1))
            new_state.position = self._cache_tokens[new_idx].position
            return new_state
        return new_state

    def _token_idx_for(self, state: ReaderState) -> int:
        """Find the index of the current token based on the state's position.

        So state position offset is character offset, but we want to move by token, so we need to
        find the current token index first.
        """
        keys = [t.position for t in self._cache_tokens]
        idx = bisect.bisect_right(keys, state.position) - 1
        return max(0, idx)

    def slice(self, state: ReaderState) -> Any:
        self._ensure_tokens(state.position.spine)
        return self

    def token_at(self, state: ReaderState) -> str:
        self._ensure_tokens(state.position.spine)
        idx = self._token_idx_for(state)
        return self._cache_tokens[idx].text

    def current_token(self, state: ReaderState) -> str:
        return self.token_at(state)

    def current_position(self, state: ReaderState) -> DocumentPosition:
        """True current position: the token the engine is actually on."""
        self._ensure_tokens(state.position.spine)
        idx = self._token_idx_for(state)
        return self._cache_tokens[idx].position

    def seek_to(self, position: DocumentPosition) -> DocumentPosition:
        self._ensure_tokens(position.spine)
        for token in self._cache_tokens:
            if token.position >= position:
                return token.position
        return self._cache_tokens[-1].position
