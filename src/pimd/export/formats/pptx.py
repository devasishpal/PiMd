"""PowerPoint renderer stub — future architecture for presentation output.

PowerPoint support will be implemented in a future release.
The stub provides the renderer interface so callers can detect
and plan for PPTX output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class PptxRenderer:
    """Render documents to PowerPoint (stub — not yet implemented).

    Planned features:
    - Slide generation from Document model headings (H1 = slide title)
    - Slide layouts and master slides
    - Image, table, and diagram placement on slides
    - Speaker notes extraction
    - Templates and themes
    """

    FORMAT_NAME = "pptx"
    FORMAT_DESCRIPTION = "PowerPoint presentation format"
    IMPLEMENTED = False

    def __init__(self) -> None:
        self._available = self._check_dependencies()

    @staticmethod
    def _check_dependencies() -> bool:
        try:
            __import__("pptx")
            return True
        except ImportError:
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def missing_dependencies(self) -> list[str]:
        deps: list[str] = []
        try:
            __import__("pptx")
        except ImportError:
            deps.append("python-pptx")
        return deps

    def render(
        self,
        document: Any,
        output_path: str | Path,
        **options: Any,
    ) -> Path:
        raise NotImplementedError(
            "PowerPoint rendering is not yet implemented. "
            "It is planned for a future release."
        )

    def render_to_bytes(self, document: Any, **options: Any) -> bytes:
        raise NotImplementedError("PowerPoint rendering not yet implemented")
