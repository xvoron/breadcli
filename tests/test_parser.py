from bread.parser import (
    Bold,
    Italics,
    Markup,
    Newline,
    Paragraph,
    Unknown,
    parse_content,
)

text = """
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

result = [
    Paragraph("This is a paragraph."),
    Newline(),
    Paragraph("This is "),
    Italics("italic"),
    Paragraph(" and "),
    Bold("bold"),
    Paragraph(" text."),
    Newline(),
    Unknown("This is a div."),
]


# More complex test with nested elements
complex_text = """
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


# Ultra-complex nesting test
ultra_complex_text = """
<html>
    <body>
        <div>
            <p>This is <b>bold with <i>italic <strong>strong <em>emphasized</em> text</strong> inside</i> bold</b> paragraph.</p>
        </div>
        <article>
            <section>
                <p>Multi-level: <b><i><strong><em>deeply nested</em></strong></i></b> formatting.</p>
            </section>
        </article>
    </body>
</html>
"""
