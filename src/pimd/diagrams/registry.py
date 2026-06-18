"""Diagram renderer registry — delegates to PiDraw.

PiDraw is the single source of truth. Plugin renderers for languages
not supported by PiDraw can still be registered here.
"""

from __future__ import annotations

from pimd.diagrams.adapter import _HAS_PIDRAW, get_supported_languages, is_supported_language
from pimd.diagrams.renderers.base import DiagramRenderer

_PLUGIN_RENDERERS: dict[str, DiagramRenderer] = {}


class DiagramRegistry:
    """Registry for diagram renderers — wraps PiDraw + plugin renderers."""

    def __init__(self) -> None:
        self._renderers: dict[str, DiagramRenderer] = {}

    def register(self, renderer: DiagramRenderer) -> None:
        self._renderers[renderer.language.lower()] = renderer

    def get(self, language: str) -> DiagramRenderer | None:
        lang = language.lower()
        if lang in self._renderers:
            return self._renderers[lang]
        if is_supported_language(lang):
            return _PiDrawAdapter(lang)
        return None

    def list_renderers(self) -> list[dict[str, str]]:
        pidraw_langs = get_supported_languages()
        items = []
        for lang, name in pidraw_langs.items():
            items.append({
                "language": lang, "name": f"PiDraw {name}",
                "version": "1.0", "available": str(_HAS_PIDRAW),
                "description": f"Rendered via PiDraw ({name})",
            })
        for r in self._renderers.values():
            if r.language not in pidraw_langs:
                items.append({
                    "language": r.language, "name": r.name,
                    "version": r.version, "available": str(r.is_available()),
                    "description": r.description,
                })
        return items

    def __contains__(self, language: str) -> bool:
        return language.lower() in self._renderers or is_supported_language(language)

    def __len__(self) -> int:
        return len(self._renderers) + len(get_supported_languages())


class _PiDrawAdapter(DiagramRenderer):
    """Adapter that wraps PiDraw renderers as DiagramRenderer instances."""

    def __init__(self, language: str) -> None:
        self.language = language
        self.name = f"PiDraw {language}"
        self.version = "1.0"
        self.description = f"Rendered via PiDraw ({language})"

    def is_available(self) -> bool:
        return _HAS_PIDRAW

    def render(self, source: str, **options: object) -> DiagramResult:  # noqa: F821
        from pimd.diagrams.adapter import render_diagram
        return render_diagram(source, self.language, dpi=options.get("dpi", 300), transparent=options.get("transparent", True))


def register_diagram_renderer(language: str, renderer: DiagramRenderer) -> None:
    renderer.language = language
    _PLUGIN_RENDERERS[language.lower()] = renderer


def get_diagram_renderer(language: str) -> DiagramRenderer | None:
    lang = language.lower()
    if lang in _PLUGIN_RENDERERS:
        return _PLUGIN_RENDERERS[lang]
    if is_supported_language(lang):
        return _PiDrawAdapter(lang)
    return None


def list_diagram_renderers() -> list[dict[str, str]]:
    items = DiagramRegistry().list_renderers()
    for renderer in _PLUGIN_RENDERERS.values():
        if not any(item["language"] == renderer.language for item in items):
            items.append({
                "language": renderer.language,
                "name": renderer.name,
                "version": renderer.version,
                "available": str(renderer.is_available()),
                "description": renderer.description,
            })
    return items
