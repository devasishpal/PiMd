"""Tests for HTMLConverter and HTMLParser."""

from pathlib import Path

import pytest

from pimd.converters.html import HTMLConverter
from pimd.models import (
    Blockquote,
    BulletList,
    CodeBlock,
    Document,
    Heading,
    HorizontalRule,
    Image,
    OrderedList,
    Paragraph,
    Table,
)
from pimd.parsers.html_parser import HTMLParser

# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def parser() -> HTMLParser:
    return HTMLParser()


def _assert_valid_docx(path: Path) -> None:
    """Verify a docx file was created and has content."""
    assert path.exists()
    assert path.stat().st_size > 0


# ======================================================================
# HTMLParser
# ======================================================================


class TestHTMLParser:
    """Verify HTMLParser converts HTML to the internal document model."""

    def test_instantiation(self) -> None:
        parser = HTMLParser()
        assert isinstance(parser, HTMLParser)

    def test_empty_string(self, parser: HTMLParser) -> None:
        doc = parser.parse("")
        assert isinstance(doc, Document)
        assert len(doc.blocks) == 0

    def test_plain_text(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p>Hello world</p>")
        assert len(doc.blocks) == 1
        block = doc.blocks[0]
        assert isinstance(block, Paragraph)
        assert block.plain_text() == "Hello world"

    def test_plain_text_body(self, parser: HTMLParser) -> None:
        """Text directly inside <body> becomes a Paragraph."""
        doc = parser.parse("Hello")
        assert len(doc.blocks) == 1
        assert isinstance(doc.blocks[0], Paragraph)

    # -- Headings --

    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6])
    def test_headings(self, parser: HTMLParser, level: int) -> None:
        doc = parser.parse(f"<h{level}>Title {level}</h{level}>")
        assert len(doc.blocks) == 1
        block = doc.blocks[0]
        assert isinstance(block, Heading)
        assert block.level == level
        assert block.plain_text() == f"Title {level}"

    # -- Inline formatting --

    def test_bold(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p><strong>bold</strong></p>")
        spans = doc.blocks[0].spans
        assert len(spans) == 1
        assert spans[0].bold is True
        assert spans[0].text == "bold"

    def test_b_tag(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p><b>bold</b></p>")
        spans = doc.blocks[0].spans
        assert spans[0].bold is True

    def test_italic(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p><em>italic</em></p>")
        spans = doc.blocks[0].spans
        assert spans[0].italic is True
        assert spans[0].text == "italic"

    def test_i_tag(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p><i>italic</i></p>")
        spans = doc.blocks[0].spans
        assert spans[0].italic is True

    def test_underline(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p><u>underlined</u></p>")
        spans = doc.blocks[0].spans
        assert spans[0].underline is True
        assert spans[0].text == "underlined"

    def test_inline_code(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p><code>code</code></p>")
        spans = doc.blocks[0].spans
        assert spans[0].code is True
        assert spans[0].text == "code"

    def test_bold_italic_nested(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p><strong>bold <em>and italic</em></strong></p>")
        spans = doc.blocks[0].spans
        assert len(spans) == 2
        assert spans[0].bold is True
        assert spans[0].italic is False
        assert spans[0].text == "bold "
        assert spans[1].bold is True
        assert spans[1].italic is True
        assert spans[1].text == "and italic"

    def test_mixed_inline(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p>Hello <b>bold</b> and <i>italic</i></p>")
        spans = doc.blocks[0].spans
        assert len(spans) == 4
        assert spans[0].text == "Hello "
        assert spans[1].bold is True
        assert spans[1].text == "bold"
        assert spans[2].text == " and "
        assert spans[3].italic is True
        assert spans[3].text == "italic"

    # -- Links --

    def test_link(self, parser: HTMLParser) -> None:
        doc = parser.parse('<p><a href="https://example.com">example</a></p>')
        spans = doc.blocks[0].spans
        assert len(spans) == 1
        assert spans[0].link_url == "https://example.com"
        assert spans[0].text == "example"

    def test_link_no_href(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p><a>no link</a></p>")
        spans = doc.blocks[0].spans
        assert spans[0].link_url == ""

    # -- Images --

    def test_inline_image(self, parser: HTMLParser) -> None:
        doc = parser.parse('<p><img src="pic.png" alt="photo"></p>')
        spans = doc.blocks[0].spans
        assert len(spans) == 1
        assert spans[0].link_url == "pic.png"
        assert spans[0].text == "photo"

    def test_block_image(self, parser: HTMLParser) -> None:
        doc = parser.parse('<img src="photo.jpg" alt="Photo" title="A photo">')
        assert len(doc.blocks) == 1
        block = doc.blocks[0]
        assert isinstance(block, Image)
        assert block.url == "photo.jpg"
        assert block.alt == "Photo"
        assert block.title == "A photo"

    # -- Code blocks --

    def test_fenced_code_block(self, parser: HTMLParser) -> None:
        doc = parser.parse("<pre><code>print('hello')</code></pre>")
        assert len(doc.blocks) == 1
        block = doc.blocks[0]
        assert isinstance(block, CodeBlock)
        assert "print('hello')" in block.code

    def test_code_block_with_language(self, parser: HTMLParser) -> None:
        doc = parser.parse('<pre><code class="python">import os</code></pre>')
        block = doc.blocks[0]
        assert isinstance(block, CodeBlock)
        assert block.language == "python"

    def test_code_block_no_code_tag(self, parser: HTMLParser) -> None:
        doc = parser.parse("<pre>raw pre text</pre>")
        assert len(doc.blocks) == 1
        assert isinstance(doc.blocks[0], CodeBlock)

    # -- Lists --

    def test_unordered_list(self, parser: HTMLParser) -> None:
        doc = parser.parse("<ul><li>One</li><li>Two</li></ul>")
        assert len(doc.blocks) == 1
        block = doc.blocks[0]
        assert isinstance(block, BulletList)
        assert len(block.items) == 2
        assert block.items[0].children[0].plain_text() == "One"

    def test_ordered_list(self, parser: HTMLParser) -> None:
        doc = parser.parse("<ol><li>First</li><li>Second</li></ol>")
        assert len(doc.blocks) == 1
        block = doc.blocks[0]
        assert isinstance(block, OrderedList)
        assert len(block.items) == 2

    def test_ordered_list_with_start(self, parser: HTMLParser) -> None:
        doc = parser.parse('<ol start="3"><li>Third</li></ol>')
        block = doc.blocks[0]
        assert isinstance(block, OrderedList)
        assert block.start == 3

    def test_nested_list(self, parser: HTMLParser) -> None:
        doc = parser.parse("<ul><li>One<ul><li>Nested</li></ul></li></ul>")
        assert len(doc.blocks) == 1
        item = doc.blocks[0].items[0]
        nested = [c for c in item.children if isinstance(c, BulletList)]
        assert len(nested) == 1

    # -- Blockquote --

    def test_blockquote(self, parser: HTMLParser) -> None:
        doc = parser.parse("<blockquote><p>Quote</p></blockquote>")
        assert len(doc.blocks) == 1
        block = doc.blocks[0]
        assert isinstance(block, Blockquote)
        assert len(block.children) == 1
        assert isinstance(block.children[0], Paragraph)
        assert block.children[0].plain_text() == "Quote"

    # -- Table --

    def test_table(self, parser: HTMLParser) -> None:
        html = """<table>
<thead><tr><th>Name</th><th>Age</th></tr></thead>
<tbody><tr><td>Alice</td><td>30</td></tr></tbody>
</table>"""
        doc = parser.parse(html)
        assert len(doc.blocks) == 1
        block = doc.blocks[0]
        assert isinstance(block, Table)
        assert block.headers == ["Name", "Age"]
        assert len(block.rows) == 1
        assert block.rows[0] == ["Alice", "30"]

    def test_table_no_thead(self, parser: HTMLParser) -> None:
        html = """<table>
<tr><th>Name</th><th>Age</th></tr>
<tr><td>Bob</td><td>25</td></tr>
</table>"""
        doc = parser.parse(html)
        block = doc.blocks[0]
        assert isinstance(block, Table)
        assert block.headers == ["Name", "Age"]
        assert len(block.rows) == 1

    def test_table_no_header(self, parser: HTMLParser) -> None:
        html = "<table><tr><td>Data</td></tr></table>"
        doc = parser.parse(html)
        block = doc.blocks[0]
        assert isinstance(block, Table)
        assert block.headers == []
        assert len(block.rows) == 1

    # -- Horizontal rule --

    def test_horizontal_rule(self, parser: HTMLParser) -> None:
        doc = parser.parse("<hr>")
        assert len(doc.blocks) == 1
        assert isinstance(doc.blocks[0], HorizontalRule)

    # -- DIV container --

    def test_div_container(self, parser: HTMLParser) -> None:
        doc = parser.parse("<div><p>Inside</p></div>")
        assert len(doc.blocks) == 1
        assert isinstance(doc.blocks[0], Paragraph)

    def test_section_container(self, parser: HTMLParser) -> None:
        doc = parser.parse("<section><h1>Section</h1></section>")
        assert len(doc.blocks) == 1
        assert isinstance(doc.blocks[0], Heading)

    # -- Full document --

    def test_full_document(self, parser: HTMLParser) -> None:
        html = """<html><body>
<h1>Title</h1>
<p>Hello <strong>world</strong></p>
<ul><li>Item</li></ul>
</body></html>"""
        doc = parser.parse(html)
        assert len(doc.blocks) >= 3
        assert isinstance(doc.blocks[0], Heading)
        assert isinstance(doc.blocks[1], Paragraph)
        assert isinstance(doc.blocks[2], BulletList)

    def test_line_break(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p>Line 1<br>Line 2</p>")
        spans = doc.blocks[0].spans
        assert len(spans) == 3
        assert spans[0].text == "Line 1"
        assert spans[1].text == "\n"
        assert spans[2].text == "Line 2"

    def test_multiple_paragraphs(self, parser: HTMLParser) -> None:
        doc = parser.parse("<p>First</p><p>Second</p>")
        assert len(doc.blocks) == 2
        assert doc.blocks[0].plain_text() == "First"
        assert doc.blocks[1].plain_text() == "Second"

    def test_span_tag(self, parser: HTMLParser) -> None:
        doc = parser.parse('<p><span style="color:red">colored</span></p>')
        spans = doc.blocks[0].spans
        assert len(spans) == 1
        assert spans[0].text == "colored"

    def test_parse_file(self, parser: HTMLParser, tmp_path: Path) -> None:
        html_file = tmp_path / "test.html"
        html_file.write_text("<h1>File</h1><p>Content</p>")
        doc = parser.parse_file(html_file)
        assert len(doc.blocks) == 2
        assert isinstance(doc.blocks[0], Heading)


# ======================================================================
# HTMLConverter
# ======================================================================


class TestHTMLConverterAPI:
    """Verify HTMLConverter API works end-to-end."""

    def test_instantiation(self) -> None:
        converter = HTMLConverter()
        assert isinstance(converter, HTMLConverter)

    def test_convert_file_not_found(self) -> None:
        converter = HTMLConverter()
        with pytest.raises(Exception):
            converter.convert("nonexistent.html", "out.docx")

    def test_convert_text_basic(self, tmp_path: Path) -> None:
        out = tmp_path / "out.docx"
        converter = HTMLConverter()
        converter.convert_text("<h1>Hello</h1><p>World</p>", out)
        _assert_valid_docx(out)

    def test_html_to_docx_convenience(self, tmp_path: Path) -> None:
        input_file = tmp_path / "test.html"
        input_file.write_text("<h1>Convenient</h1>")
        out = tmp_path / "out.docx"
        from pimd import html_to_docx

        html_to_docx(str(input_file), str(out))
        _assert_valid_docx(out)

    def test_convert_text_with_toc(self, tmp_path: Path) -> None:
        out = tmp_path / "toc.docx"
        converter = HTMLConverter()
        converter.convert_text("<h1>Chapter 1</h1><h2>Section</h2>", out, generate_toc=True)
        _assert_valid_docx(out)

    def test_convert_text_with_metadata(self, tmp_path: Path) -> None:
        out = tmp_path / "meta.docx"
        converter = HTMLConverter()
        converter.convert_text(
            "<h1>Doc</h1>",
            out,
            title="My Doc",
            author="Test",
            company="ACME",
            subject="Testing",
            keywords=["test", "html"],
        )
        _assert_valid_docx(out)

    def test_convert_text_with_page_numbers(self, tmp_path: Path) -> None:
        out = tmp_path / "pgnum.docx"
        converter = HTMLConverter()
        converter.convert_text("<p>Hello</p>", out, page_numbers=True)
        _assert_valid_docx(out)

    def test_convert_text_with_header_footer(self, tmp_path: Path) -> None:
        out = tmp_path / "hf.docx"
        converter = HTMLConverter()
        converter.convert_text("<p>Content</p>", out, header_text="Header", footer_text="Footer")
        _assert_valid_docx(out)

    def test_convert_text_with_cover(self, tmp_path: Path) -> None:
        out = tmp_path / "cover.docx"
        converter = HTMLConverter()
        converter.convert_text(
            "<p>Content</p>",
            out,
            cover_page=True,
            title="Cover",
            author="A",
            doc_version="1",
        )
        _assert_valid_docx(out)

    def test_convert_file(self, tmp_path: Path) -> None:
        input_file = tmp_path / "test.html"
        input_file.write_text("<h1>File</h1><p>Content</p>")
        out = tmp_path / "out.docx"
        converter = HTMLConverter()
        converter.convert(input_file, out)
        _assert_valid_docx(out)

    def test_all_features(self, tmp_path: Path) -> None:
        input_file = tmp_path / "full.html"
        input_file.write_text("""<html><body>
<h1>Full Document</h1>
<p>Hello <strong>world</strong></p>
<ul><li>Item</li></ul>
</body></html>""")
        out = tmp_path / "full.docx"
        converter = HTMLConverter()
        converter.convert(
            input_file,
            out,
            generate_toc=True,
            page_numbers=True,
            cover_page=True,
            title="Full",
            author="Test",
            doc_version="1.0",
        )
        _assert_valid_docx(out)
