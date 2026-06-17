"""Conversion orchestration service."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pimd.caching import CacheBackend
from pimd.exceptions import ConversionError
from pimd.models import Block, CodeBlock, Diagram, Document, DocumentStatistics, Paragraph
from pimd.observability import ConversionMetrics, ConversionReport, Timer
from pimd.plugins import ConversionHook, PluginManager
from pimd.renderers.docx_renderer import DocxRenderer
from pimd.safety import SafetyGuard, SafetyLimits
from pimd.themes import ProfessionalTheme
from pimd.themes.base import Theme
from pimd.utils.logging import get_logger

try:
    from pimd.diagrams.pidraw_integration import (
        _HAS_PIDRAW,
    )
    from pimd.diagrams.pidraw_integration import (
        detect_language as _pidraw_detect,
    )
    from pimd.diagrams.pidraw_integration import (
        render_diagram as _render_with_pidraw,
    )
except ImportError:
    _HAS_PIDRAW = False
    _pidraw_detect = None  # type: ignore
    _render_with_pidraw = None  # type: ignore

logger = get_logger(__name__)

_BOX_CHARS = frozenset(
    "\u2500\u2502\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c"
    "\u2550\u2551\u2554\u2557\u255a\u255d\u2560\u2563\u2566\u2569\u256c"
    "\u2501\u2503\u250f\u2513\u2517\u251b\u2523\u252b\u2533\u253b\u254b"
)


def _looks_like_ascii_diagram(code: str) -> bool:
    lines = code.strip().splitlines()
    if len(lines) < 3:
        return False
    for ch in _BOX_CHARS:
        if ch in code:
            return True
    has_plus_minus = False
    has_pipe = False
    for line in lines:
        stripped = line.strip()
        if "+" in stripped and "-" in stripped:
            has_plus_minus = True
        if "|" in stripped:
            has_pipe = True
        if has_plus_minus and has_pipe:
            return True
    return False


@dataclass
class ConversionResult:
    """Result returned by a conversion operation."""

    output_path: Path | None = None
    output_bytes: bytes | None = None
    report: ConversionReport = field(default_factory=ConversionReport)
    statistics: DocumentStatistics | None = None


class ConversionService:
    """Orchestrates the full parse → render pipeline with observability,
    caching, safety checks, and plugin hooks.

    This is the single entry point for all conversions in PiMD.
    The CLI, PiMD class, and future REST APIs all delegate here.
    """

    def __init__(
        self,
        theme: Theme | None = None,
        cache: CacheBackend | None = None,
        limits: SafetyLimits | None = None,
        plugins: PluginManager | None = None,
        diagram_engine: Any = None,
        equation_engine: Any = None,
        render_diagrams: bool = True,
    ) -> None:
        self._theme = theme or ProfessionalTheme()
        self._renderer = DocxRenderer(self._theme)
        self._cache = cache
        self._guard = SafetyGuard(limits)
        self._plugins = plugins or PluginManager()
        self._diagram_engine = diagram_engine or _default_diagram_engine()
        self._render_diagrams = render_diagrams
        self._equation_engine = equation_engine or _default_equation_engine()
        self._last_report: ConversionReport | None = None

    # ------------------------------------------------------------------
    # Public API — used by PiMD class and CLI
    # ------------------------------------------------------------------

    def convert_markdown(
        self,
        source: str | Path,
        *,
        output_path: str | Path | None = None,
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
        render_diagrams: bool | None = None,
    ) -> ConversionResult:
        """Convert Markdown source to DOCX.

        Args:
            source: Markdown text string or file path.
            output_path: Where to write the DOCX (``None`` = memory mode).
            render_diagrams: Whether to render diagrams (default: True).
            **options: Rendering options (TOC, page numbers, etc.).

        Returns:
            A :class:`ConversionResult` with path and/or bytes.
        """
        return self._convert(
            "markdown",
            source,
            output_path=output_path,
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
            render_diagrams=render_diagrams,
        )

    def convert_html(
        self,
        source: str | Path,
        *,
        output_path: str | Path | None = None,
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
        render_diagrams: bool | None = None,
    ) -> ConversionResult:
        """Convert HTML source to DOCX.

        Args:
            source: HTML text string or file path.
            output_path: Where to write the DOCX (``None`` = memory mode).
            render_diagrams: Whether to render diagrams (default: True).
            **options: Rendering options (TOC, page numbers, etc.).

        Returns:
            A :class:`ConversionResult` with path and/or bytes.
        """
        return self._convert(
            "html",
            source,
            output_path=output_path,
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
            render_diagrams=render_diagrams,
        )

    # ------------------------------------------------------------------
    # Report access
    # ------------------------------------------------------------------

    @property
    def last_report(self) -> ConversionReport | None:
        """Return the report from the most recent conversion."""
        return self._last_report

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_input_text(self, source: str | Path) -> str:
        """Read text from a string or file path."""
        if isinstance(source, Path):
            path = source
            self._guard.check_file_size(path)
            return path.read_text(encoding="utf-8")
        p = Path(source)
        if p.is_file() and p.suffix in (".md", ".html", ".markdown", ".htm", ".rst", ".txt"):
            self._guard.check_file_size(p)
            return p.read_text(encoding="utf-8")
        self._guard.check_text_size(source)
        return source

    def _get_parser(self, fmt: str) -> Any:
        if fmt == "markdown":
            from pimd.parsers.markdown_parser import MarkdownParser

            return MarkdownParser()
        if fmt == "html":
            from pimd.parsers.html_parser import HTMLParser

            return HTMLParser()
        raise ConversionError(f"Unknown format: {fmt}")

    def _render_to_path(self, document: Document, output_path: str | Path, **options: Any) -> None:
        self._renderer.render(document, output_path, **options)

    def _render_to_bytes(self, document: Document, **options: Any) -> bytes:
        from pimd.renderers.docx_renderer import DocxRenderer as _DocxRenderer

        renderer = _DocxRenderer(self._theme)
        return renderer.render_to_bytes(document, **options)

    def _process_diagrams(self, document: Document) -> None:
        """Process and render all diagram blocks using PiDraw.

        Handles two cases:
        1. Already-detected ``Diagram`` blocks (from parser) — renders them.
        2. ``CodeBlock`` blocks — attempts auto-detection via PiDraw.
        """
        if not self._diagram_engine or not self._render_diagrams:
            return
        engine = self._diagram_engine
        fig_counter = 0
        new_blocks: list[Block] = []
        for block in document.blocks:
            if isinstance(block, Diagram):
                # Already detected by parser — render it now
                fig_counter += 1
                result = engine.render(
                    block.source,
                    block.language,
                    dpi=300,
                    transparent=True,
                )
                if result.success:
                    block.png_bytes = result.png or b""
                    block.svg_bytes = result.svg.encode("utf-8") if result.svg else None
                    block.width = result.width
                    block.height = result.height
                    block.figure_number = fig_counter
                    block.error = None
                else:
                    logger.warning(
                        "Diagram rendering failed for %s: %s",
                        block.language,
                        result.error,
                    )
                    block.error = result.error or "Rendering failed"
                    block.figure_number = fig_counter
                new_blocks.append(block)

            elif isinstance(block, CodeBlock):
                lang = block.language
                # Try auto-detection if no language hint
                if lang is None:
                    try:
                        detected = _pidraw_detect(block.code, hint=None)
                        if detected:
                            lang = detected
                    except Exception:
                        pass

                if lang and engine.is_diagram_language(lang):
                    fig_counter += 1
                    result = engine.render(block.code, lang)
                    cap = lang.title()
                    if result.success:
                        new_blocks.append(
                            Diagram(
                                alt=f"{lang} diagram",
                                png_bytes=result.png or b"",
                                svg_bytes=result.svg.encode("utf-8") if result.svg else None,
                                source=block.code,
                                language=lang,
                                caption=cap,
                                width=result.width,
                                height=result.height,
                                figure_number=fig_counter,
                                error=result.error,
                            )
                        )
                    else:
                        logger.warning(
                            "Diagram rendering failed for %s: %s",
                            lang,
                            result.error,
                        )
                        new_blocks.append(
                            Diagram(
                                alt=f"{lang} diagram",
                                source=block.code,
                                language=lang or "unknown",
                                caption=cap,
                                figure_number=fig_counter,
                                error=result.error or "Rendering failed",
                            )
                        )
                else:
                    new_blocks.append(block)
            else:
                new_blocks.append(block)
        document.blocks = new_blocks

    def _process_equations(self, document: Document) -> None:
        if not self._equation_engine:
            return
        engine = self._equation_engine
        new_blocks: list[Block] = []
        for block in document.blocks:
            if isinstance(block, CodeBlock):
                new_blocks.append(block)
            elif isinstance(block, Paragraph):
                eq_text, is_eq = engine._process_paragraph(block)
                if is_eq:
                    if eq_text.omml is not None or eq_text.svg is not None:
                        new_blocks.append(eq_text)
                    else:
                        new_blocks.append(block)
                else:
                    new_blocks.append(block)
            else:
                new_blocks.append(block)
        document.blocks = new_blocks

    def _convert(
        self,
        fmt: str,
        source: str | Path,
        *,
        output_path: str | Path | None = None,
        render_diagrams: bool | None = None,
        **options: Any,
    ) -> ConversionResult:
        """Core conversion pipeline."""
        report = ConversionReport(source_format=fmt)
        metrics = ConversionMetrics()
        timer_total = Timer()
        timer_total.__enter__()

        try:
            # ---- Plugin: before_convert ----
            ctx: dict[str, Any] = {"format": fmt, "source": source, "options": options}
            ctx = self._plugins.dispatch(ConversionHook.BEFORE_CONVERT, ctx)

            # ---- Check cache ----
            cache_key = None
            if self._cache:
                cache_key = self._cache.make_key(
                    "convert",
                    fmt,
                    source=str(source) if not isinstance(source, Path) else str(source.absolute()),
                    **{k: str(v) for k, v in sorted(options.items()) if v},
                )
                cached = self._cache.get(cache_key)
                if cached is not None:
                    report.cache_hit = True
                    report.metrics = cached.get("metrics", metrics)
                    self._last_report = report
                    logger.debug("Cache hit for key: %s", cache_key)

                    # If the user wants a file, we need to write it, but we only cached bytes
                    if output_path and isinstance(cached, dict) and "bytes" in cached:
                        Path(output_path).write_bytes(cached["bytes"])
                        return ConversionResult(
                            output_path=Path(output_path),
                            output_bytes=cached["bytes"],
                            report=report,
                        )
                    if "result" in cached:
                        return cached["result"]
                    return ConversionResult(output_bytes=cached.get("bytes"), report=report)

            # ---- Read input ----
            source_text = self._get_input_text(source)
            metrics.input_size = len(source_text.encode("utf-8"))

            # ---- Plugin: before_parse ----
            source_text = self._plugins.dispatch(
                ConversionHook.BEFORE_PARSE, source_text, context=ctx
            )

            # ---- Parse ----
            with Timer() as parse_timer:
                parser = self._get_parser(fmt)
                document = parser.parse(str(source_text))
            metrics.parse_time = parse_timer.elapsed

            # Check block count
            self._guard.check_block_count(len(document.blocks))

            # ---- Collect statistics ----
            statistics = _collect_statistics(document)

            # ---- Plugin: after_parse / before_render ----
            document = self._plugins.dispatch(ConversionHook.AFTER_PARSE, document, context=ctx)

            # Override render_diagrams if explicitly provided
            if render_diagrams is not None:
                old_value = self._render_diagrams
                self._render_diagrams = render_diagrams
                self._process_diagrams(document)
                self._render_diagrams = old_value
            else:
                self._process_diagrams(document)
            self._process_equations(document)
            document = self._plugins.dispatch(ConversionHook.BEFORE_RENDER, document, context=ctx)

            # ---- Render ----
            with Timer() as render_timer:
                if output_path:
                    self._render_to_path(document, output_path, **options)
                else:
                    docx_bytes = self._render_to_bytes(document, **options)
            metrics.render_time = render_timer.elapsed

            # Compute final times
            timer_total.__exit__(None, None, None)
            metrics.total_time = timer_total.elapsed
            report.metrics = metrics
            report.statistics = statistics

            if output_path:
                metrics.output_size = Path(output_path).stat().st_size
                result = ConversionResult(
                    output_path=Path(output_path),
                    report=report,
                    statistics=statistics,
                )
            else:
                metrics.output_size = len(docx_bytes)
                result = ConversionResult(
                    output_bytes=docx_bytes,
                    report=report,
                    statistics=statistics,
                )

            # ---- Plugin: after_render / after_convert ----
            self._plugins.dispatch(ConversionHook.AFTER_RENDER, result, context=ctx)
            self._plugins.dispatch(ConversionHook.AFTER_CONVERT, ctx)

            # ---- Store in cache ----
            if self._cache and cache_key:
                cache_data = {
                    "metrics": metrics,
                    "bytes": result.output_bytes,
                    "statistics": statistics,
                }
                self._cache.set(cache_key, cache_data)

            self._last_report = report
            logger.info(
                "Converted %s in %.2fs (%s blocks)",
                fmt,
                metrics.total_time,
                statistics.total_blocks if statistics else 0,
            )
            return result

        except Exception as exc:
            timer_total.__exit__(None, None, None)
            metrics.total_time = timer_total.elapsed
            report.metrics = metrics
            report.success = False
            report.error = str(exc)
            self._last_report = report
            raise


def _collect_statistics(document: Document) -> DocumentStatistics:
    """Walk the document model and count elements / words."""
    from pimd.converters.markdown import _count_words

    stats = DocumentStatistics()

    def walk(blocks: list[Any]) -> None:
        for block in blocks:
            if isinstance(block, Document):
                walk(block.blocks)
            elif hasattr(block, "plain_text"):
                stats.paragraph_count += 1
                stats.word_count += _count_words(block.plain_text())
            elif hasattr(block, "code"):
                stats.code_block_count += 1
                stats.word_count += _count_words(block.code)
            elif hasattr(block, "items"):
                if hasattr(block, "start"):
                    stats.list_item_count += len(block.items)
                else:
                    stats.list_item_count += len(block.items)
                for item in block.items:
                    walk(item.children)
            elif hasattr(block, "headers"):
                stats.table_count += 1
                for h in block.headers:
                    stats.word_count += _count_words(h)
                for row in block.rows:
                    for cell in row:
                        stats.word_count += _count_words(cell)
            elif hasattr(block, "children"):
                walk(block.children)
            elif hasattr(block, "url") and hasattr(block, "alt"):
                stats.image_count += 1

    walk(document.blocks)
    return stats


def _default_diagram_engine() -> Any:
    """Create a default diagram engine backed by PiDraw."""
    from pimd.diagrams import DiagramEngine, DiagramRegistry

    registry = DiagramRegistry()
    return DiagramEngine(registry=registry)


def _default_equation_engine() -> Any:
    from pimd.equations import EquationEngine
    from pimd.equations.cache import MemoryEquationCache
    from pimd.equations.models import EquationConfig

    try:
        return EquationEngine(
            config=EquationConfig(),
            cache=MemoryEquationCache(default_ttl=7200),
        )
    except Exception:
        return None
