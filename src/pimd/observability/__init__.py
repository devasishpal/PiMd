"""Observability — timings, metrics, profiling, and conversion reports.

Unified module consolidating ``pimd.observability`` and ``pimd.profiling``.
"""

from __future__ import annotations

import gc
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pimd.models import DocumentStatistics

__all__ = [
    "BuildMetrics",
    "ConversionMetrics",
    "ConversionReport",
    "ExecutionReport",
    "measure_time",
    "MemorySnapshot",
    "MetricsCollector",
    "PipelineProfile",
    "profile_conversion",
    "Profiler",
    "Timer",
]


# ======================================================================
# Timer (merged: context manager from observability + lap support from profiling)
# ======================================================================


class Timer:
    """High-precision timer with context-manager and lap support.

    Usage::

        # As context manager
        with Timer("parse") as t:
            parse(source)
        print(t.elapsed)

        # With laps
        t = Timer("total")
        t.start_timer()
        ... step one ...
        t.lap("step1")
        ... step two ...
        t.lap("step2")
        print(t.elapsed, t.laps)
    """

    def __init__(self, name: str = "") -> None:
        self.name: str = name
        self._start: float = 0.0
        self.elapsed: float = 0.0
        self.laps: list[dict[str, float]] = []

    # ---- Context manager ----

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed = time.perf_counter() - self._start

    # ---- Lap support ----

    def start_timer(self) -> None:
        """Manually start the timer (alternative to context-manager)."""
        self._start = time.perf_counter()

    def lap(self, label: str) -> float:
        """Record a lap and return the elapsed time so far."""
        now = time.perf_counter()
        lap_time = now - self._start
        self.laps.append({"label": label, "time": lap_time})
        return lap_time

    # ---- Properties ----

    @property
    def seconds(self) -> float:
        return self.elapsed

    @property
    def milliseconds(self) -> float:
        return self.elapsed * 1000

    # ---- Utilities ----

    def reset(self) -> None:
        self._start = 0.0
        self.elapsed = 0.0
        self.laps = []

    def __float__(self) -> float:
        return self.elapsed


# ======================================================================
# Utility
# ======================================================================


def measure_time(fn: Callable, *args: Any, **kwargs: Any) -> tuple[Any, float]:
    """Call ``fn`` and return ``(result, elapsed_seconds)``."""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = time.perf_counter() - t0
    return result, elapsed


# ======================================================================
# Metrics
# ======================================================================


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


# ======================================================================
# Memory
# ======================================================================


def _get_memory_usage() -> tuple[float, float]:
    try:
        import psutil

        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        return mem.rss / (1024 * 1024), mem.vms / (1024 * 1024)
    except ImportError:
        return 0.0, 0.0


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""

    rss_mb: float = 0.0
    vms_mb: float = 0.0
    gc_objects: int = 0

    @staticmethod
    def take() -> MemorySnapshot:
        rss, vms = _get_memory_usage()
        gc.collect()
        return MemorySnapshot(
            rss_mb=rss,
            vms_mb=vms,
            gc_objects=len(gc.get_objects()),
        )

    def __sub__(self, other: MemorySnapshot) -> MemorySnapshot:
        return MemorySnapshot(
            rss_mb=self.rss_mb - other.rss_mb,
            vms_mb=self.vms_mb - other.vms_mb,
            gc_objects=self.gc_objects - other.gc_objects,
        )


# ======================================================================
# Pipeline profile
# ======================================================================


@dataclass
class PipelineProfile:
    """Timing profile for a pipeline execution."""

    stage_times: dict[str, float] = field(default_factory=dict)
    total_seconds: float = 0.0
    memory_before_mb: float = 0.0
    memory_after_mb: float = 0.0
    memory_delta_mb: float = 0.0

    @property
    def total_ms(self) -> float:
        return self.total_seconds * 1000

    def fastest_stage(self) -> str | None:
        if not self.stage_times:
            return None
        return min(self.stage_times, key=self.stage_times.get)

    def slowest_stage(self) -> str | None:
        if not self.stage_times:
            return None
        return max(self.stage_times, key=self.stage_times.get)


# ======================================================================
# ConversionReport (merged: observability + profiling fields)
# ======================================================================


