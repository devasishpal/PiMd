"""Future format renderers — EPUB, LaTeX, PowerPoint rendering architecture."""

from pimd.export.formats.epub import EpubRenderer, validate_epub
from pimd.export.formats.latex import LatexRenderer

try:
    from pimd.export.formats.pptx import PptxRenderer
except ImportError:
    class PptxRenderer:  # type: ignore
        """PowerPoint renderer stub."""
        FORMAT_NAME = "pptx"
        IMPLEMENTED = False

        def render(self, *args, **kwargs):  # type: ignore
            raise NotImplementedError("PPTX rendering not yet implemented")

__all__ = [
    "EpubRenderer",
    "validate_epub",
    "LatexRenderer",
    "PptxRenderer",
]
