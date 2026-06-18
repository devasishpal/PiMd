"""Diagram system — powered by PiDraw.

PiDraw is the authoritative diagram backend. All rendering is
delegated to PiDraw via the stable :mod:`pimd.diagrams.adapter` layer.
PiMD never implements its own diagram rendering logic.

Supported diagram languages are queried from PiDraw at runtime.
"""

from pimd.diagrams.adapter import (
    clear_cache,
    detect_language,
    doctor,
    get_supported_languages,
    is_supported_language,
    render_diagram,
    render_many_diagrams,
)
from pimd.diagrams.cache import DiagramCache, FileSystemDiagramCache, MemoryDiagramCache
from pimd.diagrams.engine import DiagramEngine
from pimd.diagrams.models import (
    DIAGRAM_LANGUAGES,
    DiagramConfig,
    DiagramContext,
    DiagramPlacement,
    DiagramResult,
    DiagramScaleMode,
    RenderResult,
)
from pimd.diagrams.plugin import DiagramHook, DiagramPlugin, DiagramPluginEvent, DiagramPluginManager
from pimd.diagrams.registry import (
    DiagramRegistry,
    get_diagram_renderer,
    list_diagram_renderers,
    register_diagram_renderer,
)

__all__ = [
    "render_diagram",
    "render_many_diagrams",
    "detect_language",
    "is_supported_language",
    "get_supported_languages",
    "clear_cache",
    "doctor",
    "DiagramEngine",
    "DiagramRegistry",
    "DiagramResult",
    "RenderResult",
    "DiagramConfig",
    "DiagramContext",
    "DiagramScaleMode",
    "DiagramPlacement",
    "DiagramPlugin",
    "DiagramPluginEvent",
    "DiagramPluginManager",
    "DiagramHook",
    "DIAGRAM_LANGUAGES",
    "DiagramCache",
    "MemoryDiagramCache",
    "FileSystemDiagramCache",
    "register_diagram_renderer",
    "get_diagram_renderer",
    "list_diagram_renderers",
]
