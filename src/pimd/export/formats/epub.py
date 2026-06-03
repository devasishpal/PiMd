"""EPUB renderer stub — future architecture for e-book output.

EPUB support will be implemented in a future release.
The stub provides the renderer interface so callers can detect
and plan for EPUB output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class EpubRenderer:
    """Render documents to EPUB format (stub — not yet implemented).

    Planned features:
    - XHTML content generation from Document model
    - EPUB 3.2 specification compliance
    - CSS styling with reflowable layout
    - Table of Contents (NCX + nav.xhtml)
    - Image and asset embedding
    - Metadata (title, author, ISBN, etc.)
    """

    FORMAT_NAME = "epub"
    FORMAT_DESCRIPTION = "EPUB 3.2 e-book format"
    IMPLEMENTED = False

    def __init__(self) -> None:
        self._available = self._check_dependencies()

    @staticmethod
    def _check_dependencies() -> bool:
        try:
            __import__("lxml")
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
            __import__("lxml")
        except ImportError:
            deps.append("lxml")
        return deps

    def render(
        self,
        document: Any,
        output_path: str | Path,
        **options: Any,
    ) -> Path:
        """Render a document model to EPUB (not yet implemented)."""
        raise NotImplementedError(
            "EPUB rendering is not yet implemented. "
            "It is planned for a future release. "
            "Contributions welcome: https://github.com/devasishpal/PiMd"
        )

    def render_to_bytes(self, document: Any, **options: Any) -> bytes:
        raise NotImplementedError("EPUB rendering not yet implemented")
