"""Speed benchmarks for PiMD conversion pipeline.

Usage:
    python -m pytest benchmarks/ -v --benchmark-only
    python benchmarks/test_speed.py
"""

from __future__ import annotations

import time
from pathlib import Path

HERE = Path(__file__).parent
SMALL_MD = "# Hello\n\nThis is a small document.\n"
MEDIUM_MD = "\n\n".join(
    f"## Section {i}\n\nParagraph content here with some **bold** and *italic*." for i in range(100)
)
LARGE_MD = "\n\n".join(
    f"## Section {i}\n\n{' '.join(f'word{j}' for j in range(100))}" for i in range(1000)
)


def test_small_conversion_speed() -> None:
    from pimd import PiMD

    engine = PiMD()
    t0 = time.perf_counter()
    for _ in range(100):
        engine.md_text_to_docx_bytes(SMALL_MD)
    elapsed = time.perf_counter() - t0
    print(f"\n  Small: 100 conversions in {elapsed:.2f}s ({elapsed / 100 * 1000:.1f}ms each)")


def test_medium_conversion_speed() -> None:
    from pimd import PiMD

    engine = PiMD()
    t0 = time.perf_counter()
    for _ in range(10):
        engine.md_text_to_docx_bytes(MEDIUM_MD)
    elapsed = time.perf_counter() - t0
    print(f"\n  Medium: 10 conversions in {elapsed:.2f}s ({elapsed / 10 * 1000:.1f}ms each)")


def test_large_conversion_speed() -> None:
    from pimd import PiMD

    engine = PiMD()
    t0 = time.perf_counter()
    engine.md_text_to_docx_bytes(LARGE_MD)
    elapsed = time.perf_counter() - t0
    print(f"\n  Large: 1 conversion in {elapsed:.2f}s")


if __name__ == "__main__":
    print("PiMD Speed Benchmarks\n" + "=" * 40)
    test_small_conversion_speed()
    test_medium_conversion_speed()
    test_large_conversion_speed()
