"""Tests for future format stubs (EPUB, LaTeX, PowerPoint)."""

import pytest

from pimd.export.formats import EpubRenderer, LatexRenderer, PptxRenderer
from pimd.export.formats.epub import EpubRenderer as Epub
from pimd.export.formats.latex import LatexRenderer as Latex
from pimd.export.formats.pptx import PptxRenderer as Pptx


class TestEpubRendererStub:
    def test_epub_format_info(self) -> None:
        renderer = EpubRenderer()
        assert renderer.FORMAT_NAME == "epub"
        assert not renderer.IMPLEMENTED

    def test_epub_render_raises(self) -> None:
        renderer = Epub()
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            renderer.render(None, "output.epub")

    def test_epub_render_to_bytes_raises(self) -> None:
        renderer = Epub()
        with pytest.raises(NotImplementedError):
            renderer.render_to_bytes(None)

    def test_epub_missing_dependencies(self) -> None:
        renderer = Epub()
        deps = renderer.missing_dependencies
        assert isinstance(deps, list)


class TestLatexRendererStub:
    def test_latex_format_info(self) -> None:
        renderer = LatexRenderer()
        assert renderer.FORMAT_NAME == "latex"
        assert not renderer.IMPLEMENTED

    def test_latex_render_raises(self) -> None:
        renderer = Latex()
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            renderer.render(None, "output.tex")

    def test_latex_is_not_available(self) -> None:
        renderer = Latex()
        assert not renderer.is_available


class TestPptxRendererStub:
    def test_pptx_format_info(self) -> None:
        renderer = PptxRenderer()
        assert renderer.FORMAT_NAME == "pptx"
        assert not renderer.IMPLEMENTED

    def test_pptx_render_raises(self) -> None:
        renderer = Pptx()
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            renderer.render(None, "output.pptx")

    def test_pptx_render_to_bytes_raises(self) -> None:
        renderer = Pptx()
        with pytest.raises(NotImplementedError):
            renderer.render_to_bytes(None)
