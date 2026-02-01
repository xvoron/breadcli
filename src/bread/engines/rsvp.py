import re
from typing import Any, Callable

from bread.app.commands import Command, GoTo, RSVPNext, SetWPM, TogglePlay
from bread.app.controller import LayoutEngine
from bread.app.state import ReaderState, ReadMode
from bread.domain.ir import Block, BlockType
from bread.domain.model import DocumentPosition


def _flattent_blocks_to_text(blocks: list[Block]) -> str:
    parts: list[str] = []
    for b in blocks:
        if b.type in (BlockType.IMG, BlockType.TABLE):
            parts.append(f"[{b.type.value.upper()}]")
            parts.append("\n")
            continue
        if b.type == BlockType.PRE:
            parts.append("".join(s.text for s in b.inlines))
            parts.append("\n")
            continue
        parts.append("".join(s.text for s in b.inlines))
        parts.append("\n")
    return "".join(parts)


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

def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


class RSVPLayoutEngine(LayoutEngine):
    mode: ReadMode = ReadMode.RSVP

    def __init__(self, get_blocks_for_spine: Callable[[int], list[Block]]) -> None:
        self._get_blocks_for_spine = get_blocks_for_spine

        self._viewport_width = 80
        self._viewport_height = 24

        self._cache_spine_index: int | None = None
        self._cache_tokens: list[str] = []

    def set_viewport(self, width: int, height: int) -> None:
        self._viewport_width = max(20, width)
        self._viewport_height = max(1, height)

    def _ensure_tokens(self, spine: int) -> None:
        if self._cache_spine_index == spine and self._cache_tokens:
            return
        blocks = self._get_blocks_for_spine(spine)
        text = _flattent_blocks_to_text(blocks)
        self._cache_tokens = tokenize(text)
        if not self._cache_tokens:
            self._cache_tokens = [""]  # Ensure at least one token
        self._cache_spine_index = spine

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

            idx = max(0, min(new_state.position.offset + command.delta, n - 1))
            new_state.position = DocumentPosition(
                spine=state.position.spine,
                block=0,
                span=0,
                offset=idx,
            )
            return new_state
        return new_state

    def slice(self, state: ReaderState) -> Any:
        self._ensure_tokens(state.position.spine)
        return self

    def token_at(self, state: ReaderState, idx: int) -> str:
        self._ensure_tokens(state.position.spine)
        if not self._cache_tokens:
            return ""
        idx = max(0, min(idx, len(self._cache_tokens) - 1))
        return self._cache_tokens[idx]

    def current_token(self, state: ReaderState) -> str:
        return self.token_at(state, state.position.offset)
