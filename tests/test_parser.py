import pytest

from bread.parser import (
    Block,
    BlockType,
    Span,
    parse_html_to_ir,
)

basic = """
<html>
    <body>
        <div>
            <p>This is a paragraph.</p>
            <p>This is <i>italic</i> and <b>bold</b> text.</p>
            <div>This is a div.</div>
        </div>
    </body>
</html>
"""

basic_expected = [
    Block(
        type=BlockType.P,
        inlines=(
            Span(text="This is a paragraph.", marks=frozenset(), href=None),
        ),
        attrs={},
    ),
    Block(
        type=BlockType.P,
        inlines=(
            Span(text="This is ", marks=frozenset(), href=None),
            Span(text="italic", marks=frozenset({"italic"}), href=None),
            Span(text=" and ", marks=frozenset(), href=None),
            Span(text="bold", marks=frozenset({"bold"}), href=None),
            Span(text=" text.", marks=frozenset(), href=None),
        ),
        attrs={},
    ),
    Block(
        type=BlockType.P,
        inlines=(
            Span(text="This is a div.", marks=frozenset(), href=None),
        ),
        attrs={},
    ),
]

nested_inlines = """
<html><body>
  <p>This is <b>bold and <i>italic</i></b>.</p>
</body></html>
"""

nested_inlines_expected = [
    Block(
        type=BlockType.P,
        inlines=(
            Span("This is ", frozenset(), None),
            Span("bold and ", frozenset({"bold"}), None),
            Span("italic", frozenset({"bold", "italic"}), None),
            Span(".", frozenset(), None),
        ),
        attrs={},
    )
]

empty_paragraphs = """
<html><body>
  <p> </p>
  <p>&nbsp;</p>
  <div><em></em></div>
  <p>Not empty.</p>
</body></html>
"""

empty_paragraphs_expected = [
    Block(type=BlockType.P, inlines=(), attrs={}),
    Block(type=BlockType.P, inlines=(), attrs={}),
    Block(type=BlockType.P, inlines=(), attrs={}),
    Block(
        type=BlockType.P,
        inlines=(Span("Not empty.", frozenset(), None),),
        attrs={},
    ),
]

links = """
<html><body>
  <p>Visit <a href="https://example.com">Example</a> now.</p>
</body></html>
"""
links_expected = [
    Block(
        type=BlockType.P,
        inlines=(
            Span("Visit ", frozenset(), None),
            Span("Example", frozenset({"link"}), "https://example.com"),
            Span(" now.", frozenset(), None),
        ),
        attrs={},
    )
]

mixed_whitespace = """
<html><body>
  <p>This   has    weird&nbsp;&nbsp;spacing.</p>
</body></html>
"""

mixed_whitespace_expected = [
    Block(
        type=BlockType.P,
        inlines=(Span("This has weird spacing.", frozenset(), None),),
        attrs={},
    )
]


complex_html = """
<html>
    <body>
        <p>This is a <b>bold <i>nested italic</i> text</b> example.</p>
        <div>A div with <i>italic</i> and <b>bold</b> content.</div>
        <p>Another <strong>strong with <em>emphasized</em> inside</strong> paragraph.</p>
        <section>
            <p>Paragraph inside section with <b>bold text</b>.</p>
        </section>
    </body>
</html>
"""

complex_expected = [
    Block(
        type=BlockType.P,
        inlines=(
            Span("This is a ", frozenset(), None),
            Span("bold ", frozenset({"bold"}), None),
            Span("nested italic", frozenset({"bold", "italic"}), None),
            Span(" text", frozenset({"bold"}), None),
            Span(" example.", frozenset(), None),
        ),
        attrs={},
    ),
    Block(
        type=BlockType.P,
        inlines=(
            Span("A div with ", frozenset(), None),
            Span("italic", frozenset({"italic"}), None),
            Span(" and ", frozenset(), None),
            Span("bold", frozenset({"bold"}), None),
            Span(" content.", frozenset(), None),
        ),
        attrs={},
    ),
    Block(
        type=BlockType.P,
        inlines=(
            Span("Another ", frozenset(), None),
            Span("strong with ", frozenset({"bold"}), None),
            Span("emphasized", frozenset({"bold", "italic"}), None),
            Span(" inside", frozenset({"bold"}), None),
            Span(" paragraph.", frozenset(), None),
        ),
        attrs={},
    ),
    Block(
        type=BlockType.P,
        inlines=(
            Span("Paragraph inside section with ", frozenset(), None),
            Span("bold text", frozenset({"bold"}), None),
            Span(".", frozenset(), None),
        ),
        attrs={},
    ),
]

@pytest.mark.parametrize("html,expected", [
    (basic, basic_expected),
    (nested_inlines, nested_inlines_expected),
    (empty_paragraphs, empty_paragraphs_expected),
    (links, links_expected),
    (mixed_whitespace, mixed_whitespace_expected),
    (complex_html, complex_expected),
])
def test_parsing(html, expected):
    parsed = parse_html_to_ir(html)
    assert parsed == expected
