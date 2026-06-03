"""Performance profiling — timing, memory, pipeline profiling, and conversion reports."""

from __future__ import annotations

import gc
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Timer:
    """High-precision timer with lap support."""

    name: str = ""
    start: float = 0.0
    elapsed: float = 0.0
    laps: list[dict[str, float]] = field(default_factory=list)

    def __enter__(self) -> Timer:
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.elapsed = time.perf_counter() - self.start

    def lap(self, label: str) -> float:
        now = time.perf_counter()
        lap_time = now - self.start
        self.laps.append({"label": label, "time": lap_time})
        return lap_time

    @property
    def seconds(self) -> float:
        return self.elapsed

    @property
    def milliseconds(self) -> float:
        return self.elapsed * 1000

    def reset(self) -> None:
        self.start = 0.0
        self.elapsed = 0.0
        self.laps = []


def measure_time(fn: Callable, *args: Any, **kwargs: Any) -> tuple[Any, float]:
    """Call fn and return (result, elapsed_seconds)."""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = time.perf_counter() - t0
    return result, elapsed


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


def _get_memory_usage() -> tuple[float, float]:
    try:
        import psutil

        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        return mem.rss / (1024 * 1024), mem.vms / (1024 * 1024)
    except ImportError:
        return 0.0, 0.0


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


@dataclass
class ConversionReport:
    """Complete performance report for a conversion run."""

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

    @property
    def total_ms(self) -> float:
        return self.total_seconds * 1000

    @property
    def blocks_per_second(self) -> float:
        if self.total_seconds > 0:
            return self.blocks_processed / self.total_seconds
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
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

    def summary(self) -> str:
        lines = [
            f"  Source:  {self.source} ({self.source_size_mb:.1f} MB)",
            f"  Format:  {self.output_format}",
            f"  Time:    {self.total_seconds:.2f}s ({self.total_ms:.0f}ms)",
            f"  Memory:  {self.memory_delta_mb:+.1f} MB (peak: {self.memory_peak_mb:.1f} MB)",
            f"  Blocks:  {self.blocks_processed} ({self.blocks_per_second:.0f} blk/s)",
        ]
        if self.diagrams_rendered:
            lines.append(f"  Diagrams: {self.diagrams_rendered}")
        if self.equations_rendered:
            lines.append(f"  Equations: {self.equations_rendered}")
        if self.stages:
            lines.append("  Stages:")
            for name, dur in self.stages.items():
                lines.append(f"    {name}: {dur * 1000:.1f}ms")
        return "\n".join(lines)


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

    Returns (result, report).
    """
    profiler = Profiler()
    profiler.snapshot("before")
    timer = profiler.timer("total")
    timer.start = time.perf_counter()

    try:
        result = fn(*args, **kwargs)
    except Exception as exc:
        timer.elapsed = time.perf_counter() - timer.start
        profiler.snapshot("after")
        report = profiler.report(
            source=kwargs.get("source", str(kwargs.get("input_path", ""))),
            errors=[str(exc)],
        )
        report.total_seconds = timer.elapsed
        return None, report

    timer.elapsed = time.perf_counter() - timer.start
    profiler.snapshot("after")
    report = profiler.report(
        source=kwargs.get("source", str(kwargs.get("input_path", ""))),
    )
    report.total_seconds = timer.elapsed
    return result, report
