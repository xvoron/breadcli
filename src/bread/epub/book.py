from __future__ import annotations

import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ManifestItem:
    id: str
    href: str
    media_type: str


@dataclass(frozen=True)
class EpubPackage:
    opf_path: Path
    opf_dir: Path
    manifest: dict[str, ManifestItem]
    spine: list[str]


class EpubError(Exception):
    pass


def extract_epub(epub_path: Path, extract_to: Path) -> None:
    if not epub_path.exists():
        raise FileNotFoundError(epub_path)
    if not zipfile.is_zipfile(epub_path):
        raise EpubError(f"Not a valid EPUB/ZIP: {epub_path}")
    extract_to.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path, "r") as zf:
        zf.extractall(extract_to)


def _ns_tag(tag: str) -> str:
    """ElementTree represents namespaced tags as '{uri}localname'.

    We'll match by localname using endswith checks.
    """
    return tag.split("}", 1)[-1] if "}" in tag else tag


def find_opf_path(extract_root: Path) -> Path:
    """Parse META-INF/container.xml and return absolute path to the OPF."""
    container = extract_root / "META-INF" / "container.xml"
    if not container.exists():
        raise FileNotFoundError(container)

    try:
        tree = ET.parse(container)
    except ET.ParseError as e:
        raise EpubError(f"Failed to parse container.xml: {e}") from e

    root = tree.getroot()

    # Find all <rootfile full-path="..."> elements (namespace-safe)
    rootfiles: list[ET.Element] = []
    for el in root.iter():
        if _ns_tag(el.tag) == "rootfile":
            rootfiles.append(el)

    if not rootfiles:
        raise EpubError("container.xml: no <rootfile> elements found")

    # Prefer the standard media-type if present, else first rootfile.
    chosen = None
    for rf in rootfiles:
        if (rf.attrib.get("media-type") or "").strip() == "application/oebps-package+xml":
            chosen = rf
            break
    if chosen is None:
        chosen = rootfiles[0]

    full_path = (chosen.attrib.get("full-path") or "").strip()
    if not full_path:
        raise EpubError("container.xml: <rootfile> missing full-path attribute")

    opf_path = (extract_root / full_path).resolve()
    if not opf_path.exists():
        raise FileNotFoundError(opf_path)

    return opf_path


def parse_opf(opf_path: Path) -> EpubPackage:
    """Parse OPF (content.opf) into manifest + spine."""
    try:
        tree = ET.parse(opf_path)
    except ET.ParseError as e:
        raise EpubError(f"Failed to parse OPF {opf_path.name}: {e}") from e

    root = tree.getroot()
    opf_dir = opf_path.parent

    # Find <manifest> and <spine> elements namespace-safely
    manifest_el: Optional[ET.Element] = None
    spine_el: Optional[ET.Element] = None

    for el in root.iter():
        name = _ns_tag(el.tag)
        if name == "manifest":
            manifest_el = el
        elif name == "spine":
            spine_el = el

    if manifest_el is None:
        raise EpubError("OPF: missing <manifest>")
    if spine_el is None:
        raise EpubError("OPF: missing <spine>")

    manifest: dict[str, ManifestItem] = {}
    for item in manifest_el:
        if _ns_tag(item.tag) != "item":
            continue
        id_ = (item.attrib.get("id") or "").strip()
        href = (item.attrib.get("href") or "").strip()
        mtype = (item.attrib.get("media-type") or "").strip()
        if not id_ or not href or not mtype:
            continue
        manifest[id_] = ManifestItem(id=id_, href=href, media_type=mtype)

    spine: list[str] = []
    for itemref in spine_el:
        if _ns_tag(itemref.tag) != "itemref":
            continue
        idref = (itemref.attrib.get("idref") or "").strip()
        if idref:
            spine.append(idref)

    if not spine:
        raise EpubError("OPF: spine is empty")

    return EpubPackage(opf_path=opf_path, opf_dir=opf_dir, manifest=manifest, spine=spine)


def read_spine_item(pkg: EpubPackage, index: int, encoding: str = "utf-8") -> str:
    """Load the HTML/XHTML text for spine[index]."""

    if index < 0 or index >= len(pkg.spine):
        raise IndexError(index)

    idref = pkg.spine[index]
    item = pkg.manifest.get(idref)
    if item is None:
        raise EpubError(f"Spine idref {idref!r} not found in manifest")

    # Enforce your MVP target: XHTML/HTML only
    if item.media_type not in ("application/xhtml+xml", "text/html"):
        raise EpubError(f"Spine item is not HTML/XHTML: {item.media_type} ({item.href})")

    path = (pkg.opf_dir / item.href).resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    # Many EPUBs are UTF-8, but some aren't; keep encoding configurable for now.
    return path.read_text(encoding=encoding, errors="replace")


class EpubBook:
    def __init__(self, epub_path: Path, extract_dir: Optional[Path] = None) -> None:
        self.epub_path = epub_path

        # If no extract_dir provided, use a unique temp dir
        if extract_dir is None:
            self._tmp = tempfile.TemporaryDirectory(prefix="epub_")
            self.extract_root = Path(self._tmp.name)
        else:
            self._tmp = None
            self.extract_root = extract_dir

        extract_epub(self.epub_path, self.extract_root)
        opf = find_opf_path(self.extract_root)
        self.package = parse_opf(opf)

    def close(self) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()

    def chapter_count(self) -> int:
        return len(self.package.spine)

    def read_chapter_html(self, i: int) -> str:
        return read_spine_item(self.package, i)


if __name__ == "__main__":
    book = EpubBook(Path("./assets/test.epub"))
    try:
        html = book.read_chapter_html(2)
        print(html)
    finally:
        book.close()
