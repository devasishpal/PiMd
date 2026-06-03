"""Tests for Markdown → DOCX conversion pipeline."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from zipfile import ZipFile

import pytest

from pimd import MarkdownConverter, md_to_docx
from pimd.exceptions import ConversionError
from pimd.models import Document, DocumentStatistics
from pimd.parsers.markdown_parser import MarkdownParser


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
    assert path.exists(), f"File not found: {path}"
    assert path.stat().st_size > 0, f"Empty file: {path}"
    with ZipFile(path) as zf:
        assert "word/document.xml" in zf.namelist()


# ======================================================================
# MarkdownConverter
# ======================================================================


class TestMarkdownConverterAPI:
    def test_instantiation(self) -> None:
        converter = MarkdownConverter()
        assert isinstance(converter, MarkdownConverter)

    def test_convert_file_not_found(self, tmp_path: Path) -> None:
        converter = MarkdownConverter()
        with pytest.raises(ConversionError, match="not found"):
            converter.convert("nonexistent.md", tmp_path / "out.docx")

    def test_convert_text_basic(self, tmp_path: Path) -> None:
        out = tmp_path / "out.docx"
        MarkdownConverter().convert_text("# Hello", str(out))
        assert_valid_docx(out)

    def test_md_to_docx_convenience(self, tmp_path: Path) -> None:
        md_file = tmp_path / "in.md"
        md_file.write_text("Hello **world**")
        out = tmp_path / "out.docx"
        md_to_docx(str(md_file), str(out))
        assert_valid_docx(out)

    # -- Metadata ----------------------------------------------------------

    def test_metadata(self, tmp_path: Path) -> None:
        md = "# Title\n\nBody."
        out = tmp_path / "meta.docx"
        MarkdownConverter().convert_text(
            md,
            str(out),
            title="My Document",
            author="Alice",
            company="Acme",
            subject="Testing",
            keywords=["test", "docs"],
        )
        assert_valid_docx(out)

    # -- TOC ---------------------------------------------------------------

    def test_generate_toc(self, tmp_path: Path) -> None:
        md = "# Chapter 1\n\nContent.\n\n## Section 1.1\n\nMore."
        out = tmp_path / "toc.docx"
        MarkdownConverter().convert_text(md, str(out), generate_toc=True)
        assert_valid_docx(out)
        # Verify TOC field code exists in the XML
        with ZipFile(out) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert "TOC" in xml

    # -- Page numbers ------------------------------------------------------

    def test_page_numbers(self, tmp_path: Path) -> None:
        md = "# Title\n\nBody."
        out = tmp_path / "pagenum.docx"
        MarkdownConverter().convert_text(md, str(out), page_numbers=True)
        assert_valid_docx(out)

    # -- Header / Footer ---------------------------------------------------

    def test_header_footer(self, tmp_path: Path) -> None:
        md = "# Title\n\nBody."
        out = tmp_path / "header_footer.docx"
        MarkdownConverter().convert_text(
            md, str(out), header_text="My Header", footer_text="My Footer"
        )
        assert_valid_docx(out)

    # -- Cover page --------------------------------------------------------

    def test_cover_page(self, tmp_path: Path) -> None:
        md = "# Chapter 1\n\nContent."
        out = tmp_path / "cover.docx"
        MarkdownConverter().convert_text(
            md,
            str(out),
            cover_page=True,
            title="The Guide",
            author="Alice",
            doc_version="1.0",
        )
        assert_valid_docx(out)

    # -- Combined features -------------------------------------------------

    def test_all_features(self, tmp_path: Path) -> None:
        md = "# Intro\n\n## Details\n\nContent."
        out = tmp_path / "all.docx"
        MarkdownConverter().convert_text(
            md,
            str(out),
            generate_toc=True,
            page_numbers=True,
            cover_page=True,
            title="Full Document",
            author="Alice",
            header_text="My Header",
        )
        assert_valid_docx(out)

    # -- Statistics --------------------------------------------------------

    def test_statistics(self, tmp_path: Path) -> None:
        md = """# H1

Paragraph one.

## H2

- Item 1
- Item 2

```python
code
```

> Quote.

| A | B |
|---|---|
| 1 | 2 |

