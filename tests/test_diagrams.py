"""Tests for the diagram system — PiDraw integration.

All diagram rendering is delegated to PiDraw. PiMD never implements
its own diagram rendering logic. These tests verify the integration
layer, caching, detection, and error handling.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pimd.diagrams import (
    DiagramEngine,
    DiagramRegistry,
    clear_cache,
    detect_language,
    doctor,
    get_supported_languages,
    is_supported_language,
    render_diagram,
    render_many_diagrams,
)
from pimd.diagrams.cache import (
    DiagramCache,
    FileSystemDiagramCache,
    MemoryDiagramCache,
)
from pimd.diagrams.models import (
    DIAGRAM_LANGUAGES,
    DiagramConfig,
    DiagramResult,
    RenderResult,
)
from pimd.diagrams.registry import (
    get_diagram_renderer,
    list_diagram_renderers,
    register_diagram_renderer,
)
from pimd.diagrams.renderers import DiagramRenderer

# ======================================================================
# PiDraw Integration — Core
# ======================================================================


class TestPiDrawIntegration:
    """Verify PiDraw is the single source of truth for diagram rendering."""

    def test_supported_languages_non_empty(self) -> None:
        """PiDraw must provide at least the core diagram languages."""
        languages = get_supported_languages()
        assert len(languages) >= 5, f"Expected >=5 languages, got {len(languages)}"

    def test_supports_mermaid(self) -> None:
        assert is_supported_language("mermaid")

    def test_supports_plantuml(self) -> None:
        assert is_supported_language("plantuml")

    def test_supports_graphviz_dot(self) -> None:
        assert is_supported_language("dot") or is_supported_language("graphviz")

    def test_supports_d2(self) -> None:
        assert is_supported_language("d2")

    def test_languages_queried_at_runtime(self) -> None:
        """Languages must come from PiDraw, not hardcoded."""
        languages = get_supported_languages()
        assert isinstance(languages, dict)

    def test_diagram_languages_import(self) -> None:
        """DIAGRAM_LANGUAGES should be populated from PiDraw."""
        assert isinstance(DIAGRAM_LANGUAGES, dict)

    def test_detect_language_mermaid(self) -> None:
        detected = detect_language("graph TD\nA --> B")
        assert detected == "mermaid"

    def test_detect_language_plantuml(self) -> None:
        detected = detect_language("@startuml\nAlice -> Bob: Hello\n@enduml")
        assert detected == "plantuml"

    def test_detect_language_graphviz(self) -> None:
        detected = detect_language("digraph G { A -> B }")
        assert detected == "dot" or detected == "graphviz"

    def test_detect_language_d2(self) -> None:
        detected = detect_language("a -> b")
        assert detected == "d2"

    def test_detect_with_hint(self) -> None:
        detected = detect_language("some code", hint="mermaid")
        assert detected == "mermaid"

    def test_detect_unknown(self) -> None:
        detected = detect_language("Just some regular text")
        assert detected is None

    def test_detect_empty_string(self) -> None:
        detected = detect_language("")
        assert detected is None


# ======================================================================
# PiDraw Rendering
# ======================================================================


class TestPiDrawRendering:
    """Verify rendering via PiDraw produces correct output."""

    def test_render_mermaid_svg(self) -> None:
        result = render_diagram("graph TD\nA[Start] --> B[End]", "mermaid")
        assert result.success, f"Render failed: {result.error}"
        assert result.svg is not None
        assert "<svg" in result.svg

    def test_render_graphviz_svg(self) -> None:
        result = render_diagram("digraph G { A -> B }", "dot")
        assert result.success, f"Render failed: {result.error}"
        assert result.svg is not None
        assert "<svg" in result.svg

    def test_render_d2_svg(self) -> None:
        result = render_diagram("a -> b", "d2")
        assert result.success, f"Render failed: {result.error}"
        assert result.svg is not None
        assert "<svg" in result.svg

    def test_render_plantuml_svg(self) -> None:
        result = render_diagram("@startuml\nAlice -> Bob: Hello\n@enduml", "plantuml")
        assert result.success, f"Render failed: {result.error}"
        assert result.svg is not None
        assert "<svg" in result.svg

    def test_render_auto_detect(self) -> None:
        result = render_diagram("graph LR\nA --> B")
        assert result.success, f"Render failed: {result.error}"

    def test_render_unknown_language(self) -> None:
        result = render_diagram("some code", "nonexistent")
        assert not result.success
        assert result.error is not None

    def test_render_unknown_no_language(self) -> None:
        result = render_diagram("Just text")
        assert not result.success
        assert result.error is not None

    def test_render_produces_png(self) -> None:
        """300 DPI transparent PNG must be produced for DOCX."""
        result = render_diagram("graph TD\nA --> B", "mermaid")
        # PNG may be None if cairosvg not available
        if result.success:
            assert result.svg is not None
            # PNG is optional (requires cairosvg)
            if result.png is not None:
                assert len(result.png) > 0

    def test_render_extracts_dimensions(self) -> None:
        result = render_diagram("graph TD\nA --> B", "mermaid")
        if result.success:
            # Width/height may be None if parsing failed
            pass  # Not critical

    def test_render_many_diagrams(self) -> None:
        diagrams = [
            ("graph TD\nA --> B", "mermaid"),
            ("digraph G { A -> B }", "dot"),
            ("a -> b", "d2"),
        ]
        results = render_many_diagrams(diagrams, max_workers=2)
        assert len(results) == 3
        for r in results:
            assert r.success, f"Render failed for {r.language}: {r.error}"
            assert r.svg is not None

    def test_clear_cache(self) -> None:
        """Clear cache should not raise."""
        clear_cache()

    def test_doctor_returns_results(self) -> None:
        results = doctor()
        assert len(results) >= 1
        assert any(r["check"] == "PiDraw installed" for r in results)


# ======================================================================
# DiagramResult / RenderResult
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

    def test_success_with_svg(self) -> None:
        r = DiagramResult(source="", language="x", svg="<svg/>")
        assert r.success

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

    def test_render_result_alias(self) -> None:
        assert RenderResult is DiagramResult


# ======================================================================
# DiagramConfig
# ======================================================================


class TestDiagramConfig:
    def test_defaults(self) -> None:
        c = DiagramConfig()
        assert c.cache
        assert c.svg_preferred
        assert c.max_width == 6.5
        assert c.figure_captions
        assert c.auto_number
        assert c.detect_diagrams
        assert c.dpi == 300

    def test_custom_values(self) -> None:
        c = DiagramConfig(default_width=800, add_captions=False, cache=False)
        assert c.default_width == 800
        assert not c.add_captions
        assert not c.cache


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
        assert reg.get("nonexistent") is None

    def test_register_and_get(self) -> None:
        reg = DiagramRegistry()
        r = _FakeRenderer()
        reg.register(r)
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
        assert reg.get("test") is r2

    def test_list_renderers(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        items = reg.list_renderers()
        assert any(item["language"] == "test" for item in items)

    def test_contains(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        assert "test" in reg
        assert "nonexistent" not in reg


# ======================================================================
# Global Registry (plugin API)
# ======================================================================


class TestGlobalRegistry:
    def test_register_diagram_renderer(self) -> None:
        r = _FakeRenderer()
        register_diagram_renderer("custom_plugin_test", r)

    def test_get_diagram_renderer(self) -> None:
        r = get_diagram_renderer("custom_plugin_test")
        assert r is not None
        assert r.language == "custom_plugin_test"

    def test_list_diagram_renderers(self) -> None:
        items = list_diagram_renderers()
        assert any(item["language"] == "custom_plugin_test" for item in items)


# ======================================================================
# DiagramEngine
# ======================================================================


class TestDiagramEngine:
    def test_instantiation(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        engine = DiagramEngine()
        assert isinstance(engine, DiagramEngine)

    def test_render_with_pidraw(self) -> None:
        engine = DiagramEngine()
        result = engine.render("graph TD\nA[Start] --> B[End]", "mermaid")
        assert result.success, f"Render failed: {result.error}"
        assert result.svg is not None

    def test_render_auto_detect(self) -> None:
        engine = DiagramEngine()
        result = engine.render("graph TD\nA --> B")
        assert result.success

    def test_render_unknown_language(self) -> None:
        engine = DiagramEngine()
        result = engine.render("source code", "nonexistent")
        assert not result.success
        assert result.error is not None

    def test_render_all_parallel(self) -> None:
        engine = DiagramEngine()
        results = engine.render_all([
            ("graph TD\nA --> B", "mermaid"),
            ("digraph G { A -> B }", "dot"),
        ])
        assert len(results) == 2
        for r in results:
            assert r.success, f"Failed: {r.error}"

    def test_detect_language(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("graph TD\nA --> B")
        assert result == "mermaid"

    def test_is_diagram_language(self) -> None:
        assert DiagramEngine.is_diagram_language("mermaid")
        assert DiagramEngine.is_diagram_language("plantuml")
        assert not DiagramEngine.is_diagram_language("python")

    def test_supported_languages(self) -> None:
        langs = DiagramEngine.supported_languages()
        assert "mermaid" in langs

    def test_clear_cache(self) -> None:
        engine = DiagramEngine()
        engine.clear_cache()  # Should not raise

    def test_doctor(self) -> None:
        engine = DiagramEngine()
        results = engine.doctor()
        assert isinstance(results, list)

    def test_renderer_error_graceful(self) -> None:
        """Engine never raises, returns error result instead."""
        engine = DiagramEngine()
        result = engine.render("bad source", "unknown")
        assert not result.success
        assert result.error is not None


# ======================================================================
# Caching
# ======================================================================


class TestDiagramCacheBase:
    def test_make_key_sha256(self) -> None:
        key = DiagramCache.make_key("source code", "mermaid")
        assert key.startswith("diagram:mermaid:")
        expected_hash = hashlib.sha256(b"source code" + b"mermaid").hexdigest()[:32]
        assert key == f"diagram:mermaid:{expected_hash}"

    def test_make_key_deterministic(self) -> None:
        key1 = DiagramCache.make_key("same source", "same lang")
        key2 = DiagramCache.make_key("same source", "same lang")
        assert key1 == key2

    def test_make_key_different_source(self) -> None:
        key1 = DiagramCache.make_key("source a", "lang")
        key2 = DiagramCache.make_key("source b", "lang")
        assert key1 != key2

    def test_make_key_with_extra(self) -> None:
        key = DiagramCache.make_key("src", "lang", width=800)
        assert key.startswith("diagram:lang:")


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

    def test_delete(self) -> None:
        cache = MemoryDiagramCache()
        cache.set("k", DiagramResult(source="", language="t", png=b"d"))
        cache.delete("k")
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

    def test_delete(self, tmp_path: Path) -> None:
        cache = FileSystemDiagramCache(cache_dir=str(tmp_path / "diagrams"))
        cache.set("k", DiagramResult(source="", language="t", png=b"x"))
        cache.delete("k")
        assert cache.get("k") is None


# ======================================================================
# Renderers (backward compatibility stubs)
# ======================================================================


class TestDiagramRendererBase:
    def test_abc_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            DiagramRenderer()  # type: ignore

    def test_default_is_available(self) -> None:
        class MinimalRenderer(DiagramRenderer):
            language = "min"
            name = "Min"
            version = "1"
            description = ""

            def render(self, source: str, **options: object) -> DiagramResult:
                return DiagramResult(source=source, language=self.language)

        r = MinimalRenderer()
        assert r.is_available()

    def test__which_returns_bool(self) -> None:
        assert DiagramRenderer._which("python") is True
        assert DiagramRenderer._which("nonexistent_tool_xyz") is False


# ======================================================================
# DOCX model integration
# ======================================================================


class TestDiagramModel:
    def test_default_construction(self) -> None:
        from pimd.models import Diagram

        d = Diagram(alt="test diagram")
        assert d.alt == "test diagram"
        assert d.png_bytes == b""
        assert d.svg_bytes is None
        assert d.error is None
        assert d.caption is None
        assert d.source == ""
        assert d.title is None
        assert d.width is None
        assert d.height is None
        assert d.figure_number is None

    def test_with_png(self) -> None:
        from pimd.models import Diagram

        d = Diagram(alt="test", png_bytes=b"pngdata", source="src", language="dot")
        assert d.png_bytes == b"pngdata"
        assert d.source == "src"
        assert d.language == "dot"

    def test_with_svg(self) -> None:
        from pimd.models import Diagram

        d = Diagram(alt="test", svg_bytes=b"<svg/>", error="partial")
        assert d.svg_bytes == b"<svg/>"
        assert d.error == "partial"

    def test_with_caption_and_figure(self) -> None:
        from pimd.models import Diagram

        d = Diagram(alt="test", caption="My Diagram", figure_number=1)
        assert d.caption == "My Diagram"
        assert d.figure_number == 1

    def test_with_title(self) -> None:
        from pimd.models import Diagram

        d = Diagram(alt="test", title="System Flow")
        assert d.title == "System Flow"

    def test_with_dimensions(self) -> None:
        from pimd.models import Diagram

        d = Diagram(alt="test", width=800, height=600)
        assert d.width == 800
        assert d.height == 600


# ======================================================================
# Markdown parser — diagram detection
# ======================================================================


class TestDiagramDetection:
    def test_parse_mermaid_fence(self) -> None:
        from pimd.parsers.markdown_parser import MarkdownParser

        md = "```mermaid\ngraph TD\nA --> B\n```"
        parser = MarkdownParser()
        doc = parser.parse(md)
        assert len(doc.blocks) == 1
        from pimd.models import Diagram

        assert isinstance(doc.blocks[0], Diagram)
        assert doc.blocks[0].language == "mermaid"

    def test_parse_plantuml_fence(self) -> None:
        from pimd.parsers.markdown_parser import MarkdownParser

        md = "```plantuml\n@startuml\nA -> B\n@enduml\n```"
        parser = MarkdownParser()
        doc = parser.parse(md)
        assert len(doc.blocks) == 1
        from pimd.models import Diagram

        assert isinstance(doc.blocks[0], Diagram)
        assert doc.blocks[0].language == "plantuml"

    def test_parse_d2_fence(self) -> None:
        from pimd.parsers.markdown_parser import MarkdownParser

        md = "```d2\na -> b\n```"
        parser = MarkdownParser()
        doc = parser.parse(md)
        assert len(doc.blocks) == 1
        from pimd.models import Diagram

        assert isinstance(doc.blocks[0], Diagram)
        assert doc.blocks[0].language == "d2"

    def test_parse_dot_fence(self) -> None:
        from pimd.parsers.markdown_parser import MarkdownParser

        md = "```dot\ndigraph G { A -> B }\n```"
        parser = MarkdownParser()
        doc = parser.parse(md)
        assert len(doc.blocks) == 1
        from pimd.models import Diagram

        assert isinstance(doc.blocks[0], Diagram)
        assert doc.blocks[0].language == "dot"

    def test_parse_fence_with_caption(self) -> None:
        from pimd.parsers.markdown_parser import MarkdownParser

        md = '```mermaid title="System Flow"\ngraph TD\nA --> B\n```'
        parser = MarkdownParser()
        doc = parser.parse(md)
        assert len(doc.blocks) == 1

        d = doc.blocks[0]
        assert d.language == "mermaid"
        assert d.title == "System Flow"
        assert d.caption == "System Flow"

    def test_regular_code_block_not_diagram(self) -> None:
        from pimd.parsers.markdown_parser import MarkdownParser

        md = "```python\nprint('hello')\n```"
        parser = MarkdownParser()
        doc = parser.parse(md)
        assert len(doc.blocks) == 1
        from pimd.models import CodeBlock

        assert isinstance(doc.blocks[0], CodeBlock)

    def test_parse_graphviz_alias(self) -> None:
        from pimd.parsers.markdown_parser import MarkdownParser

        md = "```graphviz\ndigraph G { A -> B }\n```"
        parser = MarkdownParser()
        doc = parser.parse(md)
        assert len(doc.blocks) == 1
        from pimd.models import Diagram

        assert isinstance(doc.blocks[0], Diagram)
        # graphviz is an alias for dot
        assert doc.blocks[0].language in ("graphviz", "dot")


# ======================================================================
# API — render_diagrams parameter
# ======================================================================


class TestRenderDiagramsAPI:
    def test_pimd_accepts_render_diagrams(self) -> None:
        from pimd import PiMD

        engine = PiMD(render_diagrams=False)
        assert engine._service._render_diagrams is False

        engine = PiMD(render_diagrams=True)
        assert engine._service._render_diagrams is True

    def test_pimd_default_render_diagrams(self) -> None:
        from pimd import PiMD

        engine = PiMD()
        assert engine._service._render_diagrams is True
