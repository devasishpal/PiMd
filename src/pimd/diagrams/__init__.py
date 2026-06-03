"""Diagram system — render, cache, and embed diagrams automatically."""

from pimd.diagrams.cache import DiagramCache, FileSystemDiagramCache, MemoryDiagramCache
from pimd.diagrams.engine import DiagramEngine
from pimd.diagrams.models import DiagramConfig, DiagramResult
from pimd.diagrams.registry import DiagramRegistry

__all__ = [
    "DiagramEngine",
    "DiagramRegistry",
    "DiagramResult",
    "DiagramConfig",
    "DiagramCache",
    "MemoryDiagramCache",
    "FileSystemDiagramCache",
]
