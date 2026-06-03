"""Benchmark Markdown parsing speed for various input sizes."""

from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from typing import Any

from benchmarks.conftest import format_benchmark_results, generate_sample_markdown, mbps, timer

try:
    from pimd.parsers.markdown_parser import MarkdownParser

    HAS_PIMD = True
except ImportError:
    MarkdownParser = None  # type: ignore
    HAS_PIMD = False

SIZES: list[tuple[str, int]] = [
    ("1 KB", 1024),
    ("10 KB", 10 * 1024),
    ("100 KB", 100 * 1024),
    ("1 MB", 1024 * 1024),
]


def bench_parse(size_bytes: int) -> dict[str, Any]:
    """Parse a single sample and return timing results."""
    text = generate_sample_markdown(size_bytes)
    parser = MarkdownParser()

    with timer() as t:
        doc = parser.parse(text)

    elapsed = t[0]
    doc_len = len(doc)
    throughput = mbps(len(text.encode("utf-8")), elapsed)
    return {
        "size": f"{size_bytes / 1024:.0f} KB" if size_bytes < 1024 * 1024 else f"{size_bytes / 1024 / 1024:.1f} MB",
        "bytes": len(text.encode("utf-8")),
        "time_s": round(elapsed, 4),
        "blocks": doc_len,
        "throughput_mbps": round(throughput, 2),
    }


def run() -> list[dict[str, Any]]:
    """Run all parsing benchmarks and print results."""
    if not HAS_PIMD:
        print("Skipping bench_parsing — pimd not available")
        return []

    print("=" * 60)
    print("  Parsing Benchmark")
    print("=" * 60)

    results: list[dict[str, Any]] = []
    for label, size_bytes in SIZES:
        row = bench_parse(size_bytes)
        results.append(row)
        print(f"  {label:>8s} … {row['time_s']:.4f}s  {row['throughput_mbps']:.2f} MB/s")

    table = format_benchmark_results(
        results,
        key_order=["size", "time_s", "throughput_mbps", "blocks"],
    )
    print()
    print(table)
    print()

    return results


if __name__ == "__main__":
    run()
