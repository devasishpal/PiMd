"""Diagram system — render, cache, and embed diagrams automatically."""

from pimd.diagrams.cache import DiagramCache, FileSystemDiagramCache, MemoryDiagramCache
from pimd.diagrams.engine import DiagramEngine
from pimd.diagrams.models import DIAGRAM_LANGUAGES, DiagramConfig, DiagramResult, RenderResult
from pimd.diagrams.registry import (
    DiagramRegistry,
    get_diagram_renderer,
    list_diagram_renderers,
    register_diagram_renderer,
)

__all__ = [
    "DiagramEngine",
    "DiagramRegistry",
    "DiagramResult",
    "RenderResult",
    "DiagramConfig",
    "DIAGRAM_LANGUAGES",
    "DiagramCache",
    "MemoryDiagramCache",
    "FileSystemDiagramCache",
    "register_diagram_renderer",
    "get_diagram_renderer",
    "list_diagram_renderers",
]
