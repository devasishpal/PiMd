"""Tests for the diagram system: engine, registry, cache, renderers."""

from __future__ import annotations

from pathlib import Path

import pytest

from pimd.diagrams import DiagramEngine, DiagramRegistry
from pimd.diagrams.cache import (
    FileSystemDiagramCache,
    MemoryDiagramCache,
)
from pimd.diagrams.models import DIAGRAM_LANGUAGES, DiagramConfig, DiagramResult
from pimd.diagrams.renderers import DiagramRenderer
from pimd.diagrams.renderers.ascii import AsciiRenderer
from pimd.diagrams.renderers.d2 import D2Renderer
from pimd.diagrams.renderers.graphviz import GraphvizRenderer
from pimd.diagrams.renderers.mermaid import MermaidRenderer
from pimd.diagrams.renderers.plantuml import PlantUMLRenderer
from pimd.diagrams.renderers.svg import SvgRenderer

# ======================================================================
# DiagramResult
# ======================================================================


class TestDiagramResult:
    def test_default_construction(self) -> None:
        r = DiagramResult(source="a -> b", language="mermaid")
        assert r.source == "a -> b"
        assert r.language == "mermaid"
        assert r.error is None
        assert not r.cached

    def test_success_property_no_error(self) -> None:
        r = DiagramResult(source="", language="x", png=b"abc")
        assert r.success

    def test_success_property_with_error(self) -> None:
        r = DiagramResult(source="", language="x", error="fail")
        assert not r.success

    def test_to_dict(self) -> None:
        r = DiagramResult(
            source="src",
            language="dot",
            png=b"data",
            width=100,
            height=200,
            render_time=0.5,
        )
        d = r.to_dict()
        assert d["language"] == "dot"
        assert d["width"] == 100
        assert d["height"] == 200
        assert d["success"]
        assert d["render_time"] == 0.5


# ======================================================================
# DiagramConfig
# ======================================================================


class TestDiagramConfig:
    def test_defaults(self) -> None:
        c = DiagramConfig()
        assert c.default_width == 600
        assert c.default_height == 400
        assert c.dpi == 150
        assert c.fallback_to_code_block

    def test_custom_values(self) -> None:
        c = DiagramConfig(default_width=800, add_captions=False)
        assert c.default_width == 800
        assert not c.add_captions


# ======================================================================
# DIAGRAM_LANGUAGES
# ======================================================================


class TestDiagramLanguages:
    def test_known_languages(self) -> None:
        assert "mermaid" in DIAGRAM_LANGUAGES
        assert "plantuml" in DIAGRAM_LANGUAGES
        assert "dot" in DIAGRAM_LANGUAGES
        assert "d2" in DIAGRAM_LANGUAGES
        assert "ascii" in DIAGRAM_LANGUAGES
        assert "svg" in DIAGRAM_LANGUAGES

    def test_aliases(self) -> None:
        assert DIAGRAM_LANGUAGES["mmd"] == "Mermaid"
        assert DIAGRAM_LANGUAGES["puml"] == "PlantUML"
        assert DIAGRAM_LANGUAGES["graphviz"] == "Graphviz"


# ======================================================================
# DiagramRegistry
# ======================================================================


class _FakeRenderer(DiagramRenderer):
    language = "test"
    name = "Fake"
    version = "1.0"
    description = "Fake renderer for testing"

    def is_available(self) -> bool:
        return True

    def render(self, source: str, **options: object) -> DiagramResult:
        return DiagramResult(
            source=source,
            language=self.language,
            png=b"fake_png",
        )


