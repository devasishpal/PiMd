"""Tests for the DocxRenderer in isolation."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from zipfile import ZipFile

from pimd.models import (
    Blockquote,
    BulletList,
    CodeBlock,
    Document,
    Heading,
    HorizontalRule,
    Image,
    ListItem,
    OrderedList,
    Paragraph,
    Span,
    Table,
)
from pimd.renderers.docx_renderer import DocxRenderer


def _make_png() -> bytes:
    def chunk(chunk_type: str, data: bytes) -> bytes:
        c = chunk_type.encode() + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk("IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = zlib.compress(b"\x00\xff\x00\x00")
    idat = chunk("IDAT", raw)
    iend = chunk("IEND", b"")
    return sig + ihdr + idat + iend


def assert_valid_docx(path: Path) -> None:
    assert path.exists()
    assert path.stat().st_size > 0
    with ZipFile(path) as zf:
        assert "word/document.xml" in zf.namelist()


class TestDocxRenderer:
    """Supply pre-built Document models and validate the output."""

    def renderer(self) -> DocxRenderer:
        return DocxRenderer()

    def test_empty_document(self, tmp_path: Path) -> None:
        doc = Document(blocks=[])
        out = tmp_path / "empty.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_all_heading_levels(self, tmp_path: Path) -> None:
        blocks = [Heading(level=lv, spans=[Span(text=f"H{lv}")]) for lv in range(1, 7)]
        doc = Document(blocks=blocks)
        out = tmp_path / "headings.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_paragraph_with_spans(self, tmp_path: Path) -> None:
        spans = [
            Span(text="Normal "),
            Span(text="bold", bold=True),
            Span(text=" "),
            Span(text="italic", italic=True),
            Span(text=" "),
            Span(text="code", code=True),
        ]
        doc = Document(blocks=[Paragraph(spans=spans)])
        out = tmp_path / "spans.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_code_block(self, tmp_path: Path) -> None:
        doc = Document(blocks=[CodeBlock(code="def foo():\n    pass", language="python")])
        out = tmp_path / "code.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_bullet_list(self, tmp_path: Path) -> None:
        items = [
            ListItem(children=[Paragraph(spans=[Span(text="A")])]),
            ListItem(children=[Paragraph(spans=[Span(text="B")])]),
        ]
        doc = Document(blocks=[BulletList(items=items)])
        out = tmp_path / "bullets.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_ordered_list(self, tmp_path: Path) -> None:
        items = [
            ListItem(children=[Paragraph(spans=[Span(text="One")])]),
            ListItem(children=[Paragraph(spans=[Span(text="Two")])]),
        ]
        doc = Document(blocks=[OrderedList(items=items, start=1)])
        out = tmp_path / "ordered.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_ordered_list_custom_start(self, tmp_path: Path) -> None:
        items = [
            ListItem(children=[Paragraph(spans=[Span(text="Three")])]),
            ListItem(children=[Paragraph(spans=[Span(text="Four")])]),
        ]
        doc = Document(blocks=[OrderedList(items=items, start=3)])
        out = tmp_path / "ordered_start.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_blockquote(self, tmp_path: Path) -> None:
        inner = [Paragraph(spans=[Span(text="Quoted text")])]
        doc = Document(blocks=[Blockquote(children=inner)])
        out = tmp_path / "blockquote.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_table(self, tmp_path: Path) -> None:
        doc = Document(blocks=[Table(headers=["Col A", "Col B"], rows=[["1", "2"], ["3", "4"]])])
        out = tmp_path / "table.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_horizontal_rule(self, tmp_path: Path) -> None:
        doc = Document(blocks=[HorizontalRule()])
        out = tmp_path / "hr.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_image_missing(self, tmp_path: Path) -> None:
        doc = Document(blocks=[Image(alt="missing", url="/nope.png")])
        out = tmp_path / "img_missing.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_image_present(self, tmp_path: Path) -> None:
        img = tmp_path / "pic.png"
        img.write_bytes(_make_png())
        doc = Document(blocks=[Image(alt="pic", url=str(img))])
        out = tmp_path / "img_present.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    def test_mixed_document(self, tmp_path: Path) -> None:
        doc = Document(
            blocks=[
                Heading(level=1, spans=[Span(text="Title")]),
                Paragraph(spans=[Span(text="Body")]),
                CodeBlock(code="x = 1"),
                HorizontalRule(),
            ]
        )
        out = tmp_path / "mixed.docx"
        self.renderer().render(doc, out)
        assert_valid_docx(out)

    # -- TOC ---------------------------------------------------------------

    def test_toc_in_document(self, tmp_path: Path) -> None:
        doc = Document(blocks=[Heading(level=1, spans=[Span(text="Chapter")])])
        out = tmp_path / "toc_doc.docx"
        self.renderer().render(doc, out, generate_toc=True)
        assert_valid_docx(out)
        with ZipFile(out) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert "TOC" in xml

    # -- Metadata ----------------------------------------------------------

    def test_metadata_rendered(self, tmp_path: Path) -> None:
        doc = Document(blocks=[Paragraph(spans=[Span(text="Hello")])])
        out = tmp_path / "meta_doc.docx"
        self.renderer().render(
            doc, out, title="Doc", author="Alice", company="Acme", subject="Test", keywords=["a"]
        )
        assert_valid_docx(out)

    # -- Page numbers ------------------------------------------------------

    def test_page_numbers_rendered(self, tmp_path: Path) -> None:
        doc = Document(blocks=[Paragraph(spans=[Span(text="Hello")])])
        out = tmp_path / "pn_doc.docx"
        self.renderer().render(doc, out, page_numbers=True)
        assert_valid_docx(out)

    # -- Header / Footer ---------------------------------------------------

    def test_header_footer_rendered(self, tmp_path: Path) -> None:
        doc = Document(blocks=[Paragraph(spans=[Span(text="Hello")])])
        out = tmp_path / "hf_doc.docx"
        self.renderer().render(doc, out, header_text="H", footer_text="F")
        assert_valid_docx(out)

    # -- Cover page --------------------------------------------------------

    def test_cover_page_rendered(self, tmp_path: Path) -> None:
        doc = Document(blocks=[Paragraph(spans=[Span(text="Hello")])])
        out = tmp_path / "cover_doc.docx"
        self.renderer().render(
            doc, out, cover_page=True, title="Cover", author="A", doc_version="1"
        )
        assert_valid_docx(out)
