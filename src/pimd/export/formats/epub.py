"""EPUB 3 renderer — generates valid EPUB 3.2 packages from the document model."""

from __future__ import annotations

import io
import os
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from lxml import etree

from pimd.models import (
    Block,
    Blockquote,
    BulletList,
    CodeBlock,
    Diagram,
    Document,
    EquationBlock,
    Heading,
    HorizontalRule,
    Image,
    ListItem,
    OrderedList,
    Paragraph,
    Span,
    Table,
)

EPUB_NAMESPACES = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ncx": "http://www.daisy.org/z3986/2005/ncx/",
    "xhtml": "http://www.w3.org/1999/xhtml",
    "epub": "http://www.idpf.org/2007/ops",
}

MIMETYPE = "application/epub+zip"
CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

DEFAULT_CSS = """
@namespace epub "http://www.idpf.org/2007/ops";
body {
  font-family: Georgia, 'Times New Roman', serif;
  line-height: 1.6;
  margin: 0 1em;
  color: #333;
}
h1, h2, h3, h4, h5, h6 {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  color: #1a1a2e;
  page-break-after: avoid;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}
h1 { font-size: 2em; }
h2 { font-size: 1.6em; }
h3 { font-size: 1.3em; }
h4 { font-size: 1.1em; }
p {
  margin: 0.5em 0;
  text-indent: 0;
}
code {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9em;
  background: #f4f4f4;
  padding: 0.1em 0.3em;
}
pre {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.85em;
  background: #f4f4f4;
  padding: 0.8em;
  border-left: 3px solid #1a1a2e;
  overflow-x: auto;
  white-space: pre-wrap;
}
blockquote {
  margin: 0.8em 0;
  padding: 0.5em 1em;
  border-left: 3px solid #ccc;
  color: #555;
  font-style: italic;
}
table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  font-size: 0.9em;
}
th, td {
  border: 1px solid #999;
  padding: 0.4em 0.6em;
  text-align: left;
}
th {
  background: #1a1a2e;
  color: white;
  font-weight: bold;
}
img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 1em auto;
}
figure {
  margin: 1em 0;
  text-align: center;
}
figcaption {
  font-size: 0.85em;
  color: #666;
  font-style: italic;
  margin-top: 0.3em;
}
ul, ol {
  margin: 0.5em 0;
  padding-left: 2em;
}
li {
  margin: 0.2em 0;
}
hr {
  border: none;
  border-top: 1px solid #ccc;
  margin: 1.5em 0;
}
.footnote {
  font-size: 0.85em;
  color: #666;
  border-top: 1px solid #ccc;
  margin-top: 2em;
  padding-top: 0.5em;
}
.callout {
  margin: 0.8em 0;
  padding: 0.5em 1em;
  border-left: 4px solid #1a1a2e;
  background: #f8f8ff;
}
.callout-title {
  font-weight: bold;
  margin-bottom: 0.3em;
}
.equation {
  text-align: center;
  margin: 1em 0;
  font-style: italic;
}
.equation-number {
  float: right;
  font-size: 0.9em;
  color: #666;
}
"""

COVER_CSS = """
body {
  margin: 0;
  padding: 0;
  background: #1a1a2e;
  color: white;
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100vh;
}
h1 {
  font-size: 3em;
  margin-bottom: 0.5em;
  color: white;
}
p {
  font-size: 1.2em;
  color: #ccc;
}
"""