class TestDiagramRegistry:
    def test_empty_registry(self) -> None:
        reg = DiagramRegistry()
        assert len(reg) == 0
        assert reg.get("test") is None
        assert "test" not in reg

    def test_register_and_get(self) -> None:
        reg = DiagramRegistry()
        r = _FakeRenderer()
        reg.register(r)
        assert len(reg) == 1
        assert reg.get("test") is r
        assert "test" in reg

    def test_register_case_insensitive(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        assert reg.get("TEST") is not None

    def test_register_overwrites(self) -> None:
        reg = DiagramRegistry()
        r1 = _FakeRenderer()
        r2 = _FakeRenderer()
        reg.register(r1)
        reg.register(r2)
        assert len(reg) == 1
        assert reg.get("test") is r2

    def test_list_renderers(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        items = reg.list_renderers()
        assert len(items) == 1
        assert items[0]["language"] == "test"
        assert items[0]["name"] == "Fake"

    def test_contains(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        assert "test" in reg
        assert "nonexistent" not in reg


# ======================================================================
# DiagramEngine
# ======================================================================


class TestDiagramEngine:
    def test_instantiation(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        engine = DiagramEngine(registry=reg)
        assert engine.registry is reg

    def test_render_known_language(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        engine = DiagramEngine(registry=reg)
        result = engine.render("source code", "test")
        assert result.success
        assert result.png == b"fake_png"

    def test_render_unknown_language(self) -> None:
        reg = DiagramRegistry()
        engine = DiagramEngine(registry=reg)
        result = engine.render("source code", "unknown")
        assert not result.success
        assert result.error is not None

    def test_render_case_insensitive(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        engine = DiagramEngine(registry=reg)
        result = engine.render("src", "TEST")
        assert result.success


# ======================================================================
# Caching
# ======================================================================


class TestMemoryDiagramCache:
    def test_set_and_get(self) -> None:
        cache = MemoryDiagramCache()
        result = DiagramResult(source="src", language="t", png=b"data")
        cache.set("key1", result)
        cached = cache.get("key1")
        assert cached is not None
        assert cached.png == b"data"

    def test_get_missing(self) -> None:
        cache = MemoryDiagramCache()
        assert cache.get("nope") is None

    def test_clear(self) -> None:
        cache = MemoryDiagramCache()
        cache.set("k", DiagramResult(source="", language="t", png=b"d"))
        cache.clear()
        assert cache.get("k") is None

    def test_ttl(self) -> None:
        import time

        cache = MemoryDiagramCache(default_ttl=0.1)
        cache.set("k", DiagramResult(source="", language="t", png=b"d"))
        assert cache.get("k") is not None
        time.sleep(0.15)
        assert cache.get("k") is None


class TestFileSystemDiagramCache:
    def test_set_and_get(self, tmp_path: Path) -> None:
        cache = FileSystemDiagramCache(cache_dir=str(tmp_path / "diagrams"))
        result = DiagramResult(source="src", language="t", png=b"pngdata", svg="<svg/>")
        cache.set("key1", result)
        cached = cache.get("key1")
        assert cached is not None
        assert cached.png == b"pngdata"
        assert cached.svg == "<svg/>"

    def test_get_missing(self, tmp_path: Path) -> None:
        cache = FileSystemDiagramCache(cache_dir=str(tmp_path / "diagrams"))
        assert cache.get("nope") is None

    def test_clear(self, tmp_path: Path) -> None:
        cache = FileSystemDiagramCache(cache_dir=str(tmp_path / "diagrams"))
        cache.set("k", DiagramResult(source="", language="t", png=b"x"))
        cache.clear()
        assert cache.get("k") is None
        # Directory should still exist but be empty
        assert list((tmp_path / "diagrams").iterdir()) == list()


# ======================================================================
# Renderers
# ======================================================================


class TestMermaidRenderer:
    def test_language_and_name(self) -> None:
        r = MermaidRenderer()
        assert r.language == "mermaid"
        assert r.name == "Mermaid"

    def test_priority(self) -> None:
        r = MermaidRenderer()
        assert r.priority == 10


class TestPlantUMLRenderer:
    def test_language_and_name(self) -> None:
        r = PlantUMLRenderer()
        assert r.language == "plantuml"

    def test_priority(self) -> None:
        r = PlantUMLRenderer()
        assert r.priority == 20


class TestGraphvizRenderer:
    def test_language_and_name(self) -> None:
        r = GraphvizRenderer()
        assert r.language == "dot"

    def test_priority(self) -> None:
        r = GraphvizRenderer()
        assert r.priority == 30


class TestD2Renderer:
    def test_language_and_name(self) -> None:
        r = D2Renderer()
        assert r.language == "d2"

    def test_priority(self) -> None:
        r = D2Renderer()
        assert r.priority == 40


class TestAsciiRenderer:
    def test_language_and_name(self) -> None:
        r = AsciiRenderer()
        assert r.language == "ascii"

    def test_priority(self) -> None:
        r = AsciiRenderer()
        assert r.priority == 50

    def test_pillow_not_available_returns_error(self) -> None:
        # Monkey-patch is_available to False
        r = AsciiRenderer()
        original = r.is_available
        r.is_available = lambda: False  # type: ignore
        result = r.render("test")
        assert result.error is not None
        assert "Pillow" in result.error
        r.is_available = original

    def test_render_empty_source(self) -> None:
        r = AsciiRenderer()
        if not r.is_available():
            pytest.skip("Pillow not installed")
        result = r.render("")
        assert result.error is not None


class TestSvgRenderer:
    def test_language_and_name(self) -> None:
        r = SvgRenderer()
        assert r.language == "svg"

    def test_priority(self) -> None:
        r = SvgRenderer()
        assert r.priority == 60

    def test_inline_svg_renders_without_error(self) -> None:
        r = SvgRenderer()
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'
        result = r.render(svg)
        assert result.svg == svg
        # PNG may be None if no converter available, but no error
        assert result.error is None


# ======================================================================
# Base Renderer
# ======================================================================


class TestDiagramRendererBase:
    def test_abc_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            DiagramRenderer()  # type: ignore

    def test_renderer_unavailable_graceful(self) -> None:
        """Renderers that fail should return error, not raise."""

        class BrokenRenderer(DiagramRenderer):
            language = "broken"
            name = "Broken"
            version = "1"
            description = ""

            def is_available(self) -> bool:
                return True

            def render(self, source: str, **options: object) -> DiagramResult:
                raise RuntimeError("something bad")

        r = BrokenRenderer()
        # Engine should catch the exception
        reg = DiagramRegistry()
        reg.register(r)
        engine = DiagramEngine(registry=reg)
        result = engine.render("src", "broken")
        assert not result.success
        assert result.error is not None
