"""Cache metrics collector for aggregating hit/miss/set events."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone


class CacheMetricsCollector:
    """Collects and aggregates cache metrics across backends.

    Usage::

        metrics = CacheMetricsCollector()
        metrics.record_hit("memory", "my-key")
        metrics.record_miss("redis", "other-key")
        report = metrics.report()
    """

    def __init__(self) -> None:
        self._hits: dict[str, int] = defaultdict(int)
        self._misses: dict[str, int] = defaultdict(int)
        self._sets: dict[str, int] = defaultdict(int)
        self._key_hits: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._key_misses: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._key_sets: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._start_time: datetime = datetime.now(timezone.utc)

    def record_hit(self, backend: str, key: str) -> None:
        self._hits[backend] += 1
        self._key_hits[backend][key] += 1

    def record_miss(self, backend: str, key: str) -> None:
        self._misses[backend] += 1
        self._key_misses[backend][key] += 1

    def record_set(self, backend: str, key: str) -> None:
        self._sets[backend] += 1
        self._key_sets[backend][key] += 1

    def report(self) -> dict:
        """Return an aggregated metrics report."""
        per_backend: dict[str, dict] = {}
        all_backends = set(self._hits) | set(self._misses) | set(self._sets)
        for backend in sorted(all_backends):
            hits = self._hits.get(backend, 0)
            misses = self._misses.get(backend, 0)
            total = hits + misses
            hit_rate = hits / total if total > 0 else 0.0
            per_backend[backend] = {
                "hits": hits,
                "misses": misses,
                "sets": self._sets.get(backend, 0),
                "total_ops": hits + misses + self._sets.get(backend, 0),
                "hit_rate": hit_rate,
                "top_hit_keys": dict(
                    sorted(self._key_hits[backend].items(), key=lambda x: -x[1])[:10]
                ),
                "top_miss_keys": dict(
                    sorted(self._key_misses[backend].items(), key=lambda x: -x[1])[:10]
                ),
            }

        total_hits = sum(self._hits.values())
        total_misses = sum(self._misses.values())
        total_sets = sum(self._sets.values())
        total_ops = total_hits + total_misses + total_sets
        overall_hit_rate = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0.0

        now = datetime.now(timezone.utc)
        uptime = (now - self._start_time).total_seconds()

        return {
            "overall": {
                "hits": total_hits,
                "misses": total_misses,
                "sets": total_sets,
                "total_ops": total_ops,
                "hit_rate": overall_hit_rate,
                "uptime_seconds": uptime,
                "start_time": self._start_time.isoformat(),
            },
            "per_backend": per_backend,
        }

    def clear(self) -> None:
        """Reset all collected metrics."""
        self._hits.clear()
        self._misses.clear()
        self._sets.clear()
        self._key_hits.clear()
        self._key_misses.clear()
        self._key_sets.clear()
        self._start_time = datetime.now(timezone.utc)


__all__ = [
    "CacheMetricsCollector",
]
