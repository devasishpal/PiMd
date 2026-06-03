"""Memory benchmarks for PiMD conversion pipeline.

Usage:
    python benchmarks/test_memory.py
"""

from __future__ import annotations

import tracemalloc
from pathlib import Path

HERE = Path(__file__).parent
SMALL_MD = "# Hello\n\nThis is a small document.\n"
LARGE_MD = "\n\n".join(
    f"## Section {i}\n\n{' '.join(f'word{j}' for j in range(100))}" for i in range(1000)
)


def measure_memory(fn, *args, **kwargs):
    tracemalloc.start()
    result = fn(*args, **kwargs)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, current, peak


def test_small_memory() -> None:
    from pimd import PiMD

    engine = PiMD()
    _, current, peak = measure_memory(engine.md_text_to_docx_bytes, SMALL_MD)
    print("\n  Small document:")
    print(f"    Current: {current / 1024:.1f} KB")
    print(f"    Peak:    {peak / 1024:.1f} KB")


def test_large_memory() -> None:
    from pimd import PiMD

    engine = PiMD()
    _, current, peak = measure_memory(engine.md_text_to_docx_bytes, LARGE_MD)
    print("\n  Large document (1000 sections):")
    print(f"    Current: {current / 1024:.1f} KB")
    print(f"    Peak:    {peak / 1024:.1f} KB")


def test_batch_memory() -> None:
    from pimd.converters.markdown import MarkdownConverter
    from pimd.parallel import parallel_map

    converter = MarkdownConverter()

    def convert(text):
        return converter.convert_text(text)

    texts = [f"# Doc {i}\n\nContent {i}\n" for i in range(50)]
    _, current, peak = measure_memory(parallel_map, convert, texts, max_workers=4)
    print("\n  Batch (50 conversions):")
    print(f"    Current: {current / 1024:.1f} KB")
    print(f"    Peak:    {peak / 1024:.1f} KB")


if __name__ == "__main__":
    print("PiMD Memory Benchmarks\n" + "=" * 40)
    test_small_memory()
    test_large_memory()
    test_batch_memory()
