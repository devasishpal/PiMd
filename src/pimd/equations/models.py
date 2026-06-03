"""Equation data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EquationResult:
    """Result of rendering a single equation."""

    source: str
    latex: str
    display: bool = False
    omml: Any = None  # lxml element tree — the OMML XML for native Word
    svg: str | None = None
    error: str | None = None
    cached: bool = False
    render_time: float = 0.0
    label: str | None = None
    number: int | None = None
    is_chemical: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.error is None and (self.omml is not None or self.svg is not None)

    @property
    def has_omml(self) -> bool:
        return self.omml is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "latex": self.latex,
            "display": self.display,
            "has_omml": self.has_omml,
            "has_svg": self.svg is not None,
            "error": self.error,
            "cached": self.cached,
            "render_time": round(self.render_time, 4),
            "success": self.success,
            "label": self.label,
            "number": self.number,
            "is_chemical": self.is_chemical,
        }


@dataclass
class EquationConfig:
    """Configuration for the equation rendering system."""

    enabled: bool = True
    auto_detect: bool = True
    prefer_omml: bool = True
    numbering_enabled: bool = True
    max_equations: int = 10000
    label_prefix: str = "eq"
    cache_enabled: bool = True
    cache_ttl: int = 7200
    temp_dir: str | None = None


DELIMITER_PATTERNS: dict[str, tuple[str, str, bool]] = {
    "dollar_inline": (r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", "$", "$"),
    "dollar_display": (r"\$\$(.+?)\$\$", "$$", "$$"),
    "paren_inline": (r"\\\((.+?)\\\)", r"\(", r"\)"),
    "bracket_display": (r"\\\[(.+?)\\\]", r"\[", r"\]"),
    "equation_env": (
        r"\\begin\{equation\}(.+?)\\end\{equation\}",
        r"\begin{equation}",
        r"\end{equation}",
    ),
    "equation_star_env": (
        r"\\begin{equation\*}(.+?)\\end{equation\*}",
        r"\begin{equation*}",
        r"\end{equation*}",
    ),
    "align_env": (
        r"\\begin{align}(.+?)\\end{align}",
        r"\begin{align}",
        r"\end{align}",
    ),
    "align_star_env": (
        r"\\begin{align\*}(.+?)\\end{align\*}",
        r"\begin{align*}",
        r"\end{align*}",
    ),
}

CHEMICAL_PATTERNS = [
    (r"\bH_2O\b", "H₂O"),
    (r"\bCO_2\b", "CO₂"),
    (r"\bCH_4\b", "CH₄"),
    (r"\bNH_3\b", "NH₃"),
    (r"\bNaCl\b", "NaCl"),
]

LATEX_GREEK_MAP: dict[str, str] = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "varepsilon": "ε",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "vartheta": "ϑ",
    "iota": "ι",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "omicron": "ο",
    "pi": "π",
    "varpi": "ϖ",
    "rho": "ρ",
    "sigma": "σ",
    "varsigma": "ς",
    "tau": "τ",
    "upsilon": "υ",
    "phi": "φ",
    "varphi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
    "Gamma": "Γ",
    "Delta": "Δ",
    "Theta": "Θ",
    "Lambda": "Λ",
    "Xi": "Ξ",
    "Pi": "Π",
    "Sigma": "Σ",
    "Phi": "Φ",
    "Psi": "Ψ",
    "Omega": "Ω",
}

LATEX_SYMBOL_MAP: dict[str, str] = {
    "infty": "∞",
    "partial": "∂",
    "nabla": "∇",
    "hbar": "ℏ",
    "ell": "ℓ",
    "imath": "ı",
    "jmath": "ȷ",
    "Re": "ℜ",
    "Im": "ℑ",
    "aleph": "ℵ",
    "wp": "℘",
    "exists": "∃",
    "nexists": "∄",
    "forall": "∀",
    "neg": "¬",
    "lnot": "¬",
    "wedge": "∧",
    "vee": "∨",
    "oplus": "⊕",
    "otimes": "⊗",
    "odot": "⊙",
    "ominus": "⊖",
    "cap": "∩",
    "cup": "∪",
    "subset": "⊂",
    "supset": "⊃",
    "subseteq": "⊆",
    "supseteq": "⊇",
    "subsetneq": "⊊",
    "in": "∈",
    "notin": "∉",
    "ni": "∋",
    "emptyset": "∅",
    "varnothing": "∅",
    "angle": "∠",
    "perp": "⊥",
    "mid": "∣",
    "parallel": "∥",
    "backslash": "∖",
    "cdot": "·",
    "cdots": "⋯",
    "vdots": "⋮",
    "ddots": "⋱",
    "times": "×",
    "div": "÷",
    "pm": "±",
    "mp": "∓",
    "ast": "∗",
    "star": "⋆",
    "circ": "∘",
    "bullet": "∙",
    "dagger": "†",
    "ddagger": "‡",
    "leq": "≤",
    "geq": "≥",
    "neq": "≠",
    "equiv": "≡",
    "approx": "≈",
    "sim": "∼",
    "simeq": "≃",
    "cong": "≅",
    "propto": "∝",
    "ll": "≪",
    "gg": "≫",
    "leftarrow": "←",
    "rightarrow": "→",
    "leftrightarrow": "↔",
    "Leftarrow": "⇐",
    "Rightarrow": "⇒",
    "Leftrightarrow": "⇔",
    "longleftarrow": "⟵",
    "longrightarrow": "⟶",
    "uparrow": "↑",
    "downarrow": "↓",
    "updownarrow": "↕",
    "mapsto": "↦",
    "longmapsto": "⟼",
    "to": "→",
    "gets": "←",
    "imply": "⇒",
    "implies": "⇒",
    "triangle": "△",
    "surd": "√",
    "sqrt": "√",
    "measuredangle": "∡",
    "therefore": "∴",
    "because": "∵",
    "Box": "□",
    "Diamond": "◇",
    "colon": ":",
    "ldotp": ".",
    "cdotp": "·",
    "centerdot": "·",
    "dots": "…",
    "dotsc": "…",
    "dotso": "…",
    "dotsb": "⋯",
    "dotsm": "⋯",
    "dotsi": "⋯",
}
