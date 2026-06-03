"""Benchmark full Markdown to DOCX conversion speed."""

from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import math
import os
import tempfile
from typing import Any

from benchmarks.conftest import format_benchmark_results, generate_sample_markdown, mbps, suppress_stdout, timer

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from pimd.converters.markdown import MarkdownConverter

    HAS_PIMD = True
except ImportError:
    MarkdownConverter = None  # type: ignore
    HAS_PIMD = False

SIZES: list[tuple[str, int]] = [
    ("1 KB", 1024),
    ("10 KB", 10 * 1024),
    ("100 KB", 100 * 1024),
]


def get_memory_mb() -> float:
    """Return current process RSS memory in MB, or NaN if psutil is missing."""
    if not HAS_PSUTIL:
        return math.nan
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def bench_conversion(size_bytes: int) -> dict[str, Any]:
    """Run a full md->docx conversion and return timing / memory results."""
    text = generate_sample_markdown(size_bytes)
    converter = MarkdownConverter()

    mem_before = get_memory_mb()

    with timer() as t_total:
        with suppress_stdout():
            # Parse
            with timer() as t_parse:
                doc = converter._parser.parse(text)
            parse_time = t_parse[0]

            # Save to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                output_path = tmp.name

            # Render
            with timer() as t_render:
                converter._process_diagrams(doc)
                converter._process_equations(doc)
                converter._collect_statistics(doc)
                converter._renderer.render(doc, output_path)

            render_time = t_render[0]

    total_time = t_total[0]
    mem_after = get_memory_mb()
    mem_delta = round(mem_after - mem_before, 2) if not math.isnan(mem_before) and not math.isnan(mem_after) else math.nan

    # Clean up
    try:
        os.unlink(output_path)
    except OSError:
        pass

    stats = converter.get_statistics()
    text_bytes = len(text.encode("utf-8"))

    return {
        "size": f"{size_bytes / 1024:.0f} KB" if size_bytes < 1024 * 1024 else f"{size_bytes / 1024 / 1024:.1f} MB",
        "parse_s": round(parse_time, 4),
        "render_s": round(render_time, 4),
        "total_s": round(total_time, 4),
        "throughput_mbps": round(mbps(text_bytes, total_time), 2),
        "mem_delta_mb": mem_delta,
        "word_count": stats.word_count,
    }


def run() -> list[dict[str, Any]]:
    """Run all conversion benchmarks and print results."""
    if not HAS_PIMD:
        print("Skipping bench_conversion — pimd not available")
        return []

    print("=" * 60)
    print("  Conversion Benchmark (md -> docx)")
    print("=" * 60)

    results: list[dict[str, Any]] = []
    for label, size_bytes in SIZES:
        row = bench_conversion(size_bytes)
        results.append(row)
        mem_str = f"  mem:{row['mem_delta_mb']:.1f}MB" if not math.isnan(row['mem_delta_mb']) else ""
        print(f"  {label:>8s} … {row['total_s']:.4f}s  {row['throughput_mbps']:.2f} MB/s{mem_str}")

    keys = ["size", "parse_s", "render_s", "total_s", "throughput_mbps"]
    if HAS_PSUTIL:
        keys.append("mem_delta_mb")
    keys.append("word_count")

    print()
    table = format_benchmark_results(results, key_order=keys)
    print(table)
    print()

    return results


if __name__ == "__main__":
    run()
