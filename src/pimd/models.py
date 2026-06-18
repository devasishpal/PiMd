"""Intermediate document model shared between parsers and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field

# ======================================================================
# Inline content
# ======================================================================


@dataclass
class Span:
    """A single formatted text span within a paragraph or heading.

    When *math* is set, the span represents an inline equation and
    *text* should be empty. *omml* holds the native Word equation
    XML element if already rendered.
    """

    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    code: bool = False
    link_url: str | None = None
    superscript: bool = False
    subscript: bool = False
    math: str | None = None
    math_display: bool = False
    png: bytes | None = None


# ======================================================================
# Block-level content
# ======================================================================


@dataclass
class Heading:
    """A section heading (levels 1-6)."""

    level: int
    spans: list[Span]
    alignment: str | None = None

    def plain_text(self) -> str:
        return "".join(s.text for s in self.spans)


@dataclass
class Paragraph:
    """A plain paragraph with inline formatting."""

    spans: list[Span]
    alignment: str | None = None

    def plain_text(self) -> str:
        return "".join(s.text for s in self.spans)


@dataclass
class CodeBlock:
    """A fenced or indented code block."""

    code: str
    language: str | None = None

    def plain_text(self) -> str:
        return self.code


@dataclass
class Blockquote:
    """A block quotation containing nested blocks."""

    children: list[Block] = field(default_factory=list)

    def plain_text(self) -> str:
        return "\n".join(
            _plain_text(child) for child in self.children
        )


@dataclass
class ListItem:
    """A single item inside a list, containing nested blocks."""

    children: list[Block] = field(default_factory=list)

    def plain_text(self) -> str:
        return " ".join(
            _plain_text(child) for child in self.children
        )


@dataclass
class OrderedList:
    """An ordered (numbered) list."""

    items: list[ListItem] = field(default_factory=list)
    start: int = 1

    def plain_text(self) -> str:
        return "\n".join(
            f"{self.start + i}. {item.plain_text()}"
            for i, item in enumerate(self.items)
        )


@dataclass
class BulletList:
    """An unordered (bulleted) list."""

    items: list[ListItem] = field(default_factory=list)

    def plain_text(self) -> str:
        return "\n".join(
            f"- {item.plain_text()}" for item in self.items
        )


@dataclass
class Table:
    """A grid table with an optional header row."""

    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    def plain_text(self) -> str:
        lines: list[str] = []
        if self.headers:
            lines.append(" | ".join(self.headers))
            lines.append("-+-".join("-" * len(h) for h in self.headers))
        for row in self.rows:
            lines.append(" | ".join(row))
        return "\n".join(lines)


@dataclass
class HorizontalRule:
    """A thematic break / horizontal rule."""

    def plain_text(self) -> str:
        return "---"


@dataclass
class Image:
    """A block-level image with alt text and URL."""

    alt: str
    url: str
    title: str | None = None

    def plain_text(self) -> str:
        return self.alt or f"[Image: {self.url}]"


@dataclass
class Diagram:
    """A rendered diagram block embedded in the document.

    Properties mirror the document AST DiagramNode concept:
    - language: diagram language (mermaid, plantuml, dot, d2, etc.)
    - source: raw diagram source code
    - title: optional title from info string (``title="..."``)
    - svg: SVG string content
    - png: PNG bytes (for DOCX embedding)
    - width / height: rendered dimensions
    - caption: auto-generated figure caption
    - figure_number: auto-incremented figure number
    - error: rendering error message (if any)
    """

    alt: str
    png_bytes: bytes = b""
    source: str = ""
    language: str = ""
    title: str | None = None
    caption: str | None = None
    svg_bytes: bytes | None = None
    width: int | None = None
    height: int | None = None
    figure_number: int | None = None
    error: str | None = None

    def plain_text(self) -> str:
        parts: list[str] = []
        if self.caption:
            parts.append(self.caption)
        if self.alt:
            parts.append(self.alt)
        if self.error:
            parts.append(f"[Error: {self.error}]")
        return " | ".join(parts) if parts else f"[Diagram: {self.language}]"


@dataclass
class EquationBlock:
    """A display (block) equation rendered as PNG image."""

    latex: str
    display: bool = True
    png: bytes | None = None
    label: str | None = None
    number: int | None = None
    error: str | None = None

    def plain_text(self) -> str:
        text = f"[Equation: {self.latex[:60]}"
        if self.number is not None:
            text += f" ({self.number})"
        return text + "]"


try:
    from pimd.callouts import CalloutBlock as Callout
except ImportError:
    from dataclasses import dataclass as _dataclass

    @_dataclass
    class Callout:
        type: object = None  # type: ignore
        title: str = ""
        content_lines: list[str] = field(default_factory=list)
        color: str = ""
        icon: str = ""

        def plain_text(self) -> str:
            parts: list[str] = []
            if self.title:
                parts.append(self.title)
            if self.content_lines:
                parts.extend(self.content_lines)
            return "\n".join(parts)


def _plain_text(block: Block) -> str:
    """Safe helper: call plain_text on any block, or return empty string."""
    if hasattr(block, "plain_text"):
        return block.plain_text()
    return str(block) if block is not None else ""


Block = (
    Heading
    | Paragraph
    | CodeBlock
    | Blockquote
    | ListItem
    | OrderedList
    | BulletList
    | Table
    | HorizontalRule
    | Image
    | Diagram
    | EquationBlock
    | Callout
)


# ======================================================================
# Document
# ======================================================================


@dataclass
class Document:
    """Root document model containing an ordered sequence of blocks."""

    blocks: list[Block] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.blocks)

    def __len__(self) -> int:
        return len(self.blocks)

    def __iter__(self):  # noqa: ANN201
        return iter(self.blocks)

    def __getitem__(self, index: int) -> Block:
        return self.blocks[index]


# ======================================================================
# DocumentStatistics
# ======================================================================


@dataclass
class DocumentStatistics:
    """Aggregated statistics collected during a conversion run."""

    heading_count: int = 0
    paragraph_count: int = 0
    code_block_count: int = 0
    table_count: int = 0
    image_count: int = 0
    list_item_count: int = 0
    equation_count: int = 0
    word_count: int = 0

    @property
    def total_blocks(self) -> int:
        return (
            self.heading_count
            + self.paragraph_count
            + self.code_block_count
            + self.table_count
            + self.image_count
            + self.list_item_count
        )
