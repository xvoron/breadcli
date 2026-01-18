from pathlib import Path

from bread.epub.book import EpubBook
from bread.parsing import parse_html_to_ir


if __name__ == "__main__":

    book = EpubBook(Path("./assets/test.epub"))
    try:
        html = book.read_chapter_html(3)
        print(html)
        ir = parse_html_to_ir(html)
        print("-" * 40)
        print(ir)
    finally:
        book.close()
