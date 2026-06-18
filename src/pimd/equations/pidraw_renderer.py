"""PiDraw-based equation renderer — delegates to PiDraw's equation engine.

Pipeline: LaTeX -> matplotlib SVG -> transparent PNG via PiDraw's
svg_to_png (resvg/cairosvg/playwright/Pillow).
"""

from __future__ import annotations

import time

from pimd.diagrams.models import DiagramResult
from pimd.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_equation(
    latex: str,
    display: bool = False,
    *,
    dpi: float = 200,
    transparent: bool = True,
) -> DiagramResult:
    """Render a LaTeX equation to PNG via PiDraw's equation engine.

    Delegates to PiDraw's :func:`pidraw.render_equation` which uses
    matplotlib's mathtext (no LaTeX installation required).

    Args:
        latex: LaTeX equation source (with or without $ delimiters).
        display: True for display math (centered, larger).
        dpi: Output DPI for PNG.
        transparent: Whether PNG background is transparent (default True).

    Returns:
        :class:`DiagramResult` with PNG data.
    """
    start = time.monotonic()

    try:
        from pidraw.equations import render_equation as _pidraw_render_eq
    except ImportError:
        return DiagramResult(
            source=latex,
            language="equation",
            error="PiDraw equation renderer is not available",
            render_time=time.monotonic() - start,
        )

    try:
        eq_result = _pidraw_render_eq(
            latex,
            display=display,
            dpi=dpi,
            transparent=transparent,
        )
    except Exception as exc:
        logger.warning("PiDraw equation rendering failed: %s", exc)
        return DiagramResult(
            source=latex,
            language="equation",
            error=f"Equation rendering failed: {exc}",
            render_time=time.monotonic() - start,
        )

    return DiagramResult(
        source=latex,
        language="equation",
        svg=eq_result.svg,
        png=eq_result.png,
        render_time=time.monotonic() - start,
        error=eq_result.error,
    )
