from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Mapping


class BlockType(Enum):
    P = "p"
    H1 = "h1"
    H2 = "h2"
    H3 = "h3"
    H4 = "h4"
    H5 = "h5"
    PRE = "pre"
    IMG = "img"
    TABLE = "table"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Span:
    text: str
    marks: FrozenSet[str] = frozenset()
    href: str | None = None


@dataclass(frozen=True)
class Block:
    type: BlockType
    inlines: tuple[Span, ...] = ()
    attrs: Mapping[str, str] = field(default_factory=dict)


def flatten_block_text(block: Block) -> str:
    if block.type in (BlockType.IMG, BlockType.TABLE):
        return f"[{block.type.value.upper()}]"

    if block.type == BlockType.PRE:
        return "".join((span.text for span in block.inlines))

    return "".join((span.text for span in block.inlines))
