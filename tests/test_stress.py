"""Stress tests for PiMD — large files, parallel execution, edge cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

# ======================================================================
# Large file stress tests
# ======================================================================


def _generate_large_markdown(sections: int, words_per_section: int = 50) -> str:
    lines: list[str] = []
    for i in range(sections):
        lines.append(f"## Section {i}")
        lines.append("")
        words = " ".join(f"word{j}" for j in range(words_per_section))
        lines.append(words)
        lines.append("")
        lines.append("A paragraph with **bold** and *italic* and `code`.")
        lines.append("")
    return "\n".join(lines)


@pytest.mark.slow
def test_100k_markdown() -> None:
    """Process a 100K+ line markdown document."""
    from pimd.parsers.markdown_parser import MarkdownParser

    content = _generate_large_markdown(10_000, 5)
    parser = MarkdownParser()
    doc = parser.parse(content)
    assert len(doc.blocks) > 10_000


@pytest.mark.slow
def test_large_document_statistics(tmp_path: Path) -> None:
    """Verify statistics collection on large documents."""
    content = _generate_large_markdown(500, 20)
    from pimd.converters.markdown import MarkdownConverter

    output = tmp_path / "large.docx"
    MarkdownConverter().convert_text(content, output)
    assert output.exists()
    assert output.stat().st_size > 0


# ======================================================================
# Parallel execution stress tests
# ======================================================================


def test_parallel_equation_rendering() -> None:
    """Render many equations in parallel."""
    from pimd.equations import EquationEngine
    from pimd.parallel import parallel_batch

    engine = EquationEngine()

    def render_eq(latex: str) -> Any:
        return engine.render(latex)

    equations = [f"x^{{{i}}} + y^{{{i}}}" for i in range(50)]
    result = parallel_batch(render_eq, equations, max_workers=4)
    assert result.total == 50
    assert result.succeeded >= 48


def test_parallel_conversion(tmp_path: Path) -> None:
    """Convert multiple documents in parallel."""
    from pimd.api import PiMD
    from pimd.parallel import parallel_batch

    engine = PiMD()

    def convert(text: str) -> Any:
        return engine.md_text_to_docx_bytes(text)

    docs = [f"# Doc {i}\n\nHello world {i}\n" for i in range(20)]
    result = parallel_batch(convert, docs, max_workers=4)
    assert result.total == 20
    assert result.succeeded == 20


# ======================================================================
# Edge case tests
# ======================================================================


def test_empty_document(tmp_path: Path) -> None:
    from pimd.converters.markdown import MarkdownConverter
    converter = MarkdownConverter()
    output = tmp_path / "empty.docx"
    converter.convert_text("", output)
    assert output.exists()


def test_whitespace_only(tmp_path: Path) -> None:
    from pimd.converters.markdown import MarkdownConverter
    converter = MarkdownConverter()
    output = tmp_path / "ws.docx"
    converter.convert_text("   \n\n  \n  ", output)
    assert output.exists()


def test_very_long_line(tmp_path: Path) -> None:
    """A single line with 100K characters."""
    from pimd.converters.markdown import MarkdownConverter
    converter = MarkdownConverter()
    output = tmp_path / "long.docx"
    line = "x" * 100_000
    converter.convert_text(line, output)
    assert output.exists()


def test_deeply_nested_lists() -> None:
    """Deeply nested lists should not cause recursion errors."""
    from pimd.parsers.markdown_parser import MarkdownParser
    parser = MarkdownParser()
    lines = []
    for i in range(1, 50):
        lines.append("  " * i + f"- level {i}")
    try:
        doc = parser.parse("\n".join(lines))
        assert doc is not None
    except RecursionError:
        pytest.fail("Deep nesting caused RecursionError")


def test_many_equations(tmp_path: Path) -> None:
    """Document with 100+ equations."""
    from pimd.converters.markdown import MarkdownConverter
    converter = MarkdownConverter()
    eqs = "\n\n".join(f"$$ x^{{{i}}} + y^{{{i}}} = z^{{{i}}} $$" for i in range(100))
    text = f"# Equations\n\n{eqs}\n"
    output = tmp_path / "eq.docx"
    converter.convert_text(text, output)
    assert output.exists()


# ======================================================================
# Redis optional tests
# ======================================================================


def test_redis_fallback_graceful() -> None:
    """Redis cache should fail gracefully when no Redis is available."""
    from pimd.caching.redis_cache import RedisCacheBackend
    cache = RedisCacheBackend(url="redis://nonexistent:6379/0")
    assert cache.is_available() is False
    cache.set("test", "value")
    assert cache.get("test") is None
    cache.delete("test")
    cache.clear()


@pytest.mark.skipif("True", reason="Only runs with PIMD_REDIS_URL set")
def test_redis_cache_works() -> None:
    """Redis cache integration test (requires real Redis)."""
    import os

    from pimd.caching.redis_cache import RedisCacheBackend

    url = os.environ.get("PIMD_REDIS_URL")
    if not url:
        pytest.skip("PIMD_REDIS_URL not set")
    cache = RedisCacheBackend(url=url)
    assert cache.is_available()
    cache.set("integ-test", {"hello": "world"})
    val = cache.get("integ-test")
    assert val == {"hello": "world"}
    cache.delete("integ-test")


# ======================================================================
# Pipeline stress tests
# ======================================================================


def test_pipeline_with_many_stages() -> None:
    """Pipeline with many stages should still function."""
    from pimd.pipeline import Pipeline, PipelineContext

    stages = []
    for i in range(20):
        stage = _create_dummy_stage(f"stage_{i}")
        stages.append(stage)

    p = Pipeline("stress")
    for s in stages:
        p.add_stage(s)

    ctx = PipelineContext(source_text="# Hello")
    result, stage_results = p.run(ctx)
    assert len(stage_results) == 20
    assert all(sr.success for sr in stage_results)


def _create_dummy_stage(name: str) -> Any:
    from pimd.pipeline import PipelineContext, PipelineStage, StageType

    class DummyStage(PipelineStage):
        def execute(self, ctx: PipelineContext) -> PipelineContext:
            return ctx
    return DummyStage(name=name, stage_type=StageType.CUSTOM)


# ======================================================================
# Large document merge stress test
# ======================================================================


def test_merge_many_documents(tmp_path: Path) -> None:
    """Merge 100 small markdown files."""
    files = []
    for i in range(100):
        p = tmp_path / f"doc_{i}.md"
        p.write_text(f"# Document {i}\n\nContent {i}\n", encoding="utf-8")
        files.append(p)

    from pimd.merge import DocumentMerger
    merger = DocumentMerger()
    output = tmp_path / "merged.docx"
    merger.merge([str(f) for f in files], str(output))
    assert output.exists()