@dataclass
class ConversionReport:
    """Full execution report for a conversion run.

    Combines conversion-level metadata (source/target format, metrics,
    statistics) with performance profiling data (timing, memory, stages).
    """

    # --- Conversion metadata (from observability) ---
    source_format: str = ""
    target_format: str = "docx"
    metrics: ConversionMetrics = field(default_factory=ConversionMetrics)
    statistics: DocumentStatistics | None = None
    success: bool = True
    error: str | None = None
    cache_hit: bool = False

    # --- Performance data (from profiling) ---
    source: str = ""
    source_size_mb: float = 0.0
    output_format: str = ""
    total_seconds: float = 0.0
    memory_peak_mb: float = 0.0
    memory_delta_mb: float = 0.0
    blocks_processed: int = 0
    diagrams_rendered: int = 0
    equations_rendered: int = 0
    stages: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    # ---- Properties ----

    @property
    def total_ms(self) -> float:
        return self.total_seconds * 1000

    @property
    def blocks_per_second(self) -> float:
        if self.total_seconds > 0:
            return self.blocks_processed / self.total_seconds
        return 0.0

    # ---- Serialisation ----

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            # Conversion metadata
            "source_format": self.source_format,
            "target_format": self.target_format,
            "metrics": self.metrics.to_dict(),
            "statistics": (
                {
                    "heading_count": self.statistics.heading_count,
                    "paragraph_count": self.statistics.paragraph_count,
                    "code_block_count": self.statistics.code_block_count,
                    "table_count": self.statistics.table_count,
                    "image_count": self.statistics.image_count,
                    "list_item_count": self.statistics.list_item_count,
                    "word_count": self.statistics.word_count,
                    "total_blocks": self.statistics.total_blocks,
                }
                if self.statistics
                else {}
            ),
            "success": self.success,
            "error": self.error,
            "cache_hit": self.cache_hit,
            # Performance data
            "source": self.source,
            "source_size_mb": round(self.source_size_mb, 2),
            "output_format": self.output_format,
            "total_seconds": round(self.total_seconds, 3),
            "total_ms": round(self.total_ms, 1),
            "memory_peak_mb": round(self.memory_peak_mb, 1),
            "memory_delta_mb": round(self.memory_delta_mb, 1),
            "blocks_processed": self.blocks_processed,
            "diagrams_rendered": self.diagrams_rendered,
            "equations_rendered": self.equations_rendered,
            "blocks_per_second": round(self.blocks_per_second, 1),
            "stages": self.stages,
            "errors": self.errors,
        }
        return d

    def summary(self) -> str:
        lines: list[str] = []

        # Conversion metadata
        if self.source_format:
            lines.append(f"  Source format: {self.source_format}")
        if self.target_format:
            lines.append(f"  Target format: {self.target_format}")

        # Timing
        if self.metrics.total_time:
            lines.append(
                f"  Time:   {self.metrics.total_time:.2f}s "
                f"(parse: {self.metrics.parse_time:.2f}s, "
                f"render: {self.metrics.render_time:.2f}s)"
            )
        if self.total_seconds:
            lines.append(
                f"  Profiled: {self.total_seconds:.2f}s ({self.total_ms:.0f}ms)"
            )

        # Sizes
        if self.metrics.input_size:
            lines.append(f"  Input:  {self.metrics.input_size:,} bytes")
        if self.metrics.output_size:
            lines.append(f"  Output: {self.metrics.output_size:,} bytes")
        if self.source_size_mb:
            lines.append(f"  Source: {self.source} ({self.source_size_mb:.1f} MB)")

        # Memory
        if self.memory_delta_mb:
            lines.append(
                f"  Memory: {self.memory_delta_mb:+.1f} MB "
                f"(peak: {self.memory_peak_mb:.1f} MB)"
            )

        # Blocks / diagrams / equations
        if self.metrics.block_count:
            lines.append(f"  Blocks: {self.metrics.block_count}")
        if self.blocks_processed:
            lines.append(
                f"  Blocks: {self.blocks_processed} ({self.blocks_per_second:.0f} blk/s)"
            )
        if self.diagrams_rendered:
            lines.append(f"  Diagrams: {self.diagrams_rendered}")
        if self.equations_rendered:
            lines.append(f"  Equations: {self.equations_rendered}")

        # Stages
        if self.stages:
            lines.append("  Stages:")
            for name, dur in self.stages.items():
                lines.append(f"    {name}: {dur * 1000:.1f}ms")

        # Error
        if self.error:
            lines.append(f"  Error: {self.error}")

        return "\n".join(lines)


# ======================================================================
# Profiler
# ======================================================================


