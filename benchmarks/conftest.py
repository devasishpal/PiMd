"""Common helpers for PiMD benchmarks."""

from __future__ import annotations

import math
import random
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

# ---------------------------------------------------------------------------
# Sample markdown generation
# ---------------------------------------------------------------------------

_LOREM_IPSUM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
    "nisi ut aliquip ex ea commodo consequat."
)

_HEADINGS = ["# ", "## ", "### ", "#### ", "##### ", "###### "]

_LANGUAGES = ["python", "javascript", "rust", "cpp", "go", "ruby"]


def generate_sample_markdown(size_bytes: int, seed: int = 42) -> str:
    """Generate a Markdown string approximately *size_bytes* in length.

    Produces realistic-looking Markdown with headings, paragraphs, code
    blocks, lists, horizontal rules, bold/italic text, and tables.
    """
    rng = random.Random(seed)
    parts: list[str] = []
    target = size_bytes
    # Ensure we end cleanly
    budget = target

    while budget > 0:
        choice = rng.randint(0, 7)
        snippet = ""

        if choice == 0:
            level = rng.choice(_HEADINGS)
            text = _rand_words(rng, rng.randint(3, 12))
            snippet = f"{level}{text}\n\n"
        elif choice == 1:
            sentences = rng.randint(2, 6)
            para = " ".join(
                _rand_words(rng, rng.randint(5, 20)) for _ in range(sentences)
            )
            snippet = f"{para}\n\n"
        elif choice == 2:
            lang = rng.choice(_LANGUAGES)
            lines = rng.randint(3, 10)
            code = "\n".join(
                _rand_words(rng, rng.randint(1, 8)) for _ in range(lines)
            )
            snippet = f"```{lang}\n{code}\n```\n\n"
        elif choice == 3:
            items = rng.randint(2, 5)
            list_lines = [
                f"- {_rand_words(rng, rng.randint(3, 10))}" for _ in range(items)
            ]
            snippet = f"{chr(10).join(list_lines)}\n\n"
        elif choice == 4:
            snippet = "---\n\n"
        elif choice == 5:
            text = _rand_words(rng, rng.randint(3, 8))
            snippet = f"**{text}** and *{_rand_words(rng, rng.randint(2, 5))}*\n\n"
        elif choice == 6:
            cols = rng.randint(2, 5)
            rows = rng.randint(2, 4)
            header = "| " + " | ".join(f"Col {i}" for i in range(cols)) + " |\n"
            sep = "| " + " | ".join("---" for _ in range(cols)) + " |\n"
            data = ""
            for _ in range(rows):
                data += (
                    "| "
                    + " | ".join(_rand_words(rng, rng.randint(1, 3)) for _ in range(cols))
                    + " |\n"
                )
            snippet = f"{header}{sep}{data}\n"
        elif choice == 7:
            snippet = f"[{_rand_words(rng, 2)}](https://example.com/{rng.randint(1, 100)})\n\n"

        parts.append(snippet)
        budget -= len(snippet)

    # Trim to exact target by cutting off excess characters
    result = "".join(parts)
    if len(result) > target:
        # Cut at last paragraph boundary to keep it valid-ish
        result = result[:target]
        last_nl = result.rfind("\n\n")
        if last_nl > target // 2:
            result = result[: last_nl + 2]
    return result


def _rand_words(rng: random.Random, n: int) -> str:
    """Return *n* random-ish words as a single string."""
    words = [_LOREM_IPSUM[rng.randint(0, len(_LOREM_IPSUM) - 10) :][: rng.randint(3, 12)] for _ in range(n)]
    return " ".join(w.strip(",").strip(".") for w in words)


# ---------------------------------------------------------------------------
# Table formatting
# ---------------------------------------------------------------------------


def format_benchmark_results(
    rows: list[dict[str, Any]],
    *,
    key_order: list[str] | None = None,
    separator: str = " | ",
) -> str:
    """Format a list of dicts as a human-readable table.

    Returns a string with aligned columns.  Keys become column headers.
    """
    if not rows:
        return "(no results)"

    keys = key_order or list(rows[0].keys())
    # Ensure all keys in every row
    for row in rows:
        for k in keys:
            row.setdefault(k, "")

    # Convert everything to string and measure widths
    str_rows: list[list[str]] = []
    col_widths: list[int] = []
    for k in keys:
        col_widths.append(len(str(k)))
    for row in rows:
        str_row: list[str] = []
        for idx, k in enumerate(keys):
            val = str(row.get(k, ""))
            str_row.append(val)
            col_widths[idx] = max(col_widths[idx], len(val))
        str_rows.append(str_row)

    # Build separator line
    sep_line = "-+-".join("-" * w for w in col_widths)

    # Format header
    header = separator.join(str(k).ljust(col_widths[i]) for i, k in enumerate(keys))

    lines: list[str] = [header, sep_line]
    for sr in str_rows:
        lines.append(
            separator.join(sr[i].ljust(col_widths[i]) for i in range(len(keys)))
        )

    return "\n".join(lines)


def mbps(size_bytes: int, time_seconds: float) -> float:
    """Calculate throughput in megabytes per second."""
    if time_seconds <= 0:
        return math.nan
    return (size_bytes / 1024 / 1024) / time_seconds


# ---------------------------------------------------------------------------
# Output suppression (for silencing pimd's print/log output during benchmarks)
# ---------------------------------------------------------------------------


@contextmanager
def suppress_stdout() -> Iterator[None]:
    """Temporarily redirect ``sys.stdout`` to ``os.devnull``."""
    import os

    old_stdout = sys.stdout
    try:
        with open(os.devnull, "w", encoding="utf-8") as null:
            sys.stdout = null
            yield
    finally:
        sys.stdout = old_stdout


# ---------------------------------------------------------------------------
# High-precision timer
# ---------------------------------------------------------------------------


@contextmanager
def timer() -> Iterator[list[float]]:
    """Context manager that captures elapsed wall-clock time.

    Usage::

        with timer() as t:
            do_something()
        print(f"Took {t[0]:.3f}s")
    """
    elapsed: list[float] = [0.0]
    start = time.perf_counter()
    try:
        yield elapsed
    finally:
        elapsed[0] = time.perf_counter() - start
