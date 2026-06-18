"""Abstract base for diagram renderers — concrete implementations are in PiDraw.

PiMD only provides the :class:`DiagramRenderer` ABC so that plugin authors
can define custom renderers. All built-in renderers live in PiDraw.
"""

from pimd.diagrams.renderers.base import DiagramRenderer

__all__ = [
    "DiagramRenderer",
]
