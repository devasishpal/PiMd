"""LaTeX renderer stub — future architecture for LaTeX/PDF output.

LaTeX support will be implemented in a future release.
The stub provides the renderer interface so callers can detect
and plan for LaTeX output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class LatexRenderer:
    """Render documents to LaTeX (stub — not yet implemented).

    Planned features:
    - Full LaTeX document generation from Document model
    - Configurable document classes (article, report, book)
    - Equation rendering via LaTeX natively
    - Bibliography via BibTeX/biblatex
    - Figure and table support
    - Custom packages and preamble
    """

    FORMAT_NAME = "latex"
    FORMAT_DESCRIPTION = "LaTeX typesetting format"
    IMPLEMENTED = False

    def __init__(self) -> None:
        pass

    @property
    def is_available(self) -> bool:
        return False

    @property
    def missing_dependencies(self) -> list[str]:
        return ["pdflatex (MiKTeX / TeX Live)"]

    def render(
        self,
        document: Any,
        output_path: str | Path,
        **options: Any,
    ) -> Path:
        raise NotImplementedError(
            "LaTeX rendering is not yet implemented. "
            "It is planned for a future release."
        )

    def render_to_bytes(self, document: Any, **options: Any) -> bytes:
        raise NotImplementedError("LaTeX rendering not yet implemented")
