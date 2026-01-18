from bread.domain.model import DocumentPosition

from dataclasses import dataclass
from enum import Enum


class ReadMode(Enum):
    NORMAL = "normal"
    RSVP = "rsvp"


@dataclass
class ReaderState:
    position: DocumentPosition
    mode: ReadMode

    wpm: int = 300
    playing: bool = False

    top_line_hint: int = 0
