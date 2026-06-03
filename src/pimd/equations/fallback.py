"""SVG fallback renderer for equations — renders LaTeX to SVG.

Attempts to use matplotlib's mathtext for rendering.
If matplotlib is not installed, returns a placeholder SVG.
"""

from __future__ import annotations

import io
import re
import textwrap


def latex_to_svg(latex: str, display: bool = False, fontsize: int = 14) -> str | None:
    """Render LaTeX equation to SVG string.

    Uses matplotlib's builtin mathtext parser which supports a
    substantial subset of LaTeX math.

    Falls back to a placeholder SVG if matplotlib is not available.
    """
    # Try matplotlib first
    svg = _render_with_matplotlib(latex, display, fontsize)
    if svg:
        return svg

    # Fallback: simple placeholder SVG
    return _placeholder_svg(latex, display)


def _render_with_matplotlib(latex: str, display: bool, fontsize: int) -> str | None:
    """Render equation to SVG using matplotlib's mathtext."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    try:
        # Wrap in $ for mathtext
        text = f"${latex}$" if not latex.startswith("$") else latex

        fig, ax = plt.subplots(figsize=(0.01, 0.01))
        ax.text(
            0,
            0,
            text,
            fontsize=fontsize,
            ha="left",
            va="bottom",
            usetex=False,
            math_fontfamily="dejavusans",
        )
        ax.axis("off")

        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="svg",
            bbox_inches="tight",
            pad_inches=0.05,
            dpi=200,
        )
        plt.close(fig)
        svg = buf.getvalue().decode("utf-8")

        # Extract just the SVG tag content
        match = re.search(
            r"<svg[^>]*>.*?</svg>",
            svg,
            re.DOTALL,
        )
        if match:
            return match.group()

        return svg
    except Exception:
        plt.close("all")
        return None


def _placeholder_svg(latex: str, display: bool) -> str:
    """Generate a placeholder SVG showing the LaTeX source."""
    safe = latex.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lines = textwrap.wrap(safe, width=60) or [safe]
    text_lines = "\n".join(
        f'      <tspan x="10" dy="{20 if i > 0 else 0}">{line}</tspan>'
        for i, line in enumerate(lines)
    )

    height = max(40, len(lines) * 22 + 20)
    width = max(200, min(len(safe) * 8 + 20, 600))

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{width}" height="{height}"'
        f' viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="#fafafa" rx="4"/>'
        '<text font-family="Consolas, monospace" font-size="13" fill="#666">'
        f"{text_lines}"
        "  </text>"
        "</svg>"
    )
    return svg
