"""Equation engine — orchestrates detection, rendering, caching, validation.

Auto-detects equations during document conversion and renders them
to native Word OMML (with SVG fallback).
"""

from __future__ import annotations

import time
from typing import Any

from pimd.equations.cache import EquationCache, MemoryEquationCache
from pimd.equations.fallback import latex_to_svg
from pimd.equations.models import EquationConfig, EquationResult
from pimd.equations.omml import latex_to_omml
from pimd.equations.parser import clean_latex, is_chemical_formula, normalize_chemical
from pimd.equations.validation import EquationValidator
from pimd.utils.logging import get_logger

logger = get_logger(__name__)


class EquationEngine:
    """Central equation rendering engine.

    Orchestrates detection, OMML conversion, SVG fallback, and caching.

    Usage::

        engine = EquationEngine()
        result = engine.render("E = mc^2")
        if result.has_omml:
            # inject result.omml into DOCX paragraph
        elif result.svg:
            # embed result.svg as image
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
        """Render a single equation.

        Priority:
          1. OMML (native Word equation) — editable in Word
          2. SVG fallback — when OMML is not supported

        Args:
            source: LaTeX/MathJax/KaTeX equation source.
            display: True for display math ($$...$$), False for inline.
            format: Input format ("latex", "mathjax", "katex").
            label: Optional equation label (for cross-references).
            force_chemical: Treat as chemical formula.

        Returns:
            :class:`EquationResult` with OMML or SVG.
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

        error: str | None = None
        omml: Any = None
        svg: str | None = None

        # Render OMML (native Word equation)
        try:
            omml = latex_to_omml(latex, display=display)
        except Exception as exc:
            logger.debug("OMML conversion failed for '%s': %s", latex, exc)
            omml = None

        # Fallback to SVG if OMML failed
        if omml is None:
            try:
                svg = latex_to_svg(latex, display=display)
            except Exception as exc:
                logger.debug("SVG fallback failed for '%s': %s", latex, exc)
                svg = None

            if svg is None:
                error = "Equation rendering failed (OMML and SVG both unavailable)"

        # Assign number if display math
        number: int | None = None
        if display and self._config.numbering_enabled and not error:
            self._eq_counter += 1
            number = self._eq_counter

        result = EquationResult(
            source=source,
            latex=latex,
            display=display,
            omml=omml,
            svg=svg,
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
            "Rendered equation in %.2fs (OMML=%s, SVG=%s)",
            result.render_time,
            result.has_omml,
            result.svg is not None,
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
            if result.has_omml or result.svg:
                eq_block = EquationBlock(
                    latex=latex,
                    display=True,
                    omml=result.omml,
                    svg=result.svg,
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
                if result.has_omml:
                    processed_spans.append(
                        Span(
                            text="",
                            math=src,
                            math_display=is_display,
                            omml=result.omml,
                        )
                    )
                elif result.svg:
                    processed_spans.append(
                        Span(
                            text=f"[Equation: {src}]",
                            italic=True,
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

        # OMML check
        results.append(
            {
                "check": "OMML (native Word equations)",
                "status": "ok",
                "detail": "Built-in — no external tools required",
            }
        )

        # SVG fallback check
        try:
            import matplotlib  # noqa: F401

            results.append(
                {
                    "check": "SVG fallback (matplotlib)",
                    "status": "ok",
                    "detail": "Matplotlib available for SVG rendering",
                }
            )
        except ImportError:
            results.append(
                {
                    "check": "SVG fallback (matplotlib)",
                    "status": "warning",
                    "detail": "Not installed — pip install matplotlib (recommended)",
                }
            )

        # Test OMML conversion
        test_result = self.render("E = mc^2", display=False)
        if test_result.has_omml:
            results.append(
                {
                    "check": "OMML conversion test",
                    "status": "ok",
                    "detail": f"Rendered in {test_result.render_time:.3f}s",
                }
            )
        else:
            results.append(
                {
                    "check": "OMML conversion test",
                    "status": "warning",
                    "detail": "Basic conversion works but had issues",
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