class EpubRenderer:
    """Render PiMD documents to EPUB 3.2 format.

    Generates valid EPUB packages with XHTML content, CSS styling,
    table of contents (nav.xhtml + NCX), cover page, and embedded assets.
    """

    FORMAT_NAME = "epub"
    FORMAT_DESCRIPTION = "EPUB 3.2 e-book format"
    IMPLEMENTED = True

    def __init__(self, css_path: str | Path | None = None) -> None:
        self._css_path = Path(css_path) if css_path else None
        self._available = self._check_dependencies()
        self._figure_counter = 0
        self._footnote_counter = 0
        self._chapter_counter = 0

    @staticmethod
    def _check_dependencies() -> bool:
        try:
            import lxml  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def missing_dependencies(self) -> list[str]:
        deps: list[str] = []
        try:
            import lxml  # noqa: F401
        except ImportError:
            deps.append("lxml")
        return deps

    def render(
        self,
        document: Document,
        output_path: str | Path,
        **options: Any,
    ) -> Path:
        """Render a Document to an EPUB 3.2 file.

        Args:
            document: The document model to render.
            output_path: Destination path for the .epub file.
            **options: title, author, cover_image, css, language, etc.

        Returns:
            Path to the generated EPUB file.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        title = options.get("title", "Untitled")
        author = options.get("author", "Unknown")
        language = options.get("language", "en")
        cover_image = options.get("cover_image")
        epub_css = self._load_css(options.get("css"))

        # Reset counters
        self._figure_counter = 0
        self._footnote_counter = 0
        self._chapter_counter = 0

        # Build EPUB structure
        package_id = f"urn:uuid:{uuid.uuid4()}"
        epub_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Collect content chapters
        chapters = self._split_into_chapters(document)
        nav_points: list[dict[str, Any]] = []
        spine_items: list[str] = []

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # mimetype (uncompressed)
            zf.writestr("mimetype", MIMETYPE, compress_type=zipfile.ZIP_STORED)

            # META-INF/container.xml
            zf.writestr("META-INF/container.xml", CONTAINER_XML)

            # OEBPS/ directory
            zf.writestr("OEBPS/css/main.css", epub_css)
            zf.writestr("OEBPS/css/cover.css", COVER_CSS)

            # Cover page
            cover_html = self._render_cover_page(title, author, cover_image)
            zf.writestr("OEBPS/cover.xhtml", cover_html.encode("utf-8"))
            spine_items.append("cover.xhtml")

            # Navigation document
            nav_html = self._render_nav(title, chapters)
            zf.writestr("OEBPS/nav.xhtml", nav_html.encode("utf-8"))
            spine_items.append("nav.xhtml")

            # NCX (table of contents)
            ncx_xml = self._render_ncx(package_id, title, author, chapters)
            zf.writestr("OEBPS/toc.ncx", ncx_xml.encode("utf-8"))

            # Content chapters
            for i, chapter in enumerate(chapters):
                filename = f"chapter_{i + 1:04d}.xhtml"
                html = self._render_chapter(chapter, i + 1)
                zf.writestr(f"OEBPS/{filename}", html.encode("utf-8"))
                spine_items.append(filename)
                nav_points.append({
                    "id": f"nav_{i + 1}",
                    "label": chapter.get("title", f"Chapter {i + 1}"),
                    "src": filename,
                    "play_order": i + 2,
                })

            # Content OPF
            opf_xml = self._render_opf(
                package_id=package_id,
                title=title,
                author=author,
                language=language,
                date=epub_date,
                spine_items=spine_items,
                nav_points=nav_points,
            )
            zf.writestr("OEBPS/content.opf", opf_xml.encode("utf-8"))

        buf.seek(0)
        out.write_bytes(buf.getvalue())
        return out

    def render_to_bytes(self, document: Document, **options: Any) -> bytes:
        """Render a Document to EPUB bytes without writing to disk."""
        buf = io.BytesIO()
        # Write to a temp path, then read back
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            self.render(document, tmp_path, **options)
            buf.write(Path(tmp_path).read_bytes())
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        buf.seek(0)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_css(self, css_opt: str | Path | None) -> str:
        if css_opt:
            try:
                return Path(css_opt).read_text(encoding="utf-8")
            except (OSError, FileNotFoundError):
                pass
        if self._css_path and self._css_path.exists():
            return self._css_path.read_text(encoding="utf-8")
        return DEFAULT_CSS

    def _split_into_chapters(self, document: Document) -> list[dict[str, Any]]:
        """Split document blocks into chapters based on h1/h2 headings."""
        chapters: list[dict[str, Any]] = []
        current: dict[str, Any] = {"title": "Preamble", "blocks": []}

        for block in document.blocks:
            if isinstance(block, Heading) and block.level <= 2:
                if current["blocks"]:
                    chapters.append(current)
                current = {"title": block.plain_text(), "blocks": []}
            current["blocks"].append(block)

        if current["blocks"]:
            chapters.append(current)

        return chapters

    def _render_cover_page(
        self, title: str, author: str, cover_image: str | None
    ) -> str:
        img_tag = ""
        if cover_image:
            img_tag = f'<img src="{cover_image}" alt="Cover" style="max-width:60%;"/>'

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>Cover</title>
  <link rel="stylesheet" type="text/css" href="css/cover.css"/>
  <meta charset="utf-8"/>
</head>
<body>
  <section epub:type="cover">
    {img_tag}
    <h1>{self._escape(title)}</h1>
    <p>{self._escape(author)}</p>
  </section>
</body>
</html>"""

    def _render_nav(self, title: str, chapters: list[dict[str, Any]]) -> str:
        items = ""
        for i, ch in enumerate(chapters):
            fn = f"chapter_{i + 1:04d}.xhtml"
            items += (
                f'    <li><a href="{fn}">{self._escape(ch["title"])}</a></li>\n'
            )

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>{self._escape(title)} - Table of Contents</title>
  <meta charset="utf-8"/>