class Profiler:
    """Collect profiling data across a conversion run."""

    def __init__(self) -> None:
        self._snapshots: list[MemorySnapshot] = []
        self._timers: dict[str, Timer] = {}

    def snapshot(self, label: str = "") -> MemorySnapshot:
        snap = MemorySnapshot.take()
        self._snapshots.append(snap)
        return snap

    def timer(self, name: str) -> Timer:
        t = Timer(name=name)
        self._timers[name] = t
        return t

    def get_timer(self, name: str) -> Timer | None:
        return self._timers.get(name)

    def peak_memory_mb(self) -> float:
        if not self._snapshots:
            return 0.0
        return max(s.rss_mb for s in self._snapshots)

    @property
    def first_snapshot(self) -> MemorySnapshot | None:
        return self._snapshots[0] if self._snapshots else None

    @property
    def last_snapshot(self) -> MemorySnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def report(self, **kwargs: Any) -> ConversionReport:
        report = ConversionReport(**kwargs)
        report.memory_peak_mb = self.peak_memory_mb()
        if self.first_snapshot and self.last_snapshot:
            delta = self.last_snapshot - self.first_snapshot
            report.memory_delta_mb = delta.rss_mb
        for name, timer in self._timers.items():
            report.stages[name] = timer.elapsed
        return report


def profile_conversion(
    fn: Callable,
    *args: Any,
    **kwargs: Any,
) -> tuple[Any, ConversionReport]:
    """Wrap a conversion function with profiling.

    Returns ``(result, report)``.
    """
    profiler = Profiler()
    profiler.snapshot("before")
    timer = profiler.timer("total")
    timer.start_timer()

    try:
        result = fn(*args, **kwargs)
    except Exception as exc:
        timer.elapsed = time.perf_counter() - timer._start
        profiler.snapshot("after")
        report = profiler.report(
            source=kwargs.get("source", str(kwargs.get("input_path", ""))),
            errors=[str(exc)],
        )
        report.total_seconds = timer.elapsed
        return None, report

    timer.elapsed = time.perf_counter() - timer._start
    profiler.snapshot("after")
    report = profiler.report(
        source=kwargs.get("source", str(kwargs.get("input_path", ""))),
    )
    report.total_seconds = timer.elapsed
    return result, report


# ======================================================================
# Build-level metrics
# ======================================================================


@dataclass
class BuildMetrics:
    """Build-level metrics for multi-file project conversions."""

    files_total: int = 0
    files_succeeded: int = 0
    files_failed: int = 0
    files_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    output_size_bytes: int = 0

    @property
    def success_rate(self) -> float:
        if self.files_total == 0:
            return 0.0
        return self.files_succeeded / self.files_total * 100

    @property
    def duration_ms(self) -> float:
        return self.duration_seconds * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_total": self.files_total,
            "files_succeeded": self.files_succeeded,
            "files_failed": self.files_failed,
            "files_skipped": self.files_skipped,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": round(self.duration_seconds, 3),
            "duration_ms": round(self.duration_ms, 1),
            "success_rate": round(self.success_rate, 1),
            "output_size_bytes": self.output_size_bytes,
        }


@dataclass
class ExecutionReport:
    """Execution-level report wrapping a build result."""

    build: BuildMetrics = field(default_factory=BuildMetrics)
    conversions: list[ConversionReport] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "build": self.build.to_dict(),
            "conversions": [c.to_dict() for c in self.conversions],
            "metadata": self.metadata,
        }


class MetricsCollector:
    """Collects metrics across multiple conversions."""

    def __init__(self) -> None:
        self._reports: list[ConversionReport] = []

    def add(self, report: ConversionReport) -> None:
        self._reports.append(report)

    @property
    def reports(self) -> list[ConversionReport]:
        return list(self._reports)

    @property
    def total_time(self) -> float:
        return sum(
            r.metrics.total_time or r.total_seconds for r in self._reports
        )

    @property
    def total_input_size(self) -> int:
        return sum(r.metrics.input_size for r in self._reports)

    @property
    def total_output_size(self) -> int:
        return sum(r.metrics.output_size for r in self._reports)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self._reports if r.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self._reports if not r.success)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_conversions": len(self._reports),
            "successful": self.success_count,
            "failed": self.failure_count,
            "total_time_seconds": round(self.total_time, 3),
            "total_input_size": self.total_input_size,
            "total_output_size": self.total_output_size,
            "conversion_reports": [r.to_dict() for r in self._reports],
        }

    def to_build_metrics(self) -> BuildMetrics:
        return BuildMetrics(
            files_total=len(self._reports),
            files_succeeded=self.success_count,
            files_failed=self.failure_count,
            duration_seconds=self.total_time,
        )
