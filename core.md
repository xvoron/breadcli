# Intro

The whole app consist of three main layers:
- Domain
- Layout
- UI

# Domain
Domain is responsible for document representation and answer to
the question "what is the document?". To answer this question
domain layer translate document into intermediate representation.

## Epub
To work with epub document we implement `EpubBook` object.
This object is responsible for unzip epub document, and provide content
of the chapters.

Files:
- `bread/domain/*`
- `bread/parsing/*`
- `bread/epub/*`

## IR
Intermediate representation (__IR__) is suitable for layout and render purposes
format. It contain `Block`, `Span` objects, that provide **semantic structure**
information.

# Layout Layer
Layout layers is responsible for translation __IR__ into
lines of wrapped texts.

## Layout Engine
The main component of layout layer is `LayoutEngine`.
`LayoutEngine` turns __IR__ and reader state (application state) into
something that **UI** can render.

That means that in normal reading mode it turns `Block`s into wrapped text lines.
For rsvp mode it convert `Blocks` into one word at a time representation.

`LayoutEngine` solves:
- line wrapping
- caching
- mapping scroll position to document position
- mapping document position to visible content

## Line Wrapping Layout Engine
For normal mode we implement `LineWrappingLayoutEngine`, the concrete
implementation of abstract `LayoutEngine`.

The process of this engine is following:
- fetches blocks for spine index
- flatten block text
- wraps text into lines
- keep the position of the line in the original document

## Reader State
Also we need to represent the state of the application. To do so 
`ReaderState` is introduced.

```python
@dataclass
class ReaderState:
    position: DocumentPosition
    mode: ReadMode
    top_line_hint: int
```
- `position` is canonical location in document 
- `top_line_hint` **UI** convenience (start rendering from this line)

Engine keeps this state in sync.

## Reader Controller
`ReaderController` is a simple component that:
- holds the current `ReaderState`
- knows what engine is active
- forwards commands from **UI events** to engine

Files:
- `bread/engines/*`
- `bread/app/*`

# UI
**UI** is responsible for render:
- asks controller for a `slice`
- tracks `virtual_size`
- renders lines
- send commands to controller
