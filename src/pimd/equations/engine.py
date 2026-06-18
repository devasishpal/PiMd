"""Equation engine — detects and renders equations via PiDraw (no OMML).

All rendering is delegated to PiDraw's HTML→Playwright→PNG pipeline.
"""

from __future__ import annotations

import time
from typing import Any

from pimd.equations.cache import EquationCache, MemoryEquationCache
from pimd.equations.models import EquationConfig, EquationResult
from pimd.equations.parser import clean_latex, is_chemical_formula, normalize_chemical
from pimd.equations.validation import EquationValidator
from pimd.utils.logging import get_logger

logger = get_logger(__name__)


class EquationEngine:
    """Central equation rendering engine — PiDraw only, no OMML.

    All rendering goes through PiDraw's HTML→Playwright→PNG pipeline.
    """

    def __init__(
        self,
        config: EquationConfig | None = None,
        cache: EquationCache | None = None,
    ) -> None:
        self._config = config or EquationConfig()
        self._cache = cache or MemoryEquationCache(
            default_ttl=self._config.cache_ttl,
        )
        self._validator = EquationValidator()
        self._eq_counter: int = 0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> EquationConfig:
        return self._config

    @property
    def cache(self) -> EquationCache:
        return self._cache

    # ------------------------------------------------------------------
    # Single equation rendering
    # ------------------------------------------------------------------

    def render(
        self,
        source: str,
        display: bool = False,
        *,
        format: str = "latex",
        label: str | None = None,
        force_chemical: bool = False,
    ) -> EquationResult:
        """Render a single equation via PiDraw (no OMML).

        Args:
            source: LaTeX/MathJax/KaTeX equation source.
            display: True for display math ($$...$$), False for inline.
            format: Input format ("latex", "mathjax", "katex").
            label: Optional equation label (for cross-references).
            force_chemical: Treat as chemical formula.

        Returns:
            :class:`EquationResult` with PNG from PiDraw.
        """
        start = time.monotonic()

        # Normalize source
        latex = clean_latex(source, format)

        # Handle chemical formulas
        is_chem = force_chemical or is_chemical_formula(latex)
        if is_chem:
            latex = normalize_chemical(latex)

        # Check cache
        cache_key = f"{latex}:{display}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            cached.cached = True
            cached.render_time = time.monotonic() - start
            return cached

        # Validate
        validation = self._validator.validate(latex)
        if not validation.valid:
            result = EquationResult(
                source=source,
                latex=latex,
                display=display,
                error="; ".join(validation.errors),
                render_time=time.monotonic() - start,
                is_chemical=is_chem,
            )
            logger.warning("Equation validation failed: %s", result.error)
            return result

        # Render via PiDraw (Playwright → PNG)
        png: bytes | None = None
        error: str | None = None
        try:
            from pimd.equations.pidraw_renderer import render_equation
            eq_result = render_equation(latex, display=display)
            if eq_result.png:
                png = eq_result.png
            elif eq_result.error:
                error = eq_result.error
        except Exception as exc:
            logger.debug("PiDraw equation rendering failed: %s", exc)
            error = f"PiDraw rendering failed: {exc}"

        if png is None and error is None:
            error = "PiDraw equation rendering returned no output"

        # Assign number if display math
        number: int | None = None
        if display and self._config.numbering_enabled and not error:
            self._eq_counter += 1
            number = self._eq_counter

        result = EquationResult(
            source=source,
            latex=latex,
            display=display,
            png=png,
            error=error,
            render_time=time.monotonic() - start,
            label=label,
            number=number,
            is_chemical=is_chem,
        )

        # Cache on success
        if result.success and self._config.cache_enabled:
            self._cache.set(cache_key, result, ttl=self._config.cache_ttl)

        logger.debug(
            "Rendered equation in %.2fs (PNG=%s)",
            result.render_time,
            result.png is not None,
        )
        return result

    # ------------------------------------------------------------------
    # Document processing
    # ------------------------------------------------------------------

    def process_document(self, document: Any) -> None:
        """Process a document model: detect and render all equations.

        Modifies the document in-place by:
        - Splitting spans with embedded $...$ math
        - Replacing block-level equation paragraphs with EquationBlock
        """
        from pimd.models import Block, Paragraph

        self._eq_counter = 0

        new_blocks: list[Block] = []
        for block in document.blocks:
            if isinstance(block, Paragraph):
                _, processed = self._process_paragraph(block)
                new_blocks.append(block)
            else:
                new_blocks.append(block)

        document.blocks = new_blocks

    def _process_paragraph(self, para: Any) -> tuple[Any, bool]:
        """Process a paragraph, splitting spans with math."""
        from pimd.equations.parser import extract_inline_equations, is_display_equation
        from pimd.models import EquationBlock, Span

        # Check if the entire paragraph is a display equation
        full_text = para.plain_text()
        if is_display_equation(full_text):
            from pimd.equations.parser import clean_latex as _cl

            latex = _cl(full_text, "latex")
            result = self.render(latex, display=True)
            if result.png:
                eq_block = EquationBlock(
                    latex=latex,
                    display=True,
                    png=result.png,
                    label=result.label,
                    number=result.number,
                    error=result.error,
                )
                return (eq_block, True)

        # Process inline spans for $...$ math
        processed_spans: list[Span] = []
        for span in para.spans:
            if not span.text:
                processed_spans.append(span)
                continue

            equations = extract_inline_equations(span.text)
            if not equations:
                processed_spans.append(span)
                continue

            # Split span text around math delimiters
            last_end = 0
            for src, fmt, is_display, eq_start, eq_end in equations:
                # Text before equation
                if eq_start > last_end:
                    before = span.text[last_end:eq_start]
                    processed_spans.append(
                        Span(
                            text=before,
                            bold=span.bold,
                            italic=span.italic,
                            underline=span.underline,
                            code=span.code,
                            link_url=span.link_url,
                        )
                    )

                # Render the equation
                result = self.render(src, display=is_display, format=fmt)
                if result.png:
                    processed_spans.append(
                        Span(
                            text="",
                            math=src,
                            math_display=is_display,
                            png=result.png,
                        )
                    )
                else:
                    processed_spans.append(
                        Span(
                            text=src,
                            code=True,
                        )
                    )

                last_end = eq_end

            # Text after last equation
            if last_end < len(span.text):
                after = span.text[last_end:]
                processed_spans.append(
                    Span(
                        text=after,
                        bold=span.bold,
                        italic=span.italic,
                        underline=span.underline,
                        code=span.code,
                        link_url=span.link_url,
                    )
                )

        para.spans = processed_spans
        return (None, False)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def clear_cache(self) -> None:
        self._cache.clear()
        logger.info("Equation cache cleared")

    def reset_numbering(self) -> None:
        self._eq_counter = 0

    def is_available(self) -> bool:
        return True

    def doctor(self) -> list[dict[str, str]]:
        """Run diagnostics on equation rendering capabilities."""
        results: list[dict[str, str]] = []

        # PiDraw Playwright check
        try:
            from pimd.equations.pidraw_renderer import render_equation
            test_result = render_equation("E = mc^2", display=False)
            if test_result.png:
                results.append(
                    {
                        "check": "PiDraw equation renderer",
                        "status": "ok",
                        "detail": "PNG rendering works via Playwright",
                    }
                )
            else:
                results.append(
                    {
                        "check": "PiDraw equation renderer",
                        "status": "warning",
                        "detail": test_result.error or "Render returned no PNG",
                    }
                )
        except Exception as exc:
            results.append(
                {
                    "check": "PiDraw equation renderer",
                    "status": "error",
                    "detail": f"Failed: {exc}",
                }
            )

        # Chemical support
        chem_result = self.render("H_2O", display=False, force_chemical=True)
        results.append(
            {
                "check": "Chemical formulas",
                "status": "ok" if chem_result.success else "warning",
                "detail": "Supported via LaTeX subscript notation",
            }
        )

        # Numbering
        results.append(
            {
                "check": "Equation numbering",
                "status": "ok" if self._config.numbering_enabled else "disabled",
                "detail": f"Counter at {self._eq_counter}",
            }
        )

        return results
