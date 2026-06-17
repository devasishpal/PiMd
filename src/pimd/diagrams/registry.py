"""Diagram renderer registry — delegates to PiDraw's registry.

PiDraw is the single source of truth for all diagram rendering.
This module provides a PiMD-compatible API that wraps PiDraw's
registry. Plugin renderers can still be registered via the
global registry for PiMD-specific extensions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pimd.diagrams.pidraw_integration import (
    _HAS_PIDRAW,
    get_supported_languages,
    is_supported_language,
)

if TYPE_CHECKING:
    from pimd.diagrams.renderers.base import DiagramRenderer


_REGISTRY_INSTANCE: DiagramRegistry | None = None
_PLUGIN_RENDERERS: dict[str, DiagramRenderer] = {}


def _get_global_registry() -> DiagramRegistry:
    global _REGISTRY_INSTANCE
    if _REGISTRY_INSTANCE is None:
        _REGISTRY_INSTANCE = DiagramRegistry()
    return _REGISTRY_INSTANCE


def register_diagram_renderer(language: str, renderer: DiagramRenderer) -> None:
    """Register a third-party diagram renderer.

    This is the public plugin API for registering custom diagram renderers
    that are not provided by PiDraw.

    Usage::

        from pimd import register_diagram_renderer

        register_diagram_renderer("customdsl", CustomRenderer())
    """
    renderer.language = language
    _PLUGIN_RENDERERS[language.lower()] = renderer
    _get_global_registry().register(renderer)


def get_diagram_renderer(language: str) -> DiagramRenderer | None:
    """Look up a renderer by language from the global registry."""
    return _get_global_registry().get(language)


def list_diagram_renderers() -> list[dict[str, str]]:
    """List all registered renderers from the global registry."""
    return _get_global_registry().list_renderers()


class DiagramRegistry:
    """Registry of all available diagram renderers.

    Wrap PiDraw's renderers and any PiMD plugin renderers.
    """

    def __init__(self) -> None:
        self._renderers: dict[str, DiagramRenderer] = {}

    def register(self, renderer: DiagramRenderer) -> None:
        """Register a renderer for its supported language."""
        lang = renderer.language.lower()
        self._renderers[lang] = renderer

    def get(self, language: str) -> DiagramRenderer | None:
        """Return the renderer for *language*, or ``None``.

        Checks PiDraw's supported languages first, then plugin renderers.
        """
        lang = language.lower()
        # Check PiMD plugin renderers first
        if lang in self._renderers:
            return self._renderers[lang]
        # Check PiDraw-supported languages (no actual renderer object needed)
        if is_supported_language(lang):
            from pimd.diagrams.renderers.base import DiagramRenderer

            class _PiDrawAdapterRenderer(DiagramRenderer):
                language = lang
                name = f"PiDraw {lang}"
                version = "1.0"
                description = f"PiDraw renderer for {lang}"

                def is_available(self) -> bool:
                    return _HAS_PIDRAW

                def render(
                    self, source: str, **options: object
                ) -> DiagramResult:  # noqa: F821
                    from pimd.diagrams.pidraw_integration import render_diagram

                    return render_diagram(
                        source,
                        lang,
                        dpi=options.get("dpi", 300),
                        transparent=options.get("transparent", True),
                    )

            adapter = _PiDrawAdapterRenderer()
            self._renderers[lang] = adapter
            return adapter
        return None

    def list_renderers(self) -> list[dict[str, str]]:
        """List all registered renderers with metadata."""
        pidraw_langs = get_supported_languages()
        items = []
        for lang, name in pidraw_langs.items():
            items.append({
                "language": lang,
                "name": f"PiDraw {name}",
                "version": "1.0",
                "available": str(_HAS_PIDRAW),
                "description": f"Rendered via PiDraw ({name})",
            })
        for r in self._renderers.values():
            if r.language not in pidraw_langs:
                items.append({
                    "language": r.language,
                    "name": r.name,
                    "version": r.version,
                    "available": str(r.is_available()),
                    "description": r.description,
                })
        return items

    def __contains__(self, language: str) -> bool:
        return language.lower() in self._renderers or is_supported_language(language)

    def __len__(self) -> int:
        return len(self._renderers) + len(get_supported_languages())
