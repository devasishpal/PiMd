"""Converter interface — ABC + registry for document converters.

This module is the foundation for MarkItDown and other converter integration.
All document converters (Markdown, HTML, future MarkItDown, etc.) implement
the :class:`Converter` ABC and auto-register via the :class:`ConverterRegistry`.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConverterCapability(enum.Enum):
    MARKDOWN_TO_DOCX = "markdown_to_docx"
    HTML_TO_DOCX = "html_to_docx"
    MARKDOWN_TO_HTML = "markdown_to_html"
    HTML_TO_MARKDOWN = "html_to_markdown"
    MARKDOWN_TO_EPUB = "markdown_to_epub"
    MARKDOWN_TO_LATEX = "markdown_to_latex"
    MARKDOWN_TO_TEXT = "markdown_to_text"
    MARKDOWN_TO_PDF = "markdown_to_pdf"


@dataclass
class ConversionResult:
    success: bool
    output_path: Path | None = None
    output_bytes: bytes | None = None
    error: str | None = None
    duration: float = 0.0


class Converter(ABC):
    """Abstract base class for all document converters.

    Subclasses must implement :meth:`convert` and declare their
    :attr:`capability`.
    """

    capability: ConverterCapability
    """The type of conversion this converter handles."""

    name: str = ""
    """Human-readable name (defaults to class name)."""

    version: str = "1.0.0"
    """Converter version."""

    @abstractmethod
    def convert(
        self,
        source: str | Path,
        destination: str | Path | None = None,
        **options: Any,
    ) -> ConversionResult:
        """Convert *source* (file path or text) to *destination*.

        Args:
            source: Input file path or raw text content.
            destination: Output file path (``None`` = return bytes).
            **options: Converter-specific options.

        Returns:
            :class:`ConversionResult` — always, even on error.
        """

    def validate_source(self, source: str | Path) -> list[str]:
        """Validate the source before conversion. Return list of issues."""
        return []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.name:
            cls.name = cls.__name__


class ConverterRegistry:
    """Registry for discovering :class:`Converter` implementations."""

    def __init__(self) -> None:
        self._converters: dict[str, type[Converter]] = {}
        self._by_capability: dict[ConverterCapability, list[type[Converter]]] = {}

    def register(self, converter_cls: type[Converter]) -> None:
        name = converter_cls.name or converter_cls.__name__
        self._converters[name] = converter_cls
        cap = getattr(converter_cls, "capability", None)
        if cap is not None:
            self._by_capability.setdefault(cap, []).append(converter_cls)

    def get(self, name: str) -> type[Converter] | None:
        return self._converters.get(name)

    def get_by_capability(self, capability: ConverterCapability) -> list[type[Converter]]:
        return self._by_capability.get(capability, [])

    def list_all(self) -> list[type[Converter]]:
        return list(self._converters.values())

    def clear(self) -> None:
        self._converters.clear()
        self._by_capability.clear()


_CONVERTER_REGISTRY: ConverterRegistry | None = None


def get_converter_registry() -> ConverterRegistry:
    global _CONVERTER_REGISTRY
    if _CONVERTER_REGISTRY is None:
        _CONVERTER_REGISTRY = ConverterRegistry()
    return _CONVERTER_REGISTRY


def reset_converter_registry() -> None:
    global _CONVERTER_REGISTRY
    _CONVERTER_REGISTRY = None


__all__ = [
    "Converter",
    "ConverterCapability",
    "ConversionResult",
    "ConverterRegistry",
    "get_converter_registry",
    "reset_converter_registry",
]
