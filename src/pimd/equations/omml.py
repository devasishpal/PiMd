# ruff: noqa: N806 — variable names match OMML element names (rPr, naryPr, etc.)

"""OMML equation renderer — native Word equations (Office Math Markup Language).

Converts LaTeX math expressions into OMML XML that Word edits natively.
Uses python-docx's OxmlElement to build the OMML tree.

Architecture:
  1. Tokenize LaTeX string into tokens
  2. Parse tokens into a simple AST
  3. Walk AST and generate OMML XML tree
  4. Return OMML tree for injection into DOCX

Fallback to SVG for unrecognized patterns.
"""

from __future__ import annotations

import re
from typing import Any

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from pimd.equations.models import (
    LATEX_GREEK_MAP,
    LATEX_SYMBOL_MAP,
)

# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(
    r"""
    \\[a-zA-Z]+|         # LaTeX command
    \\[\[\]\(\)]|        # \( \) \[ \]
    \{[^{}]*\}|          # braced group
    [{}]|                # single braces
    \^|_|                # super/subscript
    &|                   # alignment
    [a-zA-Z]+|           # identifier
    \d+(?:\.\d+)?|       # number
    [+\-*/=(),;:!?<>]|   # operator
    ~|                   # space
    \$|                  # dollar
    .                    # fallback — single char
    """,
    re.VERBOSE | re.DOTALL,
)


def tokenize(latex: str) -> list[str]:
    """Tokenize a LaTeX math string."""
    # Strip outer $ or $$ delimiters if present
    source = latex.strip()
    if source.startswith("$$") and source.endswith("$$"):
        source = source[2:-2].strip()
    elif source.startswith("$") and source.endswith("$"):
        source = source[1:-1].strip()
    elif source.startswith(r"\(") and source.endswith(r"\)"):
        source = source[2:-2].strip()
    elif source.startswith(r"\[") and source.endswith(r"\]"):
        source = source[2:-2].strip()

    return TOKEN_RE.findall(source)


# ---------------------------------------------------------------------------
# OMML Element Builders
# ---------------------------------------------------------------------------


def _m(name: str) -> Any:
    """Create an OMML element in the math namespace."""
    return OxmlElement(f"m:{name}")


