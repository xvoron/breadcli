from dataclasses import dataclass

from bread.domain.model import DocumentPosition


@dataclass(frozen=True)
class Command:
    pass


@dataclass(frozen=True)
class ScrollLines(Command):
    delta: int

@dataclass(frozen=True)
class ScrollToStart(Command):
    pass


@dataclass(frozen=True)
class ScrollToEnd(Command):
    pass


@dataclass(frozen=True)
class PageLines(Command):
    pages: int


@dataclass(frozen=True)
class GoTo(Command):
    position: DocumentPosition


@dataclass(frozen=True)
class ToggleMode(Command):
    pass


@dataclass(frozen=True)
class RSVPNext(Command):
    delta: int


@dataclass(frozen=True)
class TogglePlay(Command):
    pass


@dataclass(frozen=True)
class SetWPM(Command):
    wpm: int
