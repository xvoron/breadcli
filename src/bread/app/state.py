from dataclasses import dataclass
from enum import Enum

from bread.domain.model import DocumentPosition


class ReadMode(Enum):
    NORMAL = "normal"
    RSVP = "rsvp"


@dataclass
class ReaderState:
    position: DocumentPosition
    mode: ReadMode

    wpm: int = 300
    playing: bool = False
