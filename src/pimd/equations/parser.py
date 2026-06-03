"""Equation parser — detect and normalize equations from various formats.

Detects:
  - LaTeX: $...$, $$...$$, \\(...\\), \\[...\\], \begin{equation}
  - MathJax: same delimiters, extra \\(
  - KaTeX: same delimiters
  - Chemical formulas: H₂O, CO₂ patterns
"""

from __future__ import annotations

import re

# Patterns for detecting equations in text
_INLINE_PATTERNS: list[tuple[re.Pattern, str, bool]] = [
    (re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)"), "latex", False),
    (re.compile(r"\\\((.+?)\\\)"), "latex", False),
]

_DISPLAY_PATTERNS: list[tuple[re.Pattern, str, bool]] = [
    (re.compile(r"\$\$(.+?)\$\$", re.DOTALL), "latex", True),
    (re.compile(r"\\\[(.+?)\\\]", re.DOTALL), "latex", True),
    (re.compile(r"\\begin\{equation\*\}(.+?)\\end\{equation\*\}", re.DOTALL), "latex", True),
    (re.compile(r"\\begin\{equation\}(.+?)\\end\{equation\}", re.DOTALL), "latex", True),
    (re.compile(r"\\begin\{align\*\}(.+?)\\end\{align\*\}", re.DOTALL), "latex", True),
    (re.compile(r"\\begin\{align\}(.+?)\\end\{align\}", re.DOTALL), "latex", True),
]

# Detect if a block of text is entirely a display equation
_DISPLAY_BLOCK_RE = re.compile(
    r"^\s*"
    r"(?:\$\$(.+?)\$\$"
    r"|\\\[(.+?)\\\]"
    r"|\\begin\{equation\*\}(.+?)\\end\{equation\*\}"
    r"|\\begin\{equation\}(.+?)\\end\{equation\}"
    r"|\\begin\{align\*\}(.+?)\\end\{align\*\}"
    r"|\\begin\{align\}(.+?)\\end\{align\})"
    r"\s*$",
    re.DOTALL,
)

# Chemical patterns
_CHEMICAL_RE = re.compile(r"\b(?:H_2O|CO_2|CH_4|NH_3|NaCl|H_2SO_4|C_2H_5OH|C_6H_12O_6)\b")


def is_display_equation(text: str) -> bool:
    """Check if text is a standalone display equation."""
    return bool(_DISPLAY_BLOCK_RE.match(text.strip()))


def extract_inline_equations(text: str) -> list[tuple[str, str, bool, int, int]]:
    """Find inline equations in text.

    Returns list of (latex_source, format, is_display, start, end).
    """
    results: list[tuple[str, str, bool, int, int]] = []

    # Check display patterns first (they span lines)
    for pattern, fmt, is_display in _DISPLAY_PATTERNS:
        for match in pattern.finditer(text):
            src = match.group(1).strip()
            results.append((src, fmt, is_display, match.start(), match.end()))

    # Check inline patterns
    for pattern, fmt, is_display in _INLINE_PATTERNS:
        for match in pattern.finditer(text):
            # Skip if inside a display equation
            start, end = match.start(), match.end()
            if any(s <= start and end <= e for _, _, _, s, e in results):
                continue
            src = match.group(1).strip()
            results.append((src, fmt, is_display, start, end))

    # Sort by position
    results.sort(key=lambda x: x[3])
    return results


def extract_equation_blocks(text: str) -> list[tuple[str, str, bool]]:
    """Find block-level equations in text.

    Returns list of (latex_source, format, is_display).
    """
    results: list[tuple[str, str, bool]] = []
    for line in text.strip().split("\n\n"):
        clean = line.strip()
        if is_display_equation(clean):
            match = _DISPLAY_BLOCK_RE.match(clean)
            if match:
                src = next(g for g in match.groups() if g is not None)
                results.append((src.strip(), "latex", True))
    return results


def is_chemical_formula(text: str) -> bool:
    """Check if text is a chemical formula."""
    return bool(_CHEMICAL_RE.match(text.strip()))


def normalize_chemical(text: str) -> str:
    """Convert chemical notation to proper LaTeX."""
    mapping = {
        "H_2O": r"H_{2}O",
        "CO_2": r"CO_{2}",
        "CH_4": r"CH_{4}",
        "NH_3": r"NH_{3}",
        "NaCl": r"NaCl",
        "H_2SO_4": r"H_{2}SO_{4}",
        "C_2H_5OH": r"C_{2}H_{5}OH",
        "C_6H_12O_6": r"C_{6}H_{12}O_{6}",
    }
    result = text
    for raw, latex in mapping.items():
        result = result.replace(raw, latex)
    return result


def clean_latex(source: str, fmt: str) -> str:
    """Normalize equation source to plain LaTeX."""
    latex = source.strip()
    # Strip outer $ or $$ if present
    if latex.startswith("$$") and latex.endswith("$$"):
        latex = latex[2:-2].strip()
    elif latex.startswith("$") and latex.endswith("$"):
        latex = latex[1:-1].strip()
    elif latex.startswith(r"\(") and latex.endswith(r"\)"):
        latex = latex[2:-2].strip()
    elif latex.startswith(r"\[") and latex.endswith(r"\]"):
        latex = latex[2:-2].strip()
    return latex
