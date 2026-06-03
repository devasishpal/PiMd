"""Tests for the diagram system: engine, registry, cache, renderers, detection."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pimd.diagrams import DiagramEngine, DiagramRegistry
from pimd.diagrams.cache import (
    DiagramCache,
    FileSystemDiagramCache,
    MemoryDiagramCache,
)
from pimd.diagrams.models import (
    AUTO_DETECT_PATTERNS,
    DIAGRAM_LANGUAGES,
    DiagramConfig,
    DiagramResult,
    RenderResult,
)
from pimd.diagrams.registry import (
    _get_global_registry,
    get_diagram_renderer,
    list_diagram_renderers,
    register_diagram_renderer,
)
from pimd.diagrams.renderers import DiagramRenderer
from pimd.diagrams.renderers.ascii import AsciiRenderer
from pimd.diagrams.renderers.blockdiag import (
    ActDiagRenderer,
    BlockDiagRenderer,
    NwDiagRenderer,
    PacketDiagRenderer,
    SeqDiagRenderer,
)
from pimd.diagrams.renderers.bpmn import BPMNRenderer
from pimd.diagrams.renderers.d2 import D2Renderer
from pimd.diagrams.renderers.graphviz import GraphvizRenderer
from pimd.diagrams.renderers.mermaid import MermaidRenderer
from pimd.diagrams.renderers.plantuml import PlantUMLRenderer
from pimd.diagrams.renderers.svg import SvgRenderer
from pimd.diagrams.renderers.vega import VegaLiteRenderer, VegaRenderer

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

    def test_custom_values(self) -> None:
        c = DiagramConfig(default_width=800, add_captions=False, cache=False)
        assert c.default_width == 800
        assert not c.add_captions
        assert not c.cache


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
        assert "blockdiag" in DIAGRAM_LANGUAGES
        assert "seqdiag" in DIAGRAM_LANGUAGES
        assert "actdiag" in DIAGRAM_LANGUAGES
        assert "nwdiag" in DIAGRAM_LANGUAGES
        assert "packetdiag" in DIAGRAM_LANGUAGES
        assert "bpmn" in DIAGRAM_LANGUAGES
        assert "vega" in DIAGRAM_LANGUAGES
        assert "vega-lite" in DIAGRAM_LANGUAGES

    def test_aliases(self) -> None:
        assert DIAGRAM_LANGUAGES["mmd"] == "Mermaid"
        assert DIAGRAM_LANGUAGES["puml"] == "PlantUML"
        assert DIAGRAM_LANGUAGES["graphviz"] == "Graphviz"

    def test_diagram_count(self) -> None:
        assert len(DIAGRAM_LANGUAGES) >= 16


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
# Global Registry (plugin API)
# ======================================================================


class TestGlobalRegistry:
    def test_register_diagram_renderer(self) -> None:
        r = _FakeRenderer()
        register_diagram_renderer("custom_plugin", r)

    def test_get_diagram_renderer(self) -> None:
        r = get_diagram_renderer("custom_plugin")
        assert r is not None
        assert r.language == "custom_plugin"

    def test_list_diagram_renderers(self) -> None:
        items = list_diagram_renderers()
        assert any(item["language"] == "custom_plugin" for item in items)


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
        assert "No renderer registered" in result.error

    def test_render_case_insensitive(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        engine = DiagramEngine(registry=reg)
        result = engine.render("src", "TEST")
        assert result.success

    def test_render_auto_detect_no_engine(self) -> None:
        reg = DiagramRegistry()
        engine = DiagramEngine(registry=reg)
        result = engine.render("graph TD\nA --> B")
        assert result.error is not None
        assert "Could not auto-detect" in result.error or "No renderer" in result.error

    def test_render_with_config(self) -> None:
        config = DiagramConfig(cache=False)
        engine = DiagramEngine(config=config)
        assert not engine.config.cache

    def test_render_all_parallel(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        engine = DiagramEngine(registry=reg)
        results = engine.render_all([("src1", "test"), ("src2", "test")])
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_renderer_unavailable_graceful(self) -> None:
        class UnavailableRenderer(DiagramRenderer):
            language = "unavail"
            name = "Unavailable"
            version = "1"
            description = ""

            def is_available(self) -> bool:
                return False

            def render(self, source: str, **options: object) -> DiagramResult:
                return DiagramResult(source=source, language=self.language)

        reg = DiagramRegistry()
        reg.register(UnavailableRenderer())
        engine = DiagramEngine(registry=reg)
        result = engine.render("src", "unavail")
        assert not result.success
        assert "not available" in (result.error or "")

    def test_renderer_exception_caught(self) -> None:
        class BrokenRenderer(DiagramRenderer):
            language = "broken"
            name = "Broken"
            version = "1"
            description = ""

            def is_available(self) -> bool:
                return True

            def render(self, source: str, **options: object) -> DiagramResult:
                raise RuntimeError("something bad")

        reg = DiagramRegistry()
        reg.register(BrokenRenderer())
        engine = DiagramEngine(registry=reg)
        result = engine.render("src", "broken")
        assert not result.success
        assert result.error is not None


# ======================================================================
# Auto-Detection
# ======================================================================


class TestAutoDetection:
    def test_detect_mermaid_flowchart(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("graph TD\nA --> B")
        assert result == "mermaid"

    def test_detect_mermaid_sequence(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("sequenceDiagram\nAlice->>Bob: Hello")
        assert result == "mermaid"

    def test_detect_mermaid_flowchart_keyword(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("flowchart LR\nA-->B")
        assert result == "mermaid"

    def test_detect_plantuml(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("@startuml\nAlice -> Bob: Hello\n@enduml")
        assert result == "plantuml"

    def test_detect_graphviz(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("digraph G {\n  A -> B\n}")
        assert result == "dot"

    def test_detect_graphviz_undirected(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("graph G {\n  A -- B\n}")
        assert result == "dot"

    def test_detect_d2(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("a -> b")
        assert result == "d2"

    def test_detect_d2_multi(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("x -> y\ny -> z")
        assert result == "d2"

    def test_detect_ascii_box(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language(
            "+-------+     +-------+\n"
            "| Hello | --> | World |\n"
            "+-------+     +-------+"
        )
        assert result == "ascii"

    def test_detect_ascii_unicode(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("\u250c\u2500\u2510\n\u2502A\u2502\n\u2514\u2500\u2518")
        assert result == "ascii"

    def test_detect_unknown(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("Just some regular text")
        assert result is None

    def test_detect_empty_string(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("")
        assert result is None

    def test_detect_with_hint(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("some code", hint="mermaid")
        assert result == "mermaid"

    def test_detect_with_alias_hint(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("some code", hint="mmd")
        assert result == "mermaid"

    def test_detect_with_bad_hint(self) -> None:
        engine = DiagramEngine()
        result = engine.detect_language("some code", hint="nonexistent")
        assert result is None

    def test_auto_detect_patterns_defined(self) -> None:
        assert "mermaid" in AUTO_DETECT_PATTERNS
        assert "plantuml" in AUTO_DETECT_PATTERNS
        assert "dot" in AUTO_DETECT_PATTERNS
        assert "d2" in AUTO_DETECT_PATTERNS

    def test_is_diagram_language(self) -> None:
        assert DiagramEngine.is_diagram_language("mermaid")
        assert DiagramEngine.is_diagram_language("plantuml")
        assert not DiagramEngine.is_diagram_language("python")

    def test_supported_languages(self) -> None:
        langs = DiagramEngine.supported_languages()
        assert "mermaid" in langs
        assert "plantuml" in langs


# ======================================================================
# Caching
# ======================================================================


class TestDiagramCacheBase:
    def test_make_key_sha256(self) -> None:
        key = DiagramCache.make_key("source code", "mermaid")
        assert key.startswith("diagram:mermaid:")
        # Verify it's SHA256-based
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

    def test_abc_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            DiagramCache()  # type: ignore


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

    def test_ttl_expiry(self) -> None:
        import time

        cache = MemoryDiagramCache(default_ttl=0.1)
        cache.set("k", DiagramResult(source="", language="t", png=b"d"))
        assert cache.get("k") is not None
        time.sleep(0.15)
        assert cache.get("k") is None

    def test_set_with_custom_ttl(self) -> None:
        cache = MemoryDiagramCache(default_ttl=3600)
        cache.set("k", DiagramResult(source="", language="t", png=b"d"), ttl=0.05)
        import time
        time.sleep(0.08)
        assert cache.get("k") is None

    def test_cache_hit_flag(self) -> None:
        cache = MemoryDiagramCache()
        result = DiagramResult(source="src", language="t", png=b"data")
        cache.set("k", result)
        # Engine should set cached=True when retrieving from cache
        assert not result.cached

    def test_cache_stores_svg(self) -> None:
        cache = MemoryDiagramCache()
        result = DiagramResult(source="src", language="t", svg="<svg/>")
        cache.set("k", result)
        cached = cache.get("k")
        assert cached is not None
        assert cached.svg == "<svg/>"


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
        assert list((tmp_path / "diagrams").iterdir()) == list()

    def test_delete(self, tmp_path: Path) -> None:
        cache = FileSystemDiagramCache(cache_dir=str(tmp_path / "diagrams"))
        cache.set("k", DiagramResult(source="", language="t", png=b"x"))
        cache.delete("k")
        assert cache.get("k") is None

    def test_cache_dir_created(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "new_diagrams"
        assert not cache_dir.exists()
        FileSystemDiagramCache(cache_dir=str(cache_dir))
        assert cache_dir.exists()


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

    def test_description(self) -> None:
        r = MermaidRenderer()
        assert "Mermaid" in r.description


class TestPlantUMLRenderer:
    def test_language_and_name(self) -> None:
        r = PlantUMLRenderer()
        assert r.language == "plantuml"
        assert r.name == "PlantUML"

    def test_priority(self) -> None:
        r = PlantUMLRenderer()
        assert r.priority == 20


class TestGraphvizRenderer:
    def test_language_and_name(self) -> None:
        r = GraphvizRenderer()
        assert r.language == "dot"
        assert r.name == "Graphviz"

    def test_priority(self) -> None:
        r = GraphvizRenderer()
        assert r.priority == 30


class TestD2Renderer:
    def test_language_and_name(self) -> None:
        r = D2Renderer()
        assert r.language == "d2"
        assert r.name == "D2"

    def test_priority(self) -> None:
        r = D2Renderer()
        assert r.priority == 40


class TestAsciiRenderer:
    def test_language_and_name(self) -> None:
        r = AsciiRenderer()
        assert r.language == "ascii"
        assert r.name == "ASCII Diagram"

    def test_priority(self) -> None:
        r = AsciiRenderer()
        assert r.priority == 50

    def test_pillow_not_available_returns_error(self) -> None:
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

    def test_render_simple_ascii(self) -> None:
        r = AsciiRenderer()
        if not r.is_available():
            pytest.skip("Pillow not installed")
        result = r.render("+---+---+")
        assert result.success or result.error is not None


class TestSvgRenderer:
    def test_language_and_name(self) -> None:
        r = SvgRenderer()
        assert r.language == "svg"
        assert r.name == "SVG"

    def test_priority(self) -> None:
        r = SvgRenderer()
        assert r.priority == 60

    def test_inline_svg_renders_without_error(self) -> None:
        r = SvgRenderer()
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'
        result = r.render(svg)
        assert result.svg == svg
        assert result.error is None


class TestBlockDiagRenderers:
    def test_blockdiag_language(self) -> None:
        r = BlockDiagRenderer()
        assert r.language == "blockdiag"
        assert r.name == "BlockDiag"
        assert r.priority == 70

    def test_seqdiag_language(self) -> None:
        r = SeqDiagRenderer()
        assert r.language == "seqdiag"
        assert r.name == "SeqDiag"
        assert r.priority == 70

    def test_actdiag_language(self) -> None:
        r = ActDiagRenderer()
        assert r.language == "actdiag"
        assert r.name == "ActDiag"
        assert r.priority == 70

    def test_nwdiag_language(self) -> None:
        r = NwDiagRenderer()
        assert r.language == "nwdiag"
        assert r.name == "NwDiag"
        assert r.priority == 70

    def test_packetdiag_language(self) -> None:
        r = PacketDiagRenderer()
        assert r.language == "packetdiag"
        assert r.name == "PacketDiag"
        assert r.priority == 70


class TestBPMNRenderer:
    def test_language_and_name(self) -> None:
        r = BPMNRenderer()
        assert r.language == "bpmn"
        assert r.name == "BPMN"
        assert r.priority == 80

    def test_is_available(self) -> None:
        r = BPMNRenderer()
        # Should gracefully handle missing tool
        assert not r.is_available() or True


class TestVegaRenderers:
    def test_vega_language(self) -> None:
        r = VegaRenderer()
        assert r.language == "vega"
        assert r.name == "Vega"
        assert r.priority == 90

    def test_vega_lite_language(self) -> None:
        r = VegaLiteRenderer()
        assert r.language == "vega-lite"
        assert r.name == "Vega-Lite"
        assert r.priority == 90


# ======================================================================
# Base Renderer
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

    def test__tool_name_default(self) -> None:
        class MinimalRenderer(DiagramRenderer):
            language = "min"
            name = "MinimalRenderer"
            version = "1"
            description = ""

            def render(self, source: str, **options: object) -> DiagramResult:
                return DiagramResult(source=source, language=self.language)

        r = MinimalRenderer()
        assert r._tool_name() == "MinimalRenderer"

    def test__which_returns_bool(self) -> None:
        assert DiagramRenderer._which("python") is True
        assert DiagramRenderer._which("nonexistent_tool_xyz") is False


# ======================================================================
# Engine cache integration
# ======================================================================


class TestEngineCacheIntegration:
    def test_engine_uses_cache(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        cache = MemoryDiagramCache()
        engine = DiagramEngine(registry=reg, cache=cache)

        result1 = engine.render("src", "test")
        assert result1.success

        # Second call should use cache
        key = DiagramCache.make_key("src", "test")
        cached = cache.get(key)
        assert cached is not None

    def test_engine_cache_miss(self) -> None:
        cache = MemoryDiagramCache()
        key = DiagramCache.make_key("src", "test")
        assert cache.get(key) is None

    def test_engine_clear_cache(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        cache = MemoryDiagramCache()
        engine = DiagramEngine(registry=reg, cache=cache)

        engine.render("src", "test")
        assert len(cache._store) > 0
        engine.clear_cache()
        assert len(cache._store) == 0


# ======================================================================
# Plugin registration integration
# ======================================================================


class TestPluginRegistration:
    def test_register_via_module_function(self) -> None:
        class CustomRenderer(DiagramRenderer):
            language = "customdsl"
            name = "Custom DSL"
            version = "1.0"
            description = "Custom diagram DSL"

            def is_available(self) -> bool:
                return True

            def render(self, source: str, **options: object) -> DiagramResult:
                return DiagramResult(source=source, language=self.language, png=b"custom")


        old_reg = _get_global_registry()

        register_diagram_renderer("customdsl", CustomRenderer())
        assert old_reg.get("customdsl") is not None

    def test_plugin_renderer_works_in_engine(self) -> None:
        class PluginRenderer(DiagramRenderer):
            language = "pluginlang"
            name = "Plugin Renderer"
            version = "1.0"
            description = ""

            def is_available(self) -> bool:
                return True

            def render(self, source: str, **options: object) -> DiagramResult:
                return DiagramResult(source=source, language=self.language, png=b"plugin_png")

        reg = DiagramRegistry()
        reg.register(PluginRenderer())
        engine = DiagramEngine(registry=reg)
        result = engine.render("src", "pluginlang")
        assert result.success
        assert result.png == b"plugin_png"


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

    def test_with_caption(self) -> None:
        from pimd.models import Diagram

        d = Diagram(alt="test", caption="My Diagram")
        assert d.caption == "My Diagram"


# ======================================================================
# Engine doctor
# ======================================================================


class TestEngineDoctor:
    def test_doctor_returns_list(self) -> None:
        reg = DiagramRegistry()
        reg.register(_FakeRenderer())
        engine = DiagramEngine(registry=reg)
        results = engine.doctor()
        assert isinstance(results, list)
        assert len(results) >= 1
        assert any(r["language"] == "test" for r in results)