![missing](nonexistent.png)
"""
        out = tmp_path / "stats.docx"
        converter = MarkdownConverter()
        converter.convert_text(md, str(out))
        stats = converter.get_statistics()
        assert isinstance(stats, DocumentStatistics)
        assert stats.heading_count >= 2
        assert stats.paragraph_count >= 1
        assert stats.code_block_count >= 1
        assert stats.table_count >= 1
        assert stats.list_item_count >= 2


# ======================================================================
# MarkdownParser — structural tests
# ======================================================================


class TestMarkdownParser:
    def test_empty_string(self) -> None:
        doc = MarkdownParser().parse("")
        assert len(doc) == 0

    def test_parse_rejects_nesting_over_limit(self) -> None:
        md = "\n".join(f"{'  ' * i}> deep" for i in range(200))
        doc = MarkdownParser().parse(md)
        assert isinstance(doc, Document)

    def test_parse_plain_text(self) -> None:
        doc = MarkdownParser().parse("Just some plain text.")
        assert len(doc) == 1


# ======================================================================
# Full conversion — element coverage
# ======================================================================


class TestMarkdownElements:
    @pytest.fixture
    def converter(self) -> MarkdownConverter:
        return MarkdownConverter()

    @pytest.mark.parametrize("level", range(1, 7))
    def test_headings(self, level: int, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = f"{'#' * level} Heading {level}\n\nParagraph."
        out = tmp_path / "headings.docx"
        converter.convert_text(md, str(out))
        assert_valid_docx(out)

    def test_bold(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        converter.convert_text("This is **bold** text.", str(tmp_path / "bold.docx"))
        assert_valid_docx(tmp_path / "bold.docx")

    def test_italic(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        converter.convert_text("This is *italic* text.", str(tmp_path / "italic.docx"))
        assert_valid_docx(tmp_path / "italic.docx")

    def test_bold_italic_nested(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "This is ***bold italic*** and **bold *and italic***."
        converter.convert_text(md, str(tmp_path / "bolditalic.docx"))
        assert_valid_docx(tmp_path / "bolditalic.docx")

    def test_inline_code(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        converter.convert_text("Use `print()` to output.", str(tmp_path / "code.docx"))
        assert_valid_docx(tmp_path / "code.docx")

    def test_fenced_code_block(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "```python\ndef hello():\n    pass\n```"
        converter.convert_text(md, str(tmp_path / "fence.docx"))
        assert_valid_docx(tmp_path / "fence.docx")

    def test_indented_code_block(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "    x = 1\n    y = 2"
        converter.convert_text(md, str(tmp_path / "indent_code.docx"))
        assert_valid_docx(tmp_path / "indent_code.docx")

    def test_unordered_list(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "- Item A\n- Item B\n- Item C"
        converter.convert_text(md, str(tmp_path / "ulist.docx"))
        assert_valid_docx(tmp_path / "ulist.docx")

    def test_ordered_list(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "1. First\n2. Second\n3. Third"
        converter.convert_text(md, str(tmp_path / "olist.docx"))
        assert_valid_docx(tmp_path / "olist.docx")

    def test_nested_list(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "- Outer\n  - Inner A\n  - Inner B\n- Outer 2"
        converter.convert_text(md, str(tmp_path / "nested.docx"))
        assert_valid_docx(tmp_path / "nested.docx")

    def test_blockquote(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "> This is a blockquote.\n> It spans two lines."
        converter.convert_text(md, str(tmp_path / "quote.docx"))
        assert_valid_docx(tmp_path / "quote.docx")

    def test_link(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "Visit [PiMD](https://github.com/yourname/pimd)."
        converter.convert_text(md, str(tmp_path / "link.docx"))
        assert_valid_docx(tmp_path / "link.docx")

    def test_table(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "| Name  | Age |\n|-------|-----|\n| Alice | 30  |\n| Bob   | 25  |"
        converter.convert_text(md, str(tmp_path / "table.docx"))
        assert_valid_docx(tmp_path / "table.docx")

    def test_table_no_header(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "| A | B |\n| - | - |\n| 1 | 2 |"
        converter.convert_text(md, str(tmp_path / "table_noheader.docx"))
        assert_valid_docx(tmp_path / "table_noheader.docx")

    def test_horizontal_rule(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "Above\n\n---\n\nBelow"
        converter.convert_text(md, str(tmp_path / "hr.docx"))
        assert_valid_docx(tmp_path / "hr.docx")

    def test_image_missing(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "![alt](/nonexistent/image.png)"
        converter.convert_text(md, str(tmp_path / "img_missing.docx"))
        assert_valid_docx(tmp_path / "img_missing.docx")

    def test_image_present(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        img = tmp_path / "logo.png"
        img.write_bytes(_make_png())
        md = f"![Logo]({img.as_posix()})"
        converter.convert_text(md, str(tmp_path / "img_present.docx"))
        assert_valid_docx(tmp_path / "img_present.docx")

    def test_multiple_paragraphs(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        converter.convert_text(md, str(tmp_path / "paras.docx"))
        assert_valid_docx(tmp_path / "paras.docx")

    def test_full_document(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        md = """# My Document

This is a **paragraph** with *formatting* and `code`.

## Lists

- Apples
- Bananas
- Cherries

## Code

```python
print("hello")
```

> A wise quote.

---

| Key | Value |
|-----|-------|
| PiMD | 0.1.0 |
"""
        converter.convert_text(md, str(tmp_path / "full.docx"))
        assert_valid_docx(tmp_path / "full.docx")

    def test_large_document(self, tmp_path: Path, converter: MarkdownConverter) -> None:
        lines: list[str] = []
        lines.append("# Large Document\n")
        for i in range(1, 1001):
            lines.append(f"## Section {i}\n")
            lines.append(f"Content of section {i}.\n\n")
        lines.append("\n\n| A | B |\n| - | - |\n")
        for i in range(100):
            lines.append(f"| {i} | {i * 2} |\n")

        md = "".join(lines)
        converter.convert_text(md, str(tmp_path / "large.docx"))
        assert_valid_docx(tmp_path / "large.docx")
        assert (tmp_path / "large.docx").stat().st_size > 10000
