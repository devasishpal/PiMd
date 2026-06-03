"""Diagram renderer registry — register, lookup, list renderers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pimd.diagrams.renderers.base import DiagramRenderer


class DiagramRegistry:
    """Registry of all available diagram renderers.

    Usage::

        registry = DiagramRegistry()
        registry.register(mermaid_renderer)
        renderer = registry.get("mermaid")
    """

    def __init__(self) -> None:
        self._renderers: dict[str, DiagramRenderer] = {}

    def register(self, renderer: DiagramRenderer) -> None:
        """Register a renderer for its supported language."""
        lang = renderer.language.lower()
        self._renderers[lang] = renderer

    def get(self, language: str) -> DiagramRenderer | None:
        """Return the renderer for *language*, or ``None``."""
        return self._renderers.get(language.lower())

    def list_renderers(self) -> list[dict[str, str]]:
        """List all registered renderers with metadata."""
        return [
            {
                "language": r.language,
                "name": r.name,
                "version": r.version,
                "available": str(r.is_available()),
                "description": r.description,
            }
            for r in self._renderers.values()
        ]

    def __contains__(self, language: str) -> bool:
        return language.lower() in self._renderers

    def __len__(self) -> int:
        return len(self._renderers)
