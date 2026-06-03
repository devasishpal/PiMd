"""Markdown → DOCX conversion orchestration."""

from pathlib import Path

from pimd.diagrams import DiagramEngine, DiagramRegistry
from pimd.diagrams.renderers import (
    AsciiRenderer,
    D2Renderer,
    GraphvizRenderer,
    MermaidRenderer,
    PlantUMLRenderer,
    SvgRenderer,
)
from pimd.equations import EquationEngine
from pimd.equations.cache import MemoryEquationCache
from pimd.equations.models import EquationConfig
from pimd.exceptions import ConversionError
from pimd.models import (
    Block,
    Blockquote,
    BulletList,
    CodeBlock,
    Diagram,
    Document,
    DocumentStatistics,
    EquationBlock,
    Heading,
    Image,
    OrderedList,
    Paragraph,
    Table,
)
from pimd.parsers.markdown_parser import MarkdownParser
from pimd.renderers.docx_renderer import DocxRenderer
from pimd.themes import ProfessionalTheme
from pimd.themes.base import Theme
from pimd.utils.logging import get_logger

logger = get_logger(__name__)


class MarkdownConverter:
    """Convert Markdown files or strings to DOCX documents.

    Usage::

        converter = MarkdownConverter()
        converter.convert("input.md", "output.docx")
        converter.convert_text("# Hello", "hello.docx")

    Parameters
    ----------
    theme : Theme, optional
        Visual theme for the generated DOCX. Defaults to ProfessionalTheme.
    diagram_engine : DiagramEngine, optional
        Diagram rendering engine. If provided, diagram code blocks
        (mermaid, plantuml, dot, etc.) are automatically rendered.
    """

    def __init__(
        self,
        theme: Theme | None = None,
        diagram_engine: DiagramEngine | None = None,
        equation_engine: EquationEngine | None = None,
    ) -> None:
        self._parser = MarkdownParser()
        self._renderer = DocxRenderer(theme or ProfessionalTheme())
        self._statistics: DocumentStatistics = DocumentStatistics()
        self._diagram_engine = diagram_engine or _default_diagram_engine()
        self._equation_engine = equation_engine or _default_equation_engine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(
        self,
        input_file: str | Path,
        output_file: str | Path,
        *,
        generate_toc: bool = False,
        page_numbers: bool = False,
        header_text: str | None = None,
        footer_text: str | None = None,
        cover_page: bool = False,
        title: str | None = None,
        author: str | None = None,
        company: str | None = None,
        subject: str | None = None,
        keywords: list[str] | None = None,
        doc_version: str | None = None,
    ) -> None:
        """Convert a Markdown file to a DOCX document.

        Args:
            input_file: Path to the input ``.md`` file.
            output_file: Path where the output ``.docx`` will be written.
            generate_toc: Insert a Word table of contents field.
            page_numbers: Add page numbers to every page footer.
            header_text: Repeating header text for every page.
            footer_text: Repeating footer text (ignored if page_numbers=True).
            cover_page: Prepend a title page with title, author, version.
            title: Document title (metadata + cover page).
            author: Document author (metadata + cover page).
            company: Company / organisation name (metadata).
            subject: Document subject (metadata).
            keywords: List of keywords (metadata).
            doc_version: Version string shown on the cover page.

        Raises:
            ConversionError: If the input file does not exist or conversion fails.
        """
        src = Path(input_file)
        if not src.exists():
            raise ConversionError(f"Input file not found: {input_file}")

        logger.info("Converting: %s \u2192 %s", src, output_file)
        print("Converting Markdown\u2026")

        print("Parsing\u2026")
        content = src.read_text(encoding="utf-8")
        document = self._parser.parse(content)
        self._process_diagrams(document)
        self._process_equations(document)

        print("Rendering DOCX\u2026")
        self._collect_statistics(document)
        self._renderer.render(
            document,
            output_file,
            generate_toc=generate_toc,
            page_numbers=page_numbers,
            header_text=header_text,
            footer_text=footer_text,
            cover_page=cover_page,
            title=title,
            author=author,
            company=company,
            subject=subject,
            keywords=keywords,
            doc_version=doc_version,
        )

        print("Done.")

    def convert_text(
        self,
        markdown_text: str,
        output_file: str | Path,
        *,
        generate_toc: bool = False,
        page_numbers: bool = False,
        header_text: str | None = None,
        footer_text: str | None = None,
        cover_page: bool = False,
        title: str | None = None,
        author: str | None = None,
        company: str | None = None,
        subject: str | None = None,
        keywords: list[str] | None = None,
        doc_version: str | None = None,
    ) -> None:
        """Convert a Markdown string directly to a DOCX document.

        Accepts the same keyword arguments as :meth:`convert`.
        """
        logger.info("Converting text \u2192 %s", output_file)
        print("Converting Markdown\u2026")

        print("Parsing\u2026")
        document = self._parser.parse(markdown_text)
        self._process_diagrams(document)
        self._process_equations(document)

        print("Rendering DOCX\u2026")
        self._collect_statistics(document)
        self._renderer.render(
            document,
            output_file,
            generate_toc=generate_toc,
            page_numbers=page_numbers,
            header_text=header_text,
            footer_text=footer_text,
            cover_page=cover_page,
            title=title,
            author=author,
            company=company,
            subject=subject,
            keywords=keywords,
            doc_version=doc_version,
        )

        print("Done.")

    # ------------------------------------------------------------------
    # Diagram processing
    # ------------------------------------------------------------------

    def _process_diagrams(self, document: Document) -> None:
        """Walk document and replace diagram code blocks with Diagram blocks."""
        if not self._diagram_engine:
            return

        new_blocks: list[Block] = []
        for block in document.blocks:
            if (
                isinstance(block, CodeBlock)
                and block.language
                and block.language in self._diagram_engine.registry
            ):
                logger.info("Rendering %s diagram\u2026", block.language)
                result = self._diagram_engine.render(block.code, block.language)
                if result.png:
                    new_blocks.append(
                        Diagram(
                            alt=f"{block.language} diagram",
                            png_bytes=result.png,
                            source=block.code,
                            language=block.language,
                            caption=block.language,
                        )
                    )
                else:
                    logger.warning(
                        "Diagram rendering failed for %s: %s",
                        block.language,
                        result.error,
                    )
                    new_blocks.append(block)
            else:
                new_blocks.append(block)
        document.blocks = new_blocks

    # ------------------------------------------------------------------
    # Equation processing
    # ------------------------------------------------------------------

    def _process_equations(self, document: Document) -> None:
        """Walk document and detect/render equations inline and block-level."""
        if not self._equation_engine:
            return

        engine = self._equation_engine
        new_blocks: list[Block] = []

        for block in document.blocks:
            if isinstance(block, Paragraph):
                # Process inline equations and check for display equation blocks
                result = engine._process_paragraph(block)
                if result[1]:
                    # Paragraph was a display equation — use result
                    eq_block = result[0]
                    if eq_block.omml is not None or eq_block.svg is not None:
                        new_blocks.append(eq_block)
                    else:
                        new_blocks.append(block)
                else:
                    new_blocks.append(block)
            elif isinstance(block, CodeBlock):
                # Skip — diagrams handle code blocks
                new_blocks.append(block)
            else:
                new_blocks.append(block)

        document.blocks = new_blocks

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> DocumentStatistics:
        """Return the statistics from the most recent conversion run."""
        return self._statistics

    def _collect_statistics(self, document: Document) -> None:
        """Walk the document model and count elements / words."""
        stats = DocumentStatistics()

        def walk(blocks: list[Block]) -> None:
            for block in blocks:
                if isinstance(block, Heading):
                    stats.heading_count += 1
                    stats.word_count += _count_words(block.plain_text())
                elif isinstance(block, Paragraph):
                    stats.paragraph_count += 1
                    stats.word_count += _count_words(block.plain_text())
                elif isinstance(block, CodeBlock):
                    stats.code_block_count += 1
                    stats.word_count += _count_words(block.code)
                elif isinstance(block, Table):
                    stats.table_count += 1
                    for row in block.rows:
                        for cell in row:
                            stats.word_count += _count_words(cell)
                    for h in block.headers:
                        stats.word_count += _count_words(h)
                elif isinstance(block, Image):
                    stats.image_count += 1
                elif isinstance(block, Diagram):
                    stats.image_count += 1
                    stats.word_count += _count_words(block.alt)
                elif isinstance(block, BulletList):
                    stats.list_item_count += len(block.items)
                    for item in block.items:
                        walk(item.children)
                elif isinstance(block, OrderedList):
                    stats.list_item_count += len(block.items)
                    for item in block.items:
                        walk(item.children)
                elif isinstance(block, Blockquote):
                    walk(block.children)
                elif isinstance(block, EquationBlock):
                    stats.equation_count += 1
                    stats.word_count += _count_words(block.latex)

        walk(document.blocks)
        self._statistics = stats


def _default_equation_engine() -> EquationEngine | None:
    """Build a default equation engine with caching."""
    try:
        return EquationEngine(
            config=EquationConfig(),
            cache=MemoryEquationCache(default_ttl=7200),
        )
    except Exception:
        return None


def _default_diagram_engine() -> DiagramEngine | None:
    """Build a diagram engine with all available renderers (no-op if none are installed)."""
    registry = DiagramRegistry()
    for renderer_cls in (
        MermaidRenderer,
        PlantUMLRenderer,
        GraphvizRenderer,
        D2Renderer,
        AsciiRenderer,
        SvgRenderer,
    ):
        renderer = renderer_cls()
        if renderer.is_available():
            registry.register(renderer)

    if len(registry) == 0:
        return None
    return DiagramEngine(registry=registry)


def _count_words(text: str) -> int:
    return len(text.split())
