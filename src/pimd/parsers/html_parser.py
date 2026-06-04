"""HTML parser that produces PiMD's intermediate document model."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, NavigableString, Tag

from pimd.exceptions import ParserError
from pimd.models import (
    Block,
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
from pimd.utils.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

_BLOCK_TAGS = frozenset(
    {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "pre",
        "blockquote",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "hr",
        "img",
        "div",
        "section",
        "article",
        "main",
        "header",
        "footer",
        "nav",
        "aside",
        "form",
    }
)


class HTMLParser:
    """Parse HTML content into PiMD's intermediate document model.

    Uses ``beautifulsoup4`` with the ``lxml`` parser under the hood.
    Supports the full range of HTML block and inline elements needed for
    professional document conversion.
    """

    def parse(self, content: str) -> Document:
        """Parse an HTML string into a :class:`Document`.

        Args:
            content: Raw HTML text.

        Returns:
            A :class:`Document` containing structured blocks.

        Raises:
            ParserError: If parsing fails unexpectedly.
        """
        try:
            soup = BeautifulSoup(content, "lxml")
        except Exception as exc:
            raise ParserError(f"HTML parsing failed: {exc}") from exc

        body = soup.body or soup
        blocks = self._parse_blocks(body)
        return Document(blocks=blocks)

    def parse_file(self, path: str | Path) -> Document:
        """Read and parse an HTML file.

        Args:
            path: Path to the ``.html`` file.

        Returns:
            A :class:`Document` containing structured blocks.
        """
        logger.debug("Parsing file: %s", path)
        content = Path(path).read_text(encoding="utf-8")
        return self.parse(content)

    # ------------------------------------------------------------------
    # Block-level parsing
    # ------------------------------------------------------------------

    def _parse_blocks(self, element: Tag) -> list[Block]:
        """Parse block-level children of *element* into a list of blocks."""
        blocks: list[Block] = []
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    blocks.append(Paragraph(spans=[Span(text=text)]))
                continue

            if not isinstance(child, Tag) or child.name is None:
                continue

            handler = self._BLOCK_DISPATCH.get(child.name)
            if handler is not None:
                result = handler(self, child)
                if result is not None:
                    if isinstance(result, list):
                        blocks.extend(result)
                    else:
                        blocks.append(result)
            else:
                logger.debug("Unrecognised block tag <%s>, treating as container", child.name)
                inner = self._parse_blocks(child)
                if inner:
                    blocks.extend(inner)

        return blocks

    @staticmethod
    def _extract_alignment(tag: Tag) -> str | None:
        style = tag.get("style", "")
        if style:
            for part in style.split(";"):
                part = part.strip().lower()
                if part.startswith("text-align:"):
                    val = part.split(":", 1)[1].strip()
                    if val in ("left", "center", "right", "justify"):
                        return val
        return None

    def _parse_heading(self, tag: Tag) -> Heading:
        level = int(tag.name[1])
        spans = self._inline_spans(tag)
        return Heading(level=level, spans=spans, alignment=self._extract_alignment(tag))

    def _parse_paragraph(self, tag: Tag) -> Paragraph:
        spans = self._inline_spans(tag)
        alignment = self._extract_alignment(tag)
        classes = tag.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()
        if not alignment and "subtitle" in classes:
            alignment = "center"
        return Paragraph(spans=spans, alignment=alignment)

    def _parse_pre(self, tag: Tag) -> CodeBlock:
        code_tag = tag.find("code", recursive=False) if tag.find("code") else None
        if code_tag is not None:
            code = code_tag.get_text()
            cls = code_tag.get("class", [])
            lang = cls[0] if cls else tag.get("class", [None])[0]
        else:
            code = tag.get_text()
            lang = tag.get("class", [None])[0]

        code = _strip_common_indent(code)

        return CodeBlock(code=code, language=lang)

    def _parse_blockquote(self, tag: Tag) -> Blockquote:
        children = self._parse_blocks(tag)
        return Blockquote(children=children)

    def _parse_bullet_list(self, tag: Tag) -> BulletList:
        items = self._parse_list_items(tag)
        return BulletList(items=items)

    def _parse_ordered_list(self, tag: Tag) -> OrderedList:
        items = self._parse_list_items(tag)
        start = 1
        if tag.get("start"):
            try:
                start = int(tag["start"])
            except (ValueError, TypeError):
                pass
        return OrderedList(items=items, start=start)

    def _parse_list_items(self, tag: Tag) -> list[ListItem]:
        items: list[ListItem] = []
        for li in tag.find_all("li", recursive=False):
            children = self._parse_blocks(li)
            items.append(ListItem(children=children))
        return items

    def _parse_table(self, tag: Tag) -> Table:
        rows: list[list[str]] = []
        header_texts: list[str] = []
        found_header = False

        for child in tag.children:
            if not isinstance(child, Tag):
                continue

            if child.name == "thead":
                found_header = True
                for tr in child.find_all("tr", recursive=False):
                    for th in tr.find_all(["th", "td"]):
                        header_texts.append(th.get_text(strip=True))

            elif child.name == "tbody":
                for tr in child.find_all("tr", recursive=False):
                    row = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    if row:
                        rows.append(row)

        # -- Fallback: no explicit thead/tbody — treat first <tr> with <th> as header
        if not found_header:
            all_trs = tag.find_all("tr", recursive=False)
            for i, tr in enumerate(all_trs):
                cells = tr.find_all(["th", "td"])
                row = [c.get_text(strip=True) for c in cells]
                if not row:
                    continue
                if i == 0 and all(c.name == "th" for c in cells if cells):
                    header_texts = row
                else:
                    rows.append(row)

        return Table(headers=header_texts, rows=rows)

    def _parse_horizontal_rule(self, tag: Tag) -> HorizontalRule:
        return HorizontalRule()

    def _parse_image(self, tag: Tag) -> Image:
        alt = tag.get("alt", "")
        url = tag.get("src", "")
        title = tag.get("title", None)
        return Image(alt=alt, url=url, title=title)

    def _parse_container(self, tag: Tag) -> list[Block]:
        classes = tag.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()
        classes = [c.lower() for c in classes]

        # -- Map known class patterns to block types --
        if "chapter-heading" in classes:
            spans = self._inline_spans(tag)
            return [Heading(level=2, spans=spans, alignment="center")]

        if "chapter-break" in classes:
            spans = self._inline_spans(tag)
            text = "".join(s.text for s in spans).strip()
            if text:
                return [Paragraph(spans=spans, alignment="center")]
            return [HorizontalRule()]

        if "subtitle" in classes:
            spans = self._inline_spans(tag)
            return [Paragraph(spans=spans, alignment="center")]

        if "dialogue" in classes:
            children = self._parse_blocks(tag)
            return [Blockquote(children=children)]

        if "description" in classes:
            children = self._parse_blocks(tag)
            return [Blockquote(children=children)]

        return self._parse_blocks(tag)

    def _parse_li_as_block(self, tag: Tag) -> list[Block]:
        children = self._parse_blocks(tag)
        return children

    # ------------------------------------------------------------------
    # Inline (span) parsing
    # ------------------------------------------------------------------

    def _inline_spans(
        self,
        element: Tag,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        code: bool = False,
        link_url: str | None = None,
    ) -> list[Span]:
        """Recursively parse inline content into a list of Spans.

        Tracks formatting state (bold, italic, underline, code, link_url)
        as it descends through inline tags.
        """
        spans: list[Span] = []
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child)
                if text:
                    spans.append(
                        Span(
                            text=text,
                            bold=bold,
                            italic=italic,
                            underline=underline,
                            code=code,
                            link_url=link_url,
                        )
                    )
                continue

            if not isinstance(child, Tag) or child.name is None:
                continue

            name = child.name

            if name in ("strong", "b"):
                sub = self._inline_spans(
                    child,
                    bold=True,
                    italic=italic,
                    underline=underline,
                    code=code,
                    link_url=link_url,
                )
                spans.extend(sub)
            elif name in ("em", "i"):
                sub = self._inline_spans(
                    child,
                    bold=bold,
                    italic=True,
                    underline=underline,
                    code=code,
                    link_url=link_url,
                )
                spans.extend(sub)
            elif name == "u":
                sub = self._inline_spans(
                    child,
                    bold=bold,
                    italic=italic,
                    underline=True,
                    code=code,
                    link_url=link_url,
                )
                spans.extend(sub)
            elif name == "code":
                sub = self._inline_spans(
                    child,
                    bold=bold,
                    italic=italic,
                    underline=underline,
                    code=True,
                    link_url=link_url,
                )
                spans.extend(sub)
            elif name == "a":
                url = child.get("href", "")
                sub = self._inline_spans(
                    child,
                    bold=bold,
                    italic=italic,
                    underline=underline,
                    code=code,
                    link_url=url,
                )
                spans.extend(sub)
            elif name == "img":
                alt = child.get("alt", "")
                src = child.get("src", "")
                spans.append(Span(text=alt, link_url=src))
            elif name == "br":
                spans.append(Span(text="\n"))
            elif name in ("span", "small", "mark", "del", "ins", "sub", "sup", "abbr", "cite"):
                sub = self._inline_spans(
                    child,
                    bold=bold,
                    italic=italic,
                    underline=underline,
                    code=code,
                    link_url=link_url,
                )
                spans.extend(sub)
            else:
                inner = self._inline_spans(
                    child,
                    bold=bold,
                    italic=italic,
                    underline=underline,
                    code=code,
                    link_url=link_url,
                )
                if inner:
                    spans.extend(inner)

        return spans

    _BLOCK_DISPATCH: dict[str, object] = {}


HTMLParser._BLOCK_DISPATCH = {
    "h1": HTMLParser._parse_heading,
    "h2": HTMLParser._parse_heading,
    "h3": HTMLParser._parse_heading,
    "h4": HTMLParser._parse_heading,
    "h5": HTMLParser._parse_heading,
    "h6": HTMLParser._parse_heading,
    "p": HTMLParser._parse_paragraph,
    "pre": HTMLParser._parse_pre,
    "blockquote": HTMLParser._parse_blockquote,
    "ul": HTMLParser._parse_bullet_list,
    "ol": HTMLParser._parse_ordered_list,
    "table": HTMLParser._parse_table,
    "hr": HTMLParser._parse_horizontal_rule,
    "img": HTMLParser._parse_image,
    "div": HTMLParser._parse_container,
    "section": HTMLParser._parse_container,
    "article": HTMLParser._parse_container,
    "main": HTMLParser._parse_container,
    "header": HTMLParser._parse_container,
    "footer": HTMLParser._parse_container,
    "nav": HTMLParser._parse_container,
    "aside": HTMLParser._parse_container,
    "form": HTMLParser._parse_container,
    "li": HTMLParser._parse_li_as_block,
}


def _strip_common_indent(code: str) -> str:
    """Remove common leading whitespace from multi-line code strings."""
    lines = code.splitlines()
    if not lines:
        return code
    indent = None
    for line in lines:
        stripped = line.lstrip()
        if stripped:
            leading = len(line) - len(stripped)
            if indent is None or leading < indent:
                indent = leading
    if indent and indent > 0:
        lines = [line[indent:] if len(line) >= indent else line for line in lines]
    return "\n".join(lines)
