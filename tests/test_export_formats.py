"""Tests for EPUB, LaTeX, and PDF/A renderers."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pimd.export.formats import EpubRenderer, LatexRenderer
from pimd.export.formats.epub import validate_epub
from pimd.export.pdf import convert_to_pdfa
from pimd.models import (
    BulletList,
    CodeBlock,
    Document,
    Heading,
    ListItem,
    Paragraph,
    Span,
    Table,
)


# ======================================================================
# Test data
# ======================================================================

def make_simple_document() -> Document:
    return Document(
        blocks=[
            Heading(level=1, spans=[Span(text="Chapter 1")]),
            Paragraph(spans=[Span(text="Hello world.")]),
            Heading(level=2, spans=[Span(text="Section 1.1")]),
            Paragraph(spans=[Span(text="Some content here.")]),
            CodeBlock(code="print('Hello')", language="python"),
        ]
    )


def make_complex_document() -> Document:
    return Document(
        blocks=[
            Heading(level=1, spans=[Span(text="Main Title")]),
            Paragraph(spans=[Span(text="A paragraph with "), Span(text="bold", bold=True), Span(text=" text.")]),
            CodeBlock(code="def foo():\n    pass", language="python"),
            Table(
                headers=["Name", "Value"],
                rows=[["A", "1"], ["B", "2"]],
            ),
            BulletList(
                items=[
                    ListItem(children=[Paragraph(spans=[Span(text="Item 1")])]),
                    ListItem(children=[Paragraph(spans=[Span(text="Item 2")])]),
                ]
            ),
            Heading(level=2, spans=[Span(text="References")]),
            Paragraph(spans=[Span(text="See "), Span(text="here", link_url="https://example.com"), Span(text=".")]),
        ]
    )


# ======================================================================
# EPUB Renderer Tests
# ======================================================================


class TestEpubRenderer:
    def test_format_info(self) -> None:
        renderer = EpubRenderer()
        assert renderer.FORMAT_NAME == "epub"
        assert renderer.FORMAT_DESCRIPTION == "EPUB 3.2 e-book format"
        assert renderer.IMPLEMENTED

    def test_is_available(self) -> None:
        renderer = EpubRenderer()
        assert renderer.is_available

    def test_missing_dependencies(self) -> None:
        renderer = EpubRenderer()
        deps = renderer.missing_dependencies
        assert isinstance(deps, list)

    def test_render_to_file(self, tmp_path: Path) -> None:
        doc = make_simple_document()
        out = tmp_path / "test.epub"
        renderer = EpubRenderer()
        result = renderer.render(doc, out, title="Test Book", author="Author")
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_render_to_bytes(self) -> None:
        doc = make_simple_document()
        renderer = EpubRenderer()
        result = renderer.render_to_bytes(doc, title="Test", author="Author")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_render_complex_document(self, tmp_path: Path) -> None:
        doc = make_complex_document()
        out = tmp_path / "complex.epub"
        renderer = EpubRenderer()
        result = renderer.render(doc, out, title="Complex Book", author="Writer")
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_render_with_metadata(self, tmp_path: Path) -> None:
        doc = make_simple_document()
        out = tmp_path / "meta.epub"
        renderer = EpubRenderer()
        renderer.render(
            doc, out,
            title="Metadata Test",
            author="Jane Doe",
            language="en",
        )
        assert out.exists()

    def test_epub_validation_passes(self, tmp_path: Path) -> None:
        doc = make_simple_document()
        out = tmp_path / "valid.epub"
        renderer = EpubRenderer()
        renderer.render(doc, out, title="Valid Book", author="Author")
        issues = validate_epub(out)
        assert len(issues) == 0, f"Validation issues: {issues}"

    def test_epub_validation_missing_file(self) -> None:
        issues = validate_epub("/nonexistent/file.epub")
        assert len(issues) > 0
        assert "not found" in issues[0]

    def test_css_customization(self, tmp_path: Path) -> None:
        doc = make_simple_document()
        css_path = tmp_path / "custom.css"
        css_path.write_text("body { color: red; }")
        out = tmp_path / "custom_css.epub"
        renderer = EpubRenderer(css_path=css_path)
        renderer.render(doc, out, title="CSS Test", author="Author")
        assert out.exists()

    def test_render_empty_document(self, tmp_path: Path) -> None:
        doc = Document(blocks=[])
        out = tmp_path / "empty.epub"
        renderer = EpubRenderer()
        renderer.render(doc, out, title="Empty", author="Author")
        assert out.exists()

    def test_escape_html_in_text(self) -> None:
        renderer = EpubRenderer()
        escaped = renderer._escape("<script>alert('xss')</script> & \"quote\"")
        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "&amp;" in escaped
        assert "&quot;" in escaped

    def test_render_cover_page(self) -> None:
        renderer = EpubRenderer()
        html = renderer._render_cover_page("Title", "Author", None)
        assert "Title" in html
        assert "Author" in html

    def test_render_nav(self) -> None:
        renderer = EpubRenderer()
        chapters = [
            {"title": "Ch1", "blocks": []},
            {"title": "Ch2", "blocks": []},
        ]
        html = renderer._render_nav("Test Book", chapters)
        assert "Ch1" in html
        assert "Ch2" in html
        assert "Table of Contents" in html

    def test_render_ncx(self) -> None:
        renderer = EpubRenderer()
        chapters = [{"title": "Ch1", "blocks": []}]
        ncx = renderer._render_ncx("urn:uuid:test", "Book", "Author", chapters)
        assert "Ch1" in ncx
        assert "Book" in ncx
        assert "Author" in ncx

    def test_render_opf(self) -> None:
        renderer = EpubRenderer()
        opf = renderer._render_opf(
            package_id="urn:uuid:test",
            title="My Book",
            author="Author",
            language="en",
            date="2026-01-01",
            spine_items=["cover.xhtml", "nav.xhtml", "chapter_0001.xhtml"],
            nav_points=[{"id": "nav_1", "label": "Ch1", "src": "chapter_0001.xhtml", "play_order": 2}],
        )
        assert "My Book" in opf
        assert "Author" in opf
        assert "chapter_0001.xhtml" in opf

    def test_split_into_chapters(self) -> None:
        renderer = EpubRenderer()
        doc = Document(blocks=[
            Heading(level=1, spans=[Span(text="Ch1")]),
            Paragraph(spans=[Span(text="Text")]),
            Heading(level=2, spans=[Span(text="Sec1")]),
            Paragraph(spans=[Span(text="More")]),
        ])
        chapters = renderer._split_into_chapters(doc)
        assert len(chapters) == 2
        assert chapters[0]["title"] == "Ch1"
        assert chapters[1]["title"] == "Sec1"


# ======================================================================
# LaTeX Renderer Tests
# ======================================================================


class TestLatexRenderer:
    def test_format_info(self) -> None:
        renderer = LatexRenderer()
        assert renderer.FORMAT_NAME == "latex"
        assert renderer.FORMAT_DESCRIPTION == "LaTeX typesetting format"
        assert renderer.IMPLEMENTED

    def test_is_available(self) -> None:
        renderer = LatexRenderer()
        assert renderer.is_available

    def test_render_to_file(self, tmp_path: Path) -> None:
        doc = make_simple_document()
        out = tmp_path / "test.tex"
        renderer = LatexRenderer()
        result = renderer.render(doc, out, title="Test Paper", author="Author")
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_render_to_bytes(self) -> None:
        doc = make_simple_document()
        renderer = LatexRenderer()
        result = renderer.render_to_bytes(doc, title="Test", author="Author")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_render_complex_document(self, tmp_path: Path) -> None:
        doc = make_complex_document()
        out = tmp_path / "complex.tex"
        renderer = LatexRenderer()
        renderer.render(doc, out, title="Complex Paper", author="Writer")
        content = out.read_text(encoding="utf-8")
        assert "Complex Paper" in content
        assert "Writer" in content
        assert "\\section" in content
        assert "\\begin{tabular}" in content

    def test_render_article_class(self, tmp_path: Path) -> None:
        doc = make_simple_document()
        out = tmp_path / "article.tex"
        renderer = LatexRenderer()
        renderer.render(doc, out, title="Article", author="Author", document_class="article")
        content = out.read_text(encoding="utf-8")
        assert "\\documentclass[12pt,a4paper]{article}" in content

    def test_render_report_class(self, tmp_path: Path) -> None:
        doc = make_simple_document()
        out = tmp_path / "report.tex"
        renderer = LatexRenderer()
        renderer.render(doc, out, title="Report", author="Author", document_class="report")
        content = out.read_text(encoding="utf-8")
        assert "\\documentclass" in content

    def test_render_book_class(self, tmp_path: Path) -> None:
        doc = make_simple_document()
        out = tmp_path / "book.tex"
        renderer = LatexRenderer()
        renderer.render(doc, out, title="Book", author="Author", document_class="book")
        content = out.read_text(encoding="utf-8")
        assert "\\frontmatter" in content
        assert "\\mainmatter" in content

    def test_generate_toc(self, tmp_path: Path) -> None:
        doc = Document(blocks=[
            Heading(level=1, spans=[Span(text="Intro")]),
            Paragraph(spans=[Span(text="Text")]),
        ])
        out = tmp_path / "toc.tex"
        renderer = LatexRenderer()
        renderer.render(doc, out, title="TOC Test", author="Author", generate_toc=True)
        content = out.read_text(encoding="utf-8")
        assert "\\tableofcontents" in content

    def test_escape_latex_special_chars(self) -> None:
        renderer = LatexRenderer()
        result = renderer._escape_latex("100% of $ & # { }")
        assert "\\%" in result
        assert "\\$" in result
        assert "\\&" in result
        assert "\\#" in result
        assert "\\{" in result
        assert "\\}" in result

    def test_render_heading(self) -> None:
        renderer = LatexRenderer()
        block = Heading(level=1, spans=[Span(text="Section")])
        result = renderer._render_heading_latex(block)
        assert "\\section{Section}" in result

    def test_render_subheading(self) -> None:
        renderer = LatexRenderer()
        block = Heading(level=2, spans=[Span(text="Sub")])
        result = renderer._render_heading_latex(block)
        assert "\\subsection{Sub}" in result

    def test_render_bold_italic(self) -> None:
        renderer = LatexRenderer()
        spans = [Span(text="bold", bold=True), Span(text="italic", italic=True)]
        result = renderer._render_spans_latex(spans)
        assert "\\textbf" in result
        assert "\\textit" in result

    def test_render_code_block(self) -> None:
        renderer = LatexRenderer()
        block = CodeBlock(code="print('hi')", language="python")
        result = renderer._render_block_to_latex(block)
        assert "\\begin{lstlisting}" in result
        assert "print" in result

    def test_render_table(self) -> None:
        renderer = LatexRenderer()
        block = Table(headers=["A", "B"], rows=[["1", "2"]])
        result = renderer._render_table_latex(block)
        assert "\\begin{tabular}" in result
        assert "A" in result
        assert "1" in result

    def test_inline_math(self) -> None:
        renderer = LatexRenderer()
        spans = [Span(text="", math="E=mc^2")]
        result = renderer._render_spans_latex(spans)
        assert "$" in result
        assert "E=mc^2" in result

    def test_render_empty_document(self, tmp_path: Path) -> None:
        doc = Document(blocks=[])
        out = tmp_path / "empty.tex"
        renderer = LatexRenderer()
        renderer.render(doc, out, title="Empty", author="Author")
        assert out.exists()


# ======================================================================
# PDF/A Tests
# ======================================================================


class TestPdfA:
    def test_convert_to_pdfa_missing_file(self, tmp_path: Path) -> None:
        inp = tmp_path / "nonexistent.docx"
        out = tmp_path / "output.pdf"
        result = convert_to_pdfa(inp, out)
        assert not result.success

    def test_pdfa_export_format_in_enum(self) -> None:
        from pimd.export.models import ExportFormat
        assert hasattr(ExportFormat, "PDFA")


# ======================================================================
# EPUB validation tests
# ======================================================================


class TestEpubValidation:
    def test_validate_valid_epub(self, tmp_path: Path) -> None:
        doc = make_simple_document()
        out = tmp_path / "valid.epub"
        EpubRenderer().render(doc, out, title="Test", author="Author")
        issues = validate_epub(out)
        assert len(issues) == 0

    def test_validate_mimetype(self, tmp_path: Path) -> None:
        # Create invalid EPUB
        import zipfile
        bad_path = tmp_path / "bad.epub"
        with zipfile.ZipFile(bad_path, "w") as zf:
            zf.writestr("wrong", "content")
        issues = validate_epub(bad_path)
        assert len(issues) > 0

    def test_validate_nonexistent(self) -> None:
        issues = validate_epub("/nonexistent.epub")
        assert "not found" in issues[0]
