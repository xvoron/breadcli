from __future__ import annotations

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from bread.domain.ir import Block, BlockType, Span

NBSP = "\xa0"

INLINE_MARKS = {
    "em": "italic",
    "i": "italic",
    "strong": "bold",
    "b": "bold",
    "code": "code",
    "a": "link",
}


def _clean_text(s: str) -> str:
    s = (
        s
        .replace(NBSP, " ")
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("\t", " ")
    )

    while "  " in s:
        s = s.replace("  ", " ")
    return s

def _iter_spans(node, marks: frozenset[str], href: str | None) -> list[Span]:
    out: list[Span] = []

    if isinstance(node, NavigableString):
        txt = _clean_text(str(node))
        if txt == "":
            return out
        if txt.strip() == "":
            out.append(Span(" ", marks, href))
            return out

        out.append(Span(txt, marks, href))
        return out

    name = (node.name or "").lower()
    if name == "br":
        out.append(Span("\n", marks, href))
        return out

    new_marks = marks
    new_href = href
    if name in INLINE_MARKS:
        new_marks = frozenset(set(marks) | {INLINE_MARKS[name]})
        if name == "a":
            new_href = node.get("href")

    for child in node.children:
        out.extend(_iter_spans(child, new_marks, new_href))

    return out

def _has_block_descendant(tag: Tag) -> bool:
    for child in tag.descendants:
        if isinstance(child, Tag) and child is not tag:
            name = (child.name or "").lower()
            if name in {"p", "div", "h1", "h2", "h3", "h4", "h5", "pre", "img", "table"}:
                return True
    return False

def parse_html_to_ir(content: str) -> list[Block]:
    soup = BeautifulSoup(content, "html.parser")

    body = soup.body or soup
    blocks: list[Block] = []

    for el in body.descendants:
        if not isinstance(el, Tag):
            continue

        name = (el.name or "").lower()

        if name in {"p", "div"} and _has_block_descendant(el):
            continue

        if name in {"p", "div"}:
            spans = _merge_adjacent(_iter_spans(el, frozenset(), None))
            text_all = "".join(s.text for s in spans).replace("\n", "")
            if text_all.strip() == "":
                blocks.append(Block(BlockType.P, ()))
            else:
                spans = _trim_span_edges(spans)
                blocks.append(Block(BlockType.P, tuple(spans)))
        elif name in {"h1", "h2", "h3", "h4", "h5"}:
            spans = _trim_span_edges(_merge_adjacent(_iter_spans(el, frozenset(),
                                                                 None)))
            blocks.append(Block(BlockType(name), tuple(spans)))
        elif name == "pre":
            txt = el.get_text()
            blocks.append(Block(BlockType.PRE, (Span(txt, marks=frozenset({"code"})),)))
        elif name == "img":
            blocks.append(Block(BlockType.IMG, (), attrs=dict(el.attrs)))
        elif name == "table":
            blocks.append(Block(BlockType.TABLE, (), attrs=dict(el.attrs)))
    return blocks

def _trim_span_edges(spans: list[Span]) -> list[Span]:
    if not spans:
        return []
    first = spans[0]
    ft = first.text.lstrip(" ")
    spans[0] = Span(ft, marks=first.marks, href=first.href)

    last = spans[-1]
    lt = last.text.rstrip(" ")
    spans[-1] = Span(lt, marks=last.marks, href=last.href)

    return [s for s in spans if s.text != ""]

def _merge_adjacent(spans: list[Span]) -> list[Span]:
    if not spans:
        return []

    out: list[Span] = [spans[0]]

    for s in spans[1:]:
        last = out[-1]
        if last.marks == s.marks and last.href == s.href:
            out[-1] = Span(last.text + s.text, marks=last.marks, href=last.href)
        else:
            out.append(s)

    return out