def _mk_run(text: str, italic: bool = True) -> Any:
    """Create an OMML run (m:r) with optional italic formatting."""
    r = _m("r")
    if italic:
        rPr = _m("rPr")
        ital = _m("ital")
        ital.set(qn("m:val"), "1")
        rPr.append(ital)
        r.append(rPr)
    t = _m("t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def _mk_run_bold(text: str) -> Any:
    """Create a bold OMML run."""
    r = _m("r")
    rPr = _m("rPr")
    b = _m("lit")
    b.set(qn("m:val"), "1")
    rPr.append(b)
    r.append(rPr)
    t = _m("t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def _mk_script(base: Any, sub: Any | None, sup: Any | None) -> Any:
    """Create superscript, subscript, or sub-sup combination."""
    if sub is not None and sup is not None:
        elem = _m("subSup")
        e = _m("e")
        e.append(base)
        elem.append(e)
        sub_e = _m("sub")
        sub_e.append(sub)
        elem.append(sub_e)
        sup_e = _m("sup")
        sup_e.append(sup)
        elem.append(sup_e)
        return elem
    elif sup is not None:
        elem = _m("sup")
        e = _m("e")
        e.append(base)
        elem.append(e)
        lim = _m("lim")
        lim.append(sup)
        elem.append(lim)
        return elem
    elif sub is not None:
        elem = _m("sub")
        e = _m("e")
        e.append(base)
        elem.append(e)
        lim = _m("lim")
        lim.append(sub)
        elem.append(lim)
        return elem
    return base


def _mk_nary(symbol: str, base: Any, lower: Any | None, upper: Any | None) -> Any:
    """Create an n-ary operator (integral, sum, product)."""
    nary = _m("nary")
    naryPr = _m("naryPr")
    chr_elem = _m("chr")
    chr_elem.set(qn("m:val"), symbol)
    naryPr.append(chr_elem)
    nary.append(naryPr)

    if lower is not None:
        sub_e = _m("sub")
        sub_e.append(lower)
        nary.append(sub_e)

    if upper is not None:
        sup_e = _m("sup")
        sup_e.append(upper)
        nary.append(sup_e)

    e = _m("e")
    e.append(base)
    nary.append(e)
    return nary


def _mk_fraction(num: Any, den: Any) -> Any:
    """Create a fraction element."""
    f = _m("f")
    num_e = _m("num")
    num_e.append(num)
    f.append(num_e)
    den_e = _m("den")
    den_e.append(den)
    f.append(den_e)
    return f


def _mk_radical(radicand: Any, degree: Any | None = None) -> Any:
    """Create a radical (square root / nth root)."""
    rad = _m("rad")
    if degree is not None:
        deg = _m("deg")
        deg.append(degree)
        rad.append(deg)
    e = _m("e")
    e.append(radicand)
    rad.append(e)
    return rad


def _mk_function(name: str, arg: Any) -> Any:
    """Create a function application like sin(x), cos(x)."""
    func = _m("func")
    fName = _m("fName")
    fName.append(_mk_run(name, italic=False))
    func.append(fName)
    e = _m("e")
    e.append(arg)
    func.append(e)
    return func


def _mk_delimiter(content: Any, left: str, right: str) -> Any:
    """Wrap content in delimiters (parentheses, brackets, etc.)."""
    d = _m("d")
    dPr = _m("dPr")
    begChr = _m("begChr")
    begChr.set(qn("m:val"), left)
    dPr.append(begChr)
    endChr = _m("endChr")
    endChr.set(qn("m:val"), right)
    dPr.append(endChr)
    d.append(dPr)
    e = _m("e")
    e.append(content)
    d.append(e)
    return d


def _mk_box(content: Any) -> Any:
    """Group multiple elements into a box.

    Accepts a list of OMML elements or a _SequenceWrapper.
    """
    box = _m("box")
    boxPr = _m("boxPr")
    box.append(boxPr)
    e = _m("e")
    if isinstance(content, _SequenceWrapper):
        content.append_to(e)
    elif isinstance(content, list):
        for child in content:
            e.append(child)
    else:
        e.append(content)
    box.append(e)
    return box


# ---------------------------------------------------------------------------
# Simple Parser / Compiler
# ---------------------------------------------------------------------------

# Functions that render in roman (upright) style
_FUNCTIONS: set[str] = {
    "sin",
    "cos",
    "tan",
    "cot",
    "sec",
    "csc",
    "sinh",
    "cosh",
    "tanh",
    "coth",
    "arcsin",
    "arccos",
    "arctan",
    "log",
    "ln",
    "lg",
    "exp",
    "lim",
    "limsup",
    "liminf",
    "max",
    "min",
    "sup",
    "inf",
    "det",
    "dim",
    "ker",
    "hom",
    "Pr",
    "var",
    "cov",
    "corr",
    "mod",
    "pmod",
    "bmod",
}

# N-ary operators and their Unicode symbols
_NARY_OPS: dict[str, str] = {
    "int": "∫",
    "iint": "∬",
    "iiint": "∭",
    "oint": "∮",
    "sum": "∑",
    "prod": "∏",
    "coprod": "∐",
}

# Greek letters that are uppercase and thus upright
_UPRIGHT_GREEK: set[str] = {
    "Gamma",
    "Delta",
    "Theta",
    "Lambda",
    "Xi",
    "Pi",
    "Sigma",
    "Phi",
    "Psi",
    "Omega",
}


def _maybe_delim(c: str) -> tuple[str, str] | None:
    """Return (left, right) delimiter pair for a character, or None."""
    pairs = {
        "(": ("(", ")"),
        ")": ("(", ")"),
        "[": ("[", "]"),
        "]": ("[", "]"),
        "{": ("{", "}"),
        "}": ("{", "}"),
        "|": ("|", "|"),
    }
    return pairs.get(c)


def _resolve_symbol(name: str) -> str | None:
    """Resolve a LaTeX command name to a Unicode character."""
    if name in LATEX_GREEK_MAP:
        return LATEX_GREEK_MAP[name]
    if name in LATEX_SYMBOL_MAP:
        return LATEX_SYMBOL_MAP[name]
    return None


def _build_group(tokens: list[str], start: int) -> tuple[Any, int]:
    """Parse tokens[start:] and return (OMML element, new_index)."""
    elements: list[Any] = []
    i = start
    while i < len(tokens):
        token = tokens[i]

        # --- Braced group { ... } ---
        if token == "{":
            inner_start = i + 1
            depth = 1
            j = i + 1
            while j < len(tokens) and depth > 0:
                if tokens[j] == "{":
                    depth += 1
                elif tokens[j] == "}":
                    depth -= 1
                j += 1
            inner = tokens[inner_start : j - 1]
            group_elem, _ = _build_group(inner, 0)
            if group_elem is not None:
                elements.append(group_elem)
            i = j
            continue

        if token == "}":
            break

        # --- LaTeX command ---
        if token.startswith("\\"):
            cmd = token[1:]

            # \frac
            if cmd == "frac":
                num_elem, i = _build_group(tokens, i + 1)
                den_elem, i = _build_group(tokens, i + 1)
                if num_elem is not None and den_elem is not None:
                    elements.append(_mk_fraction(num_elem, den_elem))
                continue

            # \sqrt
            if cmd == "sqrt":
                degree_elem = None
                idx = i + 1
                if idx < len(tokens) and tokens[idx] == "[":
                    idx += 1
                    depth = 1
                    bracket_tokens = []
                    while idx < len(tokens) and depth > 0:
                        if tokens[idx] == "[":
                            depth += 1
                        elif tokens[idx] == "]":
                            depth -= 1
                            if depth > 0:
                                bracket_tokens.append(tokens[idx])
                        else:
                            bracket_tokens.append(tokens[idx])
                        idx += 1
                    if bracket_tokens:
                        degree_elem, _ = _build_group(bracket_tokens, 0)
                else:
                    idx = i + 1
                radicand_elem, i = _build_group(tokens, idx)
                if radicand_elem is not None:
                    elements.append(_mk_radical(radicand_elem, degree_elem))
                continue

            # \int, \sum, \prod, etc.
            if cmd in _NARY_OPS:
                symbol = _NARY_OPS[cmd]
                idx = i + 1
                lower = None
                upper = None
                if idx < len(tokens) and tokens[idx] == "_":
                    lower, idx = _build_group(tokens, idx + 1)
                if idx < len(tokens) and tokens[idx] == "^":
                    upper, idx = _build_group(tokens, idx + 1)
                base_elem, idx = _build_group(tokens, idx)
                base = base_elem if base_elem is not None else _mk_run("")
                elements.append(_mk_nary(symbol, base, lower, upper))
                i = idx
                continue

            # \lim
            if cmd == "lim":
                idx = i + 1
                lower = None
                if idx < len(tokens) and tokens[idx] == "_":
                    lower, idx = _build_group(tokens, idx + 1)
                elements.append(_mk_run("lim", italic=False))
                if lower is not None:
                    lim_elem = _m("limLow")
                    e = _m("e")
                    e.append(_mk_run("", italic=False))
                    lim_elem.append(e)
                    lim_elem.append(lower)
                    elements.append(lim_elem)
                i = idx
                continue

            # \lim with subscript
            if cmd in _FUNCTIONS:
                idx = i + 1
                sub_elem = None
                if idx < len(tokens) and tokens[idx] == "_":
                    sub_elem, idx = _build_group(tokens, idx + 1)
                arg_elem, idx = _build_group(tokens, idx)
                if sub_elem is not None:
                    elem = _mk_script(_mk_run(cmd, italic=False), sub_elem, None)
                    elements.append(elem)
                elif arg_elem is not None:
                    elements.append(_mk_function(cmd, arg_elem))
                else:
                    elements.append(_mk_run(cmd, italic=False))
                i = idx
                continue

            # \text
            if cmd == "text":
                idx = i + 1
                if idx < len(tokens) and tokens[idx] == "{":
                    # Find matching }
                    text_tokens = []
                    depth = 1
                    j = idx + 1
                    while j < len(tokens) and depth > 0:
                        if tokens[j] == "{":
                            depth += 1
                        elif tokens[j] == "}":
                            depth -= 1
                        if depth > 0:
                            text_tokens.append(tokens[j])
                        j += 1
                    text = "".join(text_tokens)
                    elements.append(_mk_run(text, italic=False))
                    i = j
                    continue

            # \left, \right, \bigl, \bigr, etc.
            if cmd in ("left", "right", "bigl", "bigr", "big", "Bigl", "Bigr", "Big"):
                # Just skip size commands
                i += 1
                continue

            # \cdot, \times, etc. handled by LATEX_SYMBOL_MAP
            # \alpha, \beta, etc.
            resolved = _resolve_symbol(cmd)
            if resolved:
                is_italic = cmd not in _UPRIGHT_GREEK and not cmd[0].isupper()
                elements.append(_mk_run(resolved, italic=is_italic))
                i += 1
                continue

            # \mathbf, \mathrm, \mathit
            if cmd in ("mathbf", "mathrm", "mathit", "mathcal", "mathbb", "mathscr"):
                idx = i + 1
                if idx < len(tokens) and tokens[idx] == "{":
                    inner_text = []
                    depth = 1
                    j = idx + 1
                    while j < len(tokens) and depth > 0:
                        if tokens[j] == "{":
                            depth += 1
                        elif tokens[j] == "}":
                            depth -= 1
                        if depth > 0:
                            inner_text.append(tokens[j])
                        j += 1
                    text = "".join(inner_text)
                    is_bold = cmd == "mathbf"
                    is_ital = cmd == "mathit"
                    elements.append(
                        _mk_run_bold(text) if is_bold else _mk_run(text, italic=is_ital)
                    )
                    i = j
                    continue

            # Unknown command — output as-is
            ch = _resolve_symbol(cmd)
            if ch:
                elements.append(_mk_run(ch, italic=False))
            else:
                elements.append(_mk_run(f"\\{cmd}", italic=False))
            i += 1
            continue

        # --- Superscript ^ ---
        if token == "^":
            sup_elem, i = _build_group(tokens, i + 1)
            if elements:
                last = elements.pop()
                elements.append(_mk_script(last, None, sup_elem))
            continue

        # --- Subscript _ ---
        if token == "_":
            sub_elem, i = _build_group(tokens, i + 1)
            if elements:
                last = elements.pop()
                elements.append(_mk_script(last, sub_elem, None))
            continue

        # --- Numbers ---
        if re.match(r"^\d+(?:\.\d+)?$", token):
            elements.append(_mk_run(token, italic=False))
            i += 1
            continue

        # --- Operators / Identifiers ---
        if token in ("+", "-", "=", ",", ";", ":", "!", "?"):
            elements.append(_mk_run(token, italic=False))
            i += 1
            continue

        if token in ("*", "/"):
            elements.append(_mk_run(token, italic=False))
            i += 1
            continue

        if token == "(":
            # Find matching ) or parse ahead
            inner, i = _build_group(tokens, i + 1)
            if inner is not None:
                elements.append(_mk_delimiter(inner, "(", ")"))
            continue

        if token == ")":
            break

        if token == "[":
            inner, i = _build_group(tokens, i + 1)
            if inner is not None:
                elements.append(_mk_delimiter(inner, "[", "]"))
            continue

        if token == "]":
            break

        if token == "|":
            inner, i = _build_group(tokens, i + 1)
            if inner is not None:
                elements.append(_mk_delimiter(inner, "|", "|"))
            continue

        if token == "&":
            i += 1
            continue

        if token == "~":
            elements.append(_mk_run(" ", italic=False))
            i += 1
            continue

        # --- Identifiers (variables) ---
        if re.match(r"^[a-zA-Z]+$", token):
            elements.append(_mk_run(token))
            i += 1
            continue

        # Fallback — single character
        elements.append(_mk_run(token, italic=token.isalpha()))
        i += 1

    # Merge adjacent runs into box if multiple
    if len(elements) == 0:
        return _mk_run(""), i
    if len(elements) == 1:
        return elements[0], i
    return _mk_box(_SequenceWrapper(elements)), i

    i = []


class _SequenceWrapper:
    """Helper that holds child elements for OMML grouping."""

    def __init__(self, children: list[Any]) -> None:
        self._children = children
        self.xml: str = ""

    def append_to(self, parent: Any) -> None:
        for child in self._children:
            parent.append(child)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def latex_to_omml(latex: str, display: bool = False) -> Any | None:
    """Convert LaTeX equation to OMML element tree.

    Returns an ``m:oMath`` (inline) or ``m:oMathPara`` (display) element
    for injection into a python-docx paragraph, or ``None`` on failure.

    Args:
        latex: LaTeX math expression.
        display: If True, create a display equation (``m:oMathPara``).
    """
    try:
        tokens = tokenize(latex)
    except Exception:
        return None

    try:
        body, _ = _build_group(tokens, 0)
    except Exception:
        return None

    if body is None:
        return None

    try:
        if display:
            para = _m("oMathPara")
            paraPr = _m("oMathParaPr")
            align = _m("jc")
            align.set(qn("m:val"), "center")
            paraPr.append(align)
            para.append(paraPr)
            math = _m("oMath")
            _append_body(math, body)
            para.append(math)
            return para
        else:
            math = _m("oMath")
            _append_body(math, body)
            return math
    except Exception:
        return None


def _append_body(math: Any, body: Any) -> None:
    """Append body element(s) to the math element."""
    if isinstance(body, _SequenceWrapper):
        body.append_to(math)
    elif body is not None:
        # Get the XML element from OxmlElement
        if hasattr(body, "append_to"):
            body.append_to(math)
        else:
            math.append(body)