</head>
<body>
  <nav epub:type="toc">
    <h1>Table of Contents</h1>
    <ol>
{items}
    </ol>
  </nav>
</body>
</html>"""

    def _render_ncx(
        self,
        package_id: str,
        title: str,
        author: str,
        chapters: list[dict[str, Any]],
    ) -> str:
        nav_map = ""
        for i, ch in enumerate(chapters):
            play_order = i + 2
            fn = f"chapter_{i + 1:04d}.xhtml"
            nav_map += f"""
    <navPoint id="nav_{i + 1}" playOrder="{play_order}">
      <navLabel>
        <text>{self._escape(ch['title'])}</text>
      </navLabel>
      <content src="{fn}"/>
    </navPoint>"""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{self._escape(package_id)}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>{self._escape(title)}</text>
  </docTitle>
  <docAuthor>
    <text>{self._escape(author)}</text>
  </docAuthor>
  <navMap>
    <navPoint id="nav_cover" playOrder="1">
      <navLabel>
        <text>Cover</text>
      </navLabel>
      <content src="cover.xhtml"/>
    </navPoint>
    {nav_map}
  </navMap>
</ncx>"""

    def _render_opf(
        self,
        package_id: str,
        title: str,
        author: str,
        language: str,
        date: str,
        spine_items: list[str],
        nav_points: list[dict[str, Any]],
    ) -> str:
        manifest = ""
        spine = ""
        guide = ""

        for item in spine_items:
            media_type = "application/xhtml+xml"
            manifest += f'    <item id="{item}" href="{item}" media-type="{media_type}"/>\n'
            spine += f'    <itemref idref="{item}"/>\n'

        manifest += (
            '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" '
            'properties="nav"/>\n'
        )
        manifest += (
            '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
        )
        manifest += (
            '    <item id="css" href="css/main.css" media-type="text/css"/>\n'
        )
        manifest += (
            '    <item id="cover-css" href="css/cover.css" media-type="text/css"/>\n'
        )

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf"
         xmlns:dc="http://purl.org/dc/elements/1.1/"
         version="3.0"
         unique-identifier="book-id"
         prefix="rendition: http://www.idpf.org/vocab/rendition/#">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">{self._escape(package_id)}</dc:identifier>
    <dc:title>{self._escape(title)}</dc:title>
    <dc:creator id="author">{self._escape(author)}</dc:creator>
    <dc:language>{self._escape(language)}</dc:language>
    <dc:date>{date}</dc:date>
    <meta property="dcterms:modified">{date}</meta>
    <meta property="rendition:layout">reflowable</meta>
    <meta property="rendition:spread">auto</meta>
  </metadata>
  <manifest>
{manifest}  </manifest>
  <spine toc="ncx">
{spine}  </spine>
  <guide>
    <reference type="cover" title="Cover" href="cover.xhtml"/>
    <reference type="toc" title="Table of Contents" href="nav.xhtml"/>
  </guide>
