# 📘 Bread — Technical Architecture & Roadmap

## Project Goal

Build a terminal-based EPUB reader with:
- multiple reading modes (normal scroll, RSVP, later paging)
- semantic understanding of book structure (HTML → IR)
- stable navigation across modes
- future extensibility: bookmarks, highlights, notes, AI companion, search

The design prioritizes:
- correctness over shortcuts
- modularity
- testability
- long-term maintainability

## High-Level Architecture

```
EPUB file
   ↓
[ EPUB Model ]
   ↓
[ HTML → IR Parser ]
   ↓
[ Semantic IR ]
   ↓
[ Controller + State ]
   ↓
[ Layout Engines ]  ←→  [ Policies ]
   ↓
[ View Widgets (Textual) ]
```

Each layer has one responsibility and no UI leakage downward.


## Core Concepts (Agreed Foundations)

### Canonical Addressing

Navigation, bookmarks, highlights, RSVP position, etc. must all refer to the same canonical
position, independent of rendering.

Canonical Position (future-ready)

```
DocPos(
    spine: int,   # chapter / spine item index
    block: int,   # block index inside chapter
    span: int,    # span index inside block
    offset: int,  # character offset inside span.text
)
```

This survives:
- reflow
- terminal resize
- switching between normal / RSVP
- different renderers


## Component Breakdown

4.1 EPUB Model (DONE)

Responsibility
	•	unzip EPUB
	•	locate OPF via META-INF/container.xml
	•	parse OPF (manifest, spine)
	•	load raw XHTML/HTML for spine items

Key properties
	•	no rendering logic
	•	no HTML parsing
	•	deterministic, testable

Public API

book = EpubBook(path)
book.chapter_count()
html = book.read_chapter_html(i)


4.2 HTML → IR Parser (DONE)

Responsibility
	•	convert raw XHTML into semantic IR
	•	preserve structure and inline formatting
	•	normalize whitespace correctly
	•	remain renderer-agnostic

Intermediate Representation (IR)

class BlockType(Enum):
    P, H1, H2, H3, H4, H5, PRE, IMG, TABLE

@dataclass(frozen=True)
class Span:
    text: str
    marks: FrozenSet[str]  # {"bold","italic","code","link"}
    href: str | None

@dataclass(frozen=True)
class Block:
    type: BlockType
    inlines: tuple[Span, ...]
    attrs: Mapping[str, str]

Design decisions
	•	<div> treated as paragraph (P)
	•	empty paragraphs preserved
	•	nested inline formatting preserved
	•	whitespace normalized but not destroyed
	•	external links captured (href)
	•	code / tables / images identified early

This layer is the semantic backbone of the app.


4.3 Reader State

Single source of truth for navigation.

@dataclass
class ReaderState:
    pos: DocPos
    mode: ReadMode  # NORMAL / RSVP / (future: PAGE)
    wpm: int
    playing: bool

No widget mutates this directly.


4.4 Controller (TO IMPLEMENT)

Responsibility
	•	own ReaderState
	•	apply commands
	•	enforce policies
	•	mediate between engines and UI

UI never mutates state directly.

Commands (examples)

ScrollLines(+1)
PageDown()
ToggleMode()
RSVPNextToken()
SetWPM(400)
GoTo(DocPos)

Controller:
	•	routes command to current engine
	•	updates canonical position
	•	handles forced mode switches


4.5 Policies

Rules that affect behavior globally.

RSVP Safety Policy (AGREED)
RSVP is disabled for:
	•	images
	•	tables
	•	code blocks
	•	external links

Implementation:
	•	RSVP engine emits RequiresNormalMode
	•	controller switches mode + pauses playback
	•	UI displays reason

Policies are not hardcoded into views.


4.6 Layout Engines (TO IMPLEMENT)

Engines interpret IR + state to produce render slices.

Normal (LineWrap) Engine
	•	lazy line wrapping
	•	reflows on resize
	•	uses Textual Line API
	•	maps rendered lines ↔ DocPos
	•	supports large books efficiently

RSVP Engine
	•	flattens IR into token stream
	•	tokens carry:
	•	text
	•	marks
	•	source DocPos
	•	ORP alignment handled in view
	•	enforces RSVP safety policy

Engines are:
	•	stateless or lightly cached
	•	deterministic
	•	independent of UI toolkit


4.7 View Widgets (Textual)

Responsibility
	•	render slices
	•	capture input
	•	emit commands

Examples:
	•	LineReaderWidget
	•	RSVPWidget
	•	future: PageWidget

Widgets:
	•	do not parse HTML
	•	do not compute layout
	•	do not store navigation state


## Feature Extensibility (Planned)

Because of the IR + DocPos design, these become natural extensions:

Bookmarks

Bookmark(name, DocPos)

Highlights

Highlight(DocSpan, color)

Notes

Note(DocSpan, text)

Search
	•	IR text search
	•	search over notes/bookmarks
	•	jump to DocPos

AI Companion
	•	chat about current Block / Span
	•	inline explanations
	•	summary of chapter/block

All of these depend on stable canonical addressing, which you now have.


## Roadmap (Concrete Next Steps)

Phase 1 — Reader MVP
- [X] EPUB Model
- [X] HTML → IR parser + tests
- [X] ReaderState + Controller
- [X] Normal (line-wrap) engine
- [X] Normal reader widget (Textual Line API)
- [X] Scroll navigation

Phase 2 — RSVP Mode
- [X] RSVP token stream engine
- [X] ORP-aligned RSVP widget
- [X] WPM control + timing
- [X] RSVP safety enforcement

Phase 3 — UX & Stability
- [.] Mode switching (Normal ↔ RSVP)
- [.] Resize-safe reflow
- [.] Progress tracking
- [ ] Status overlays

Phase 4 — Power Features
- [ ] Bookmarks
- [ ] Highlights & notes
- [ ] Search
- [ ] AI companion


## Key Design Principles (Keep These)
- Semantic first, visual second
- One canonical position
- Engines don’t know UI
- Widgets don’t know book structure
- Policies live outside rendering
- Everything testable without Textual
