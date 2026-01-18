from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentPosition:
    spine: int
    block: int
    span: int
    offset: int

    def clamp_non_negative(self) -> DocumentPosition:
        return DocumentPosition(
            spine=max(0, self.spine),
            block=max(0, self.block),
            span=max(0, self.span),
            offset=max(0, self.offset),
        )

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.spine, self.block, self.span, self.offset)

    def __lt__(self, other: DocumentPosition) -> bool:
        return self.as_tuple() < other.as_tuple()

    def __le__(self, other: DocumentPosition) -> bool:
        return self.as_tuple() <= other.as_tuple()


@dataclass(frozen=True)
class DocumentSpan:
    start: DocumentPosition
    end: DocumentPosition

    def normalized(self) -> DocumentSpan:
        return self if self.start <= self.end else DocumentSpan(self.end, self.start)