</package>"""

    def _render_chapter(self, chapter: dict[str, Any], number: int) -> str:
        body_parts: list[str] = []
        for block in chapter.get("blocks", []):
            html = self._render_block_to_html(block)
            if html:
                body_parts.append(html)

        title = self._escape(chapter.get("title", f"Chapter {number}"))

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="css/main.css"/>
  <meta charset="utf-8"/>
</head>
<body>
  <section epub:type="chapter">
    {"".join(body_parts)}
  </section>
</body>
</html>"""

    def _render_block_to_html(self, block: Block) -> str:
        if isinstance(block, Heading):
            level = min(block.level, 6)
            text = self._render_spans_html(block.spans)
            return f"<h{level}>{text}</h{level}>\n"

        if isinstance(block, Paragraph):
            text = self._render_spans_html(block.spans)
            return f"<p>{text}</p>\n"

        if isinstance(block, CodeBlock):
            lang = f' class="language-{block.language}"' if block.language else ""
            code = self._escape(block.code)
            return f"<pre><code{lang}>{code}</code></pre>\n"

        if isinstance(block, Blockquote):
            children = "".join(
                self._render_block_to_html(c) for c in block.children
            )
            return f"<blockquote>{children}</blockquote>\n"

        if isinstance(block, BulletList):
            items = "".join(
                self._render_list_item_html(item) for item in block.items
            )
            return f"<ul>{items}</ul>\n"

        if isinstance(block, OrderedList):
            items = "".join(
                self._render_list_item_html(item) for item in block.items
            )
            return f"<ol>{items}</ol>\n"

        if isinstance(block, Table):
            return self._render_table_html(block)

        if isinstance(block, HorizontalRule):
            return "<hr/>\n"

        if isinstance(block, Image):
            alt = self._escape(block.alt)
            src = self._escape(block.url)
            title_attr = f' title="{self._escape(block.title)}"' if block.title else ""
            return f'<figure><img src="{src}" alt="{alt}"{title_attr}/></figure>\n'

        if isinstance(block, Diagram):
            alt = self._escape(block.alt)
            if block.svg_bytes:
                try:
                    svg_text = block.svg_bytes.decode("utf-8")
                    return f"<figure>{svg_text}</figure>\n"
                except UnicodeDecodeError:
                    pass
            if block.png_bytes:
                return (
                    f'<figure><img src="data:image/png;base64,'
                    f'{__import__("base64").b64encode(block.png_bytes).decode()}'
                    f'" alt="{alt}"/></figure>\n'
                )
            return f"<p><em>[Diagram: {alt}]</em></p>\n"

        if isinstance(block, EquationBlock):
            if block.omml is not None:
                return f'<p class="equation">[Equation]</p>\n'
            latex = self._escape(block.latex)
            num = f' <span class="equation-number">({block.number})</span>' if block.number is not None else ""
            return f'<p class="equation">\\({latex}\\){num}</p>\n'

        if hasattr(block, "type") and hasattr(block, "title"):
            callout_type = getattr(block, "type", None)
            callout_title = getattr(block, "title", "")
            content_lines = getattr(block, "content_lines", []) or getattr(block, "content", [])
            lines_html = "".join(
                f"<p>{self._escape(str(l))}</p>" for l in content_lines
            )
            return (
                f'<div class="callout">'
                f'<p class="callout-title">{self._escape(str(callout_title))}</p>'
                f"{lines_html}</div>\n"
            )

        if isinstance(block, ListItem):
            return self._render_list_item_html(block)

        return ""

    def _render_spans_html(self, spans: list[Span]) -> str:
        parts = []
        for span in spans:
            text = self._escape(span.text)
            if span.math and not text:
                text = self._escape(span.math)
            if span.code:
                text = f"<code>{text}</code>"
            if span.link_url:
                text = f'<a href="{self._escape(span.link_url)}">{text}</a>'
            if span.bold:
                text = f"<strong>{text}</strong>"
            if span.italic:
                text = f"<em>{text}</em>"
            if span.underline:
                text = f"<u>{text}</u>"
            if span.superscript:
                text = f"<sup>{text}</sup>"
            if span.subscript:
                text = f"<sub>{text}</sub>"
            parts.append(text)
        return "".join(parts)

    def _render_list_item_html(self, item: ListItem) -> str:
        children = "".join(
            self._render_block_to_html(c) for c in item.children
        )
        return f"<li>{children}</li>\n"

    def _render_table_html(self, block: Table) -> str:
        parts = ["<table>\n"]
        if block.headers:
            parts.append("<thead>\n<tr>")
            for h in block.headers:
                parts.append(f"<th>{self._escape(h)}</th>")
            parts.append("</tr>\n</thead>\n")
        parts.append("<tbody>\n")
        for row in block.rows:
            parts.append("<tr>")
            for cell in row:
                parts.append(f"<td>{self._escape(cell)}</td>")
            parts.append("</tr>\n")
        parts.append("</tbody>\n</table>\n")
        return "".join(parts)

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )


