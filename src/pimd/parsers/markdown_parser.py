"""Low-level Markdown parser that produces an intermediate document model."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from pimd.exceptions import ParserError
from pimd.models import (
    Block,
    Blockquote,
    BulletList,
    CodeBlock,
    Diagram,
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
    from collections.abc import Sequence

logger = get_logger(__name__)


class MarkdownParser:
    """Parse Markdown content into PiMD's intermediate document model.

    Uses ``markdown-it-py`` under the hood with the default CommonMark preset,
    plus superscript (^...^) and subscript (~...~) via mdit-py-plugins.
    """

    def __init__(self) -> None:
        self._md: MarkdownIt = MarkdownIt("commonmark", {"maxNesting": 100})
        self._md.enable(["table", "linkify"])
        try:
            from mdit_py_plugins.subscript import sub_plugin
            from mdit_py_plugins.superscript import superscript_plugin

            self._md.use(superscript_plugin).use(sub_plugin)
        except ImportError:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, content: str) -> Document:
        """Parse a Markdown string into a :class:`Document`.

        Args:
            content: Raw Markdown text.

        Returns:
            A :class:`Document` containing structured blocks.

        Raises:
            ParserError: If parsing fails unexpectedly.
        """
        try:
            tokens: list[Token] = self._md.parse(content)
        except Exception as exc:
            raise ParserError(f"Markdown parsing failed: {exc}") from exc

        blocks = self._to_blocks(tokens)
        return Document(blocks=blocks)

    def parse_file(self, path: str | Path) -> Document:
        """Read and parse a Markdown file.

        Args:
            path: Path to the ``.md`` file.

        Returns:
            A :class:`Document` containing structured blocks.
        """
        logger.debug("Parsing file: %s", path)
        content = Path(path).read_text(encoding="utf-8")
        return self.parse(content)

    # ------------------------------------------------------------------
    # Block-level parsing
    # ------------------------------------------------------------------

    def _to_blocks(
        self, tokens: Sequence[Token], start: int = 0, end: int | None = None
    ) -> list[Block]:
        end = end or len(tokens)
        blocks: list[Block] = []
        i = start
        while i < end:
            token = tokens[i]

            if token.nesting == -1:
                i += 1
                continue

            handler = self._BLOCK_DISPATCH.get(token.type)
            if handler is not None:
                block, consumed = handler(self, tokens, i)
                if block is not None:
                    blocks.append(block)
                i += consumed
            else:
                i += 1

        return blocks

    # -- heading -----------------------------------------------------------

    def _parse_heading(self, tokens: Sequence[Token], i: int) -> tuple[Block | None, int]:
        level = int(tokens[i].tag[1])
        inline = tokens[i + 1]
        spans = self._parse_spans(inline)
        return Heading(level=level, spans=spans), 3

    # -- paragraph ---------------------------------------------------------

    def _parse_paragraph(self, tokens: Sequence[Token], i: int) -> tuple[Block | None, int]:
        inline = tokens[i + 1]
        spans = self._parse_spans(inline)
        return Paragraph(spans=spans), 3

    # -- standalone inline -------------------------------------------------

    def _parse_standalone_inline(self, tokens: Sequence[Token], i: int) -> tuple[Block | None, int]:
        spans = self._parse_spans(tokens[i])
        return Paragraph(spans=spans), 1

    # -- code blocks -------------------------------------------------------

    _TITLE_RE = re.compile(r'title\s*=\s*"([^"]*)"')

    def _parse_fence(self, tokens: Sequence[Token], i: int) -> tuple[Block | None, int]:
        info = tokens[i].info.strip() if tokens[i].info else None
        code = tokens[i].content

        # Extract title="..." from info string (e.g. ```mermaid title="Flow")
        title: str | None = None
        language: str | None = None
        if info:
            title_match = self._TITLE_RE.search(info)
            if title_match:
                title = title_match.group(1)
                language = self._TITLE_RE.sub("", info).strip()
            else:
                language = info

        # Check if this is a known diagram language (via PiDraw)
        if language and self._is_diagram_language(language):
            caption = title or language.title()
            return Diagram(
                alt=f"{language} diagram",
                source=code,
                language=language,
                title=title,
                caption=caption,
            ), 1

        return CodeBlock(code=code, language=info), 1

    @staticmethod
    def _is_diagram_language(language: str) -> bool:
        """Check if *language* is a supported diagram language.

        Uses PiDraw's list of supported languages with alias resolution.
        """
        try:
            from pimd.diagrams.pidraw_integration import (
                _normalize_language,
            )
            normalized = _normalize_language(language)
            from pimd.diagrams.pidraw_integration import (
                get_supported_languages,
            )
            supported = get_supported_languages()
            return normalized in supported
        except Exception:
            return False

    def _parse_code_block(self, tokens: Sequence[Token], i: int) -> tuple[Block | None, int]:
        return CodeBlock(code=tokens[i].content), 1

    # -- horizontal rule ---------------------------------------------------

    def _parse_hr(self, tokens: Sequence[Token], i: int) -> tuple[Block | None, int]:
        return HorizontalRule(), 1

    # -- blockquote --------------------------------------------------------

    def _parse_blockquote(self, tokens: Sequence[Token], i: int) -> tuple[Block | None, int]:
        end = self._find_close(tokens, i + 1, "blockquote_open", "blockquote_close")
        children = self._to_blocks(tokens, i + 1, end)
        consumed = end - i + 1
        return Blockquote(children=children), consumed

    # -- lists -------------------------------------------------------------

    def _parse_bullet_list(self, tokens: Sequence[Token], i: int) -> tuple[Block | None, int]:
        end = self._find_close(tokens, i + 1, "bullet_list_open", "bullet_list_close")
        items = self._parse_list_items(tokens, i + 1, end)
        consumed = end - i + 1
        return BulletList(items=items), consumed

    def _parse_ordered_list(self, tokens: Sequence[Token], i: int) -> tuple[Block | None, int]:
        end = self._find_close(tokens, i + 1, "ordered_list_open", "ordered_list_close")
        items = self._parse_list_items(tokens, i + 1, end)
        start_num = 1
        if tokens[i].attrs is not None:
            start_num = int(tokens[i].attrs.get("start", 1))
        consumed = end - i + 1
        return OrderedList(items=items, start=start_num), consumed

    def _parse_list_items(self, tokens: Sequence[Token], start: int, end: int) -> list[ListItem]:
        items: list[ListItem] = []
        i = start
        while i < end:
            token = tokens[i]
            if token.type == "list_item_open":
                item_end = self._find_close(tokens, i + 1, "list_item_open", "list_item_close")
                children = self._to_blocks(tokens, i + 1, item_end)
                items.append(ListItem(children=children))
                i = item_end + 1
            else:
                i += 1
        return items

    # -- table -------------------------------------------------------------

    def _parse_table(self, tokens: Sequence[Token], i: int) -> tuple[Block | None, int]:
        end = self._find_close(tokens, i + 1, "table_open", "table_close")
        header_rows: list[list[str]] = []
        rows: list[list[str]] = []
        current_row: list[str] = []
        in_header = True

        j = i + 1
        while j < end:
            token = tokens[j]
            if token.type == "thead_open":
                in_header = True
                j += 1
            elif token.type == "tbody_open":
                in_header = False
                j += 1
            elif token.type == "tr_open":
                current_row = []
                j += 1
            elif token.type == "tr_close":
                if current_row:
                    (header_rows if in_header else rows).append(current_row)
                current_row = []
                j += 1
            elif token.type in ("th_open", "td_open"):
                j += 1
                if j < end and tokens[j].type == "inline":
                    current_row.append(tokens[j].content)
                    j += 1
                j += 1
            elif token.type in ("th_close", "td_close", "thead_close", "tbody_close"):
                j += 1
            else:
                j += 1

        consumed = end - i + 1
        headers = header_rows[0] if header_rows and header_rows[0] else []
        return Table(headers=headers, rows=rows), consumed

    # -- block-level image -------------------------------------------------

    def _parse_block_image(self, tokens: Sequence[Token], i: int) -> tuple[Block | None, int]:
        attrs = tokens[i].attrs or {}
        url: str = attrs.get("src", "") or ""
        alt: str = tokens[i].content or ""
        title: str | None = attrs.get("title", None) or None
        return Image(alt=alt, url=url, title=title), 1

    # ------------------------------------------------------------------
    # Inline (span) parsing
    # ------------------------------------------------------------------

    def _parse_spans(self, token: Token) -> list[Span]:
        children: list[Token] = token.children or []
        return self._parse_inline_children(children)

    def _parse_inline_children(
        self, children: Sequence[Token], start: int = 0, end: int | None = None
    ) -> list[Span]:
        end = end or len(children)
        spans: list[Span] = []
        i = start
        while i < end:
            child = children[i]

            if child.type == "text":
                spans.append(Span(text=child.content))
                i += 1

            elif child.type == "strong_open":
                close = self._find_inline_close(children, i, "strong_open", "strong_close")
                inner = self._parse_inline_children(children, i + 1, close)
                for s in inner:
                    s.bold = True
                spans.extend(inner)
                i = close + 1

            elif child.type == "em_open":
                close = self._find_inline_close(children, i, "em_open", "em_close")
                inner = self._parse_inline_children(children, i + 1, close)
                for s in inner:
                    s.italic = True
                spans.extend(inner)
                i = close + 1

            elif child.type == "sup_open":
                close = self._find_inline_close(children, i, "sup_open", "sup_close")
                inner = self._parse_inline_children(children, i + 1, close)
                for s in inner:
                    s.superscript = True
                spans.extend(inner)
                i = close + 1

            elif child.type == "sub_open":
                close = self._find_inline_close(children, i, "sub_open", "sub_close")
                inner = self._parse_inline_children(children, i + 1, close)
                for s in inner:
                    s.subscript = True
                spans.extend(inner)
                i = close + 1

            elif child.type == "code_inline":
                spans.append(Span(text=child.content, code=True))
                i += 1

            elif child.type == "link_open":
                url: str = ""
                if child.attrs is not None:
                    url = child.attrs.get("href", "") or ""
                close = self._find_inline_close(children, i, "link_open", "link_close")
                inner = self._parse_inline_children(children, i + 1, close)
                for s in inner:
                    s.link_url = url
                spans.extend(inner)
                i = close + 1

            elif child.type == "image":
                attrs = child.attrs or {}
                img_url: str = attrs.get("src", "") or ""
                alt: str = child.content or ""
                spans.append(Span(text=alt, link_url=img_url))
                i += 1

            elif child.type in ("softbreak", "hardbreak"):
                spans.append(Span(text=" "))
                i += 1

            else:
                if child.content:
                    spans.append(Span(text=child.content))
                i += 1

        return spans

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_close(tokens: Sequence[Token], start: int, open_type: str, close_type: str) -> int:
        depth = 1
        i = start
        while i < len(tokens) and depth > 0:
            t = tokens[i]
            if t.type == open_type:
                depth += 1
            elif t.type == close_type:
                depth -= 1
            if depth > 0:
                i += 1
        return i

    @staticmethod
    def _find_inline_close(
        children: Sequence[Token], start: int, open_type: str, close_type: str
    ) -> int:
        depth = 1
        i = start + 1
        while i < len(children) and depth > 0:
            if children[i].type == open_type:
                depth += 1
            elif children[i].type == close_type:
                depth -= 1
            if depth > 0:
                i += 1
        return i

    # ------------------------------------------------------------------
    # Dispatch table
    # ------------------------------------------------------------------

    _BLOCK_DISPATCH: dict[str, Any] = {}  # filled in at end of class


MarkdownParser._BLOCK_DISPATCH = {
    "heading_open": MarkdownParser._parse_heading,
    "paragraph_open": MarkdownParser._parse_paragraph,
    "inline": MarkdownParser._parse_standalone_inline,
    "fence": MarkdownParser._parse_fence,
    "code_block": MarkdownParser._parse_code_block,
    "hr": MarkdownParser._parse_hr,
    "blockquote_open": MarkdownParser._parse_blockquote,
    "bullet_list_open": MarkdownParser._parse_bullet_list,
    "ordered_list_open": MarkdownParser._parse_ordered_list,
    "table_open": MarkdownParser._parse_table,
    "image": MarkdownParser._parse_block_image,
}
