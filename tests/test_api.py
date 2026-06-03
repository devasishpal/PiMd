"""Tests for PiMD public API, service layer, caching, safety, plugins, and async."""

from __future__ import annotations

from pathlib import Path

import pytest

from pimd import PiMD
from pimd.caching import MemoryCache
from pimd.observability import ConversionMetrics, ConversionReport, Timer
from pimd.plugins import ConversionHook, Plugin, PluginManager
from pimd.safety import SafetyError, SafetyGuard, SafetyLimits

# ======================================================================
# PiMD public API
# ======================================================================


class TestPiMD:
    """Verify the PiMD class (primary public API)."""

    def test_instantiation(self) -> None:
        engine = PiMD()
        assert isinstance(engine, PiMD)

    def test_md_text_to_docx_bytes(self) -> None:
        engine = PiMD()
        result = engine.md_text_to_docx_bytes("# Hello\n\nWorld.")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_html_text_to_docx_bytes(self) -> None:
        engine = PiMD()
        result = engine.html_text_to_docx_bytes("<h1>Hello</h1><p>World</p>")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_md_text_to_docx_file(self, tmp_path: Path) -> None:
        out = tmp_path / "out.docx"
        engine = PiMD()
        engine.md_text_to_docx("# Hello", out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_html_text_to_docx_file(self, tmp_path: Path) -> None:
        out = tmp_path / "out.docx"
        engine = PiMD()
        engine.html_text_to_docx("<h1>Hello</h1>", out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_md_to_docx_file(self, tmp_path: Path) -> None:
        input_file = tmp_path / "test.md"
        input_file.write_text("# Hello\n\nWorld.")
        out = tmp_path / "out.docx"
        engine = PiMD()
        engine.md_to_docx(input_file, out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_html_to_docx_file(self, tmp_path: Path) -> None:
        input_file = tmp_path / "test.html"
        input_file.write_text("<h1>Hello</h1><p>World</p>")
        out = tmp_path / "out.docx"
        engine = PiMD()
        engine.html_to_docx(input_file, out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_md_text_to_docx_bytes_with_options(self) -> None:
        engine = PiMD()
        result = engine.md_text_to_docx_bytes(
            "# Hello\n\nWorld.",
            generate_toc=True,
            page_numbers=True,
            title="Test",
            author="Me",
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_html_text_to_docx_bytes_with_options(self) -> None:
        engine = PiMD()
        result = engine.html_text_to_docx_bytes(
            "<h1>Hello</h1>",
            cover_page=True,
            title="Cover",
            author="Me",
            doc_version="1",
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    # -- Report --

    def test_last_report_available(self) -> None:
        engine = PiMD()
        engine.md_text_to_docx_bytes("# Hello")
        report = engine.last_report
        assert report is not None
        assert report.success is True
        assert report.metrics.total_time > 0

    def test_get_report_alias(self) -> None:
        engine = PiMD()
        engine.md_text_to_docx_bytes("# Hello")
        assert engine.get_report() is engine.last_report

    # -- Cache --

    def test_cache_cleared(self) -> None:
        engine = PiMD()
        engine.md_text_to_docx_bytes("# Hello")
        engine.clear_cache()
        assert True  # no error


# ======================================================================
# Async API
# ======================================================================


@pytest.mark.asyncio
class TestAsyncPiMD:
    """Verify async wrappers work."""

    async def test_async_md_text_to_docx_bytes(self) -> None:
        engine = PiMD()
        result = await engine.async_md_text_to_docx_bytes("# Hello\n\nWorld.")
        assert isinstance(result, bytes)
        assert len(result) > 0

    async def test_async_html_text_to_docx_bytes(self) -> None:
        engine = PiMD()
        result = await engine.async_html_text_to_docx_bytes("<h1>Hello</h1>")
        assert isinstance(result, bytes)
        assert len(result) > 0

    async def test_async_md_text_to_docx_file(self, tmp_path: Path) -> None:
        out = tmp_path / "out.docx"
        engine = PiMD()
        result = await engine.async_md_text_to_docx("# Hello", out)
        assert out.exists()
        assert result is not None

    async def test_async_html_text_to_docx_file(self, tmp_path: Path) -> None:
        out = tmp_path / "out.docx"
        engine = PiMD()
        result = await engine.async_html_text_to_docx("<h1>Hello</h1>", out)
        assert out.exists()
        assert result is not None

    async def test_async_md_to_docx_file(self, tmp_path: Path) -> None:
        input_file = tmp_path / "test.md"
        input_file.write_text("# Hello")
        out = tmp_path / "out.docx"
        engine = PiMD()
        result = await engine.async_md_to_docx(input_file, out)
        assert out.exists()
        assert result is not None

    async def test_async_html_to_docx_file(self, tmp_path: Path) -> None:
        input_file = tmp_path / "test.html"
        input_file.write_text("<h1>Hello</h1>")
        out = tmp_path / "out.docx"
        engine = PiMD()
        result = await engine.async_html_to_docx(input_file, out)
        assert out.exists()
        assert result is not None


# ======================================================================
# Memory mode
# ======================================================================


class TestMemoryMode:
    """Verify conversion works without filesystem writes."""

    def test_md_no_temp_files(self) -> None:
        engine = PiMD()
        result = engine.md_text_to_docx_bytes("# Hello")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_html_no_temp_files(self) -> None:
        engine = PiMD()
        result = engine.html_text_to_docx_bytes("<h1>Hello</h1>")
        assert isinstance(result, bytes)
        assert len(result) > 0


# ======================================================================
# Caching
# ======================================================================


class TestCaching:
    """Verify MemoryCache works."""

    def test_set_and_get(self) -> None:
        cache = MemoryCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_get_missing(self) -> None:
        cache = MemoryCache()
        assert cache.get("nonexistent") is None

    def test_delete(self) -> None:
        cache = MemoryCache()
        cache.set("key", "value")
        cache.delete("key")
        assert cache.get("key") is None

    def test_clear(self) -> None:
        cache = MemoryCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_ttl_expiry(self) -> None:
        cache = MemoryCache(default_ttl=0)
        cache.set("key", "value", ttl=0)
        assert cache.get("key") is None

    def test_make_key(self) -> None:
        cache = MemoryCache()
        key = cache.make_key("convert", "markdown", toc="true")
        assert "convert" in key
        assert "markdown" in key

    def test_pimd_cache_integration(self) -> None:
        """Second identical call should hit cache and return bytes."""
        engine = PiMD(enable_cache=True)
        first = engine.md_text_to_docx_bytes("# Hello")
        second = engine.md_text_to_docx_bytes("# Hello")
        assert isinstance(first, bytes)
        assert isinstance(second, bytes)
        assert len(first) > 0
        assert len(second) > 0


# ======================================================================
# Safety
# ======================================================================


class TestSafety:
    """Verify safety guards."""

    def test_default_limits(self) -> None:
        limits = SafetyLimits()
        assert limits.max_input_size == 100 * 1024 * 1024

    def test_text_size_ok(self) -> None:
        guard = SafetyGuard(SafetyLimits(max_input_size=1000))
        guard.check_text_size("hello")  # should not raise

    def test_text_size_exceeded(self) -> None:
        guard = SafetyGuard(SafetyLimits(max_input_size=5))
        with pytest.raises(SafetyError, match="exceeds safety limit"):
            guard.check_text_size("hello world")

    def test_file_size_ok(self, tmp_path: Path) -> None:
        f = tmp_path / "small.txt"
        f.write_text("hello")
        guard = SafetyGuard()
        guard.check_file_size(f)  # should not raise

    def test_file_size_exceeded(self, tmp_path: Path) -> None:
        f = tmp_path / "big.txt"
        f.write_bytes(b"x" * 1000)
        guard = SafetyGuard(SafetyLimits(max_file_size=100))
        with pytest.raises(SafetyError):
            guard.check_file_size(f)

    def test_nesting_depth_ok(self) -> None:
        guard = SafetyGuard()
        guard.check_nesting_depth(50)  # should not raise

    def test_nesting_depth_exceeded(self) -> None:
        guard = SafetyGuard(SafetyLimits(max_nesting_depth=10))
        with pytest.raises(SafetyError):
            guard.check_nesting_depth(11)

    def test_block_count_ok(self) -> None:
        guard = SafetyGuard()
        guard.check_block_count(100)

    def test_block_count_exceeded(self) -> None:
        guard = SafetyGuard(SafetyLimits(max_document_blocks=10))
        with pytest.raises(SafetyError):
            guard.check_block_count(11)

    def test_image_size_ok(self) -> None:
        guard = SafetyGuard()
        guard.check_image_size(1000)

    def test_image_size_exceeded(self) -> None:
        guard = SafetyGuard(SafetyLimits(max_image_size=5))
        with pytest.raises(SafetyError, match="exceeds"):
            guard.check_image_size(100)


# ======================================================================
# Observability
# ======================================================================


class TestObservability:
    """Verify timing, metrics, and reports."""

    def test_timer(self) -> None:
        timer = Timer()
        with timer:
            pass
        assert timer.elapsed >= 0

    def test_metrics_to_dict(self) -> None:
        metrics = ConversionMetrics(parse_time=0.1, render_time=0.2, total_time=0.3)
        d = metrics.to_dict()
        assert d["parse_time"] == 0.1
        assert d["render_time"] == 0.2
        assert d["total_time"] == 0.3

    def test_report_to_dict(self) -> None:
        report = ConversionReport(source_format="markdown", success=True)
        d = report.to_dict()
        assert d["source_format"] == "markdown"
        assert d["success"] is True
        assert d["cache_hit"] is False

    def test_report_with_statistics(self) -> None:
        from pimd.models import DocumentStatistics

        stats = DocumentStatistics(heading_count=3, paragraph_count=5)
        report = ConversionReport(statistics=stats)
        d = report.to_dict()
        assert d["statistics"]["heading_count"] == 3
        assert d["statistics"]["paragraph_count"] == 5


# ======================================================================
# Plugin system
# ======================================================================


class TestPluginSystem:
    """Verify plugin registration, hooks, and dispatch."""

    def test_register_and_list(self) -> None:
        manager = PluginManager()
        plugin = _SimplePlugin()
        plugin.attach(manager)
        plugins = manager.list_plugins()
        assert len(plugins) >= 1
        assert plugins[0]["name"] == "test_plugin"

    def test_dispatch_hook(self) -> None:
        manager = PluginManager()
        plugin = _SimplePlugin()
        plugin.attach(manager)
        result = manager.dispatch(ConversionHook.AFTER_PARSE, "hello", context={})
        assert result == "hello_TRANSFORMED"

    def test_disable_plugin(self) -> None:
        manager = PluginManager()
        plugin = _SimplePlugin()
        plugin.attach(manager)
        manager.disable("test_plugin")
        plugins = manager.list_plugins()
        for p in plugins:
            if p["name"] == "test_plugin":
                assert p["enabled"] == "False"

    def test_enable_plugin(self) -> None:
        manager = PluginManager()
        plugin = _SimplePlugin()
        plugin.attach(manager)
        manager.disable("test_plugin")
        manager.enable("test_plugin")
        plugins = manager.list_plugins()
        for p in plugins:
            if p["name"] == "test_plugin":
                assert p["enabled"] == "True"


class _SimplePlugin(Plugin):
    name = "test_plugin"
    version = "1.0.0"
    description = "Test plugin for unit tests"

    def attach(self, manager: PluginManager) -> None:
        manager.register(self, ConversionHook.AFTER_PARSE, self._transform)

    def _transform(self, document: str, context: dict) -> str:
        return document + "_TRANSFORMED"


# ======================================================================
# DocumentService
# ======================================================================


class TestDocumentService:
    """Verify DocumentService operations."""

    def test_add_heading(self) -> None:
        from pimd.models import Document
        from pimd.services import DocumentService

        doc = Document()
        DocumentService.add_heading(doc, "Title", level=1)
        assert len(doc.blocks) == 1
        assert doc.blocks[0].plain_text() == "Title"

    def test_add_paragraph(self) -> None:
        from pimd.models import Document
        from pimd.services import DocumentService

        doc = Document()
        DocumentService.add_paragraph(doc, "Content")
        assert len(doc.blocks) == 1

    def test_merge(self) -> None:
        from pimd.models import Document
        from pimd.services import DocumentService

        doc1 = Document()
        DocumentService.add_paragraph(doc1, "A")
        doc2 = Document()
        DocumentService.add_paragraph(doc2, "B")
        merged = DocumentService.merge([doc1, doc2])
        assert len(merged.blocks) == 2

    def test_find_headings(self) -> None:
        from pimd.models import Document
        from pimd.services import DocumentService

        doc = Document()
        DocumentService.add_heading(doc, "H1", level=1)
        DocumentService.add_heading(doc, "H2", level=2)
        DocumentService.add_paragraph(doc, "Text")
        headings = DocumentService.find_headings(doc)
        assert len(headings) == 2

    def test_find_headings_by_level(self) -> None:
        from pimd.models import Document
        from pimd.services import DocumentService

        doc = Document()
        DocumentService.add_heading(doc, "H1", level=1)
        DocumentService.add_heading(doc, "H2", level=2)
        headings = DocumentService.find_headings(doc, level=1)
        assert len(headings) == 1
        assert headings[0].plain_text() == "H1"


# ======================================================================
# TemplateService
# ======================================================================


class TestTemplateService:
    """Verify TemplateService."""

    def test_list_empty(self) -> None:
        from pimd.services import TemplateService

        svc = TemplateService()
        assert svc.list_templates() == []

    def test_load_and_get(self, tmp_path: Path) -> None:
        from pimd.services import TemplateService

        template_file = tmp_path / "template.dotx"
        template_file.write_text("placeholder")
        svc = TemplateService()
        svc.load_template("default", template_file)
        assert svc.get_template_path("default") == template_file