def validate_epub(epub_path: str | Path) -> list[str]:
    """Basic EPUB validation — checks package structure and well-formedness.

    Args:
        epub_path: Path to the EPUB file to validate.

    Returns:
        List of validation issues (empty if valid).
    """
    issues: list[str] = []
    path = Path(epub_path)
    if not path.exists():
        return ["EPUB file not found"]

    try:
        with zipfile.ZipFile(path, "r") as zf:
            # Check mimetype
            if "mimetype" not in zf.namelist():
                issues.append("Missing mimetype file")
            else:
                mt = zf.read("mimetype").decode("utf-8").strip()
                if mt != MIMETYPE:
                    issues.append(f"Invalid mimetype: {mt}")

            # Check META-INF/container.xml
            if "META-INF/container.xml" not in zf.namelist():
                issues.append("Missing META-INF/container.xml")

            # Check content.opf
            if "OEBPS/content.opf" not in zf.namelist():
                issues.append("Missing OEBPS/content.opf")

            # Validate OPF XML
            if "OEBPS/content.opf" in zf.namelist():
                try:
                    etree.parse(io.BytesIO(zf.read("OEBPS/content.opf")))
                except Exception as e:
                    issues.append(f"Invalid content.opf: {e}")

            # Check nav.xhtml
            if "OEBPS/nav.xhtml" not in zf.namelist():
                issues.append("Missing nav.xhtml (EPUB3 navigation)")

            # Check referenced items exist
            if "OEBPS/content.opf" in zf.namelist():
                try:
                    opf = etree.parse(io.BytesIO(zf.read("OEBPS/content.opf")))
                    ns = {"opf": "http://www.idpf.org/2007/opf"}
                    for item in opf.findall(".//opf:item", ns):
                        href = item.get("href", "")
                        full_path = f"OEBPS/{href}"
                        if full_path not in zf.namelist():
                            issues.append(f"Missing referenced item: {full_path}")
                except Exception:
                    pass

    except zipfile.BadZipFile:
        issues.append("Invalid ZIP file")
    except Exception as e:
        issues.append(f"Validation error: {e}")

    return issues
