"""Parallel processing — thread and process pool executors for concurrent work."""

from __future__ import annotations

import concurrent.futures
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParallelResult:
    """Result of a parallel task execution."""

    success: bool
    data: Any = None
    error: str | None = None
    task_id: str | None = None


@dataclass
class BatchSummary:
    """Summary of a parallel batch execution."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    results: list[ParallelResult] = field(default_factory=list)
    duration: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 1.0
        return self.succeeded / self.total


class ParallelExecutor(ABC):
    """Abstract base for parallel task executors."""

    def __init__(self, max_workers: int | None = None) -> None:
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)

    def __enter__(self) -> ParallelExecutor:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    @abstractmethod
    def map(self, fn: Callable, items: list[Any], **kwargs: Any) -> list[ParallelResult]:
        """Apply fn to each item in parallel."""

    def batch(self, fn: Callable, items: list[Any], **kwargs: Any) -> BatchSummary:
        """Execute a batch of tasks and return a summary."""
        import time

        t0 = time.perf_counter()
        results = self.map(fn, items, **kwargs)
        duration = time.perf_counter() - t0
        succeeded = sum(1 for r in results if r.success)
        return BatchSummary(
            total=len(results),
            succeeded=succeeded,
            failed=len(results) - succeeded,
            results=results,
            duration=duration,
        )


class ThreadExecutor(ParallelExecutor):
    """Thread-based parallel executor (I/O-bound tasks)."""

    def map(self, fn: Callable, items: list[Any], **kwargs: Any) -> list[ParallelResult]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(fn, item, **kwargs): i for i, item in enumerate(items)}
            results: list[ParallelResult] = []
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                try:
                    data = future.result()
                    results.append(ParallelResult(success=True, data=data, task_id=str(idx)))
                except Exception as exc:
                    results.append(ParallelResult(success=False, error=str(exc), task_id=str(idx)))
            results.sort(key=lambda r: int(r.task_id or "0"))
            return results


class ProcessExecutor(ParallelExecutor):
    """Process-based parallel executor (CPU-bound tasks)."""

    def map(self, fn: Callable, items: list[Any], **kwargs: Any) -> list[ParallelResult]:
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(fn, item, **kwargs): i for i, item in enumerate(items)}
            results: list[ParallelResult] = []
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                try:
                    data = future.result()
                    results.append(ParallelResult(success=True, data=data, task_id=str(idx)))
                except Exception as exc:
                    results.append(ParallelResult(success=False, error=str(exc), task_id=str(idx)))
            results.sort(key=lambda r: int(r.task_id or "0"))
            return results


def parallel_map(
    fn: Callable,
    items: list[Any],
    *,
    max_workers: int | None = None,
    use_processes: bool = False,
    **kwargs: Any,
) -> list[ParallelResult]:
    """Convenience: run fn on each item in parallel.

    Args:
        fn: Function to apply.
        items: List of inputs.
        max_workers: Number of workers (default: CPU count + 4).
        use_processes: Use ProcessPoolExecutor (default: ThreadPoolExecutor).
    """
    executor: ParallelExecutor
    if use_processes:
        executor = ProcessExecutor(max_workers)
    else:
        executor = ThreadExecutor(max_workers)
    return executor.map(fn, items, **kwargs)


def parallel_batch(
    fn: Callable,
    items: list[Any],
    *,
    max_workers: int | None = None,
    use_processes: bool = False,
    **kwargs: Any,
) -> BatchSummary:
    """Convenience: run fn on each item and return a summary."""
    executor: ParallelExecutor
    if use_processes:
        executor = ProcessExecutor(max_workers)
    else:
        executor = ThreadExecutor(max_workers)
    return executor.batch(fn, items, **kwargs)
