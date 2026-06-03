"""Abstract base class for PiMD themes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docx import Document as DocxDocument


class Theme(ABC):
    """Base theme that defines visual styling for rendered documents.

    Subclasses override methods to control typography, colours, spacing,
    and element-specific formatting.
    """

    name: str = "base"

    @abstractmethod
    def configure_styles(self, doc: DocxDocument) -> None:
        """Configure built-in and custom paragraph / character styles.

        Args:
            doc: The python-docx Document whose styles should be modified.
        """
