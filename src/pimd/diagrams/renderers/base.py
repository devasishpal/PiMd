"""Abstract base class for all diagram renderers."""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from typing import Any

from pimd.diagrams.models import DiagramResult


class DiagramRenderer(ABC):
    """Base class for diagram rendering backends.

    Subclasses override :meth:`render` and :meth:`is_available` to
    implement support for a specific diagram language.
    """

    language: str = ""
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    priority: int = 100

    @abstractmethod
    def render(self, source: str, **options: Any) -> DiagramResult:
        """Render a diagram from *source* text.

        Args:
            source: Raw diagram source code.
            **options: Rendering options (width, height, theme, etc.).

        Returns:
            A :class:`DiagramResult` with rendered output.
        """

    def is_available(self) -> bool:
        """Check if this renderer's dependencies are installed.

        Override in subclasses that require external tools.
        """
        return True

    def _tool_name(self) -> str:
        """Return the name of the external tool (for error messages)."""
        return self.name

    @staticmethod
    def _which(tool: str) -> bool:
        """Check if a CLI tool is available on ``PATH``."""
        return shutil.which(tool) is not None
