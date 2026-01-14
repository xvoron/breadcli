from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentPosition:
    spine: int
    block: int
    char: int


@dataclass(frozen=True)
class DocumentSpan:
    start: DocumentPosition
    end: DocumentPosition
