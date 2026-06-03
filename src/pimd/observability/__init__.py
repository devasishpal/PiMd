"""Observability — timings, metrics, conversion reports."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from pimd.models import DocumentStatistics


@dataclass
class ConversionMetrics:
    """Timing and size metrics for a single conversion run."""

    parse_time: float = 0.0
    render_time: float = 0.0
    total_time: float = 0.0
    input_size: int = 0
    output_size: int = 0
    block_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "parse_time": round(self.parse_time, 4),
            "render_time": round(self.render_time, 4),
            "total_time": round(self.total_time, 4),
            "input_size": self.input_size,
            "output_size": self.output_size,
            "block_count": self.block_count,
        }


@dataclass
class ConversionReport:
    """Full execution report for a conversion run."""

    source_format: str = ""
    target_format: str = "docx"
    metrics: ConversionMetrics = field(default_factory=ConversionMetrics)
    statistics: DocumentStatistics | None = None
    success: bool = True
    error: str | None = None
    cache_hit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_format": self.source_format,
            "target_format": self.target_format,
            "metrics": self.metrics.to_dict(),
            "statistics": {
                "heading_count": self.statistics.heading_count if self.statistics else 0,
                "paragraph_count": self.statistics.paragraph_count if self.statistics else 0,
                "code_block_count": self.statistics.code_block_count if self.statistics else 0,
                "table_count": self.statistics.table_count if self.statistics else 0,
                "image_count": self.statistics.image_count if self.statistics else 0,
                "list_item_count": self.statistics.list_item_count if self.statistics else 0,
                "word_count": self.statistics.word_count if self.statistics else 0,
                "total_blocks": self.statistics.total_blocks if self.statistics else 0,
            }
            if self.statistics
            else {},
            "success": self.success,
            "error": self.error,
            "cache_hit": self.cache_hit,
        }


class Timer:
    """Simple context manager for timing code blocks.

    Usage::

        timer = Timer()
        with timer:
            do_something()
        print(timer.elapsed)
    """

    def __init__(self) -> None:
        self._start: float | None = None
        self.elapsed: float = 0.0

    def __enter__(self) -> Timer:
        self._start = time.monotonic()
        return self

    def __exit__(self, *args: object) -> None:
        if self._start is not None:
            self.elapsed = time.monotonic() - self._start

    def __float__(self) -> float:
        return self.elapsed
