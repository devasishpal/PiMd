"""Abstract cache backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheStats:
    hits: int
    misses: int
    sets: int
    size: int
    hit_rate: float
    memory_estimate: int
    backend_type: str


class CacheBackend(ABC):
    """Abstract interface for cache backends.

    Implementations must be thread-safe.
    """

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Return cached value for *key*, or ``None`` if missing / expired."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store *value* under *key* with an optional TTL (seconds)."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove *key* from the cache."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all entries from the cache."""

    def make_key(self, *parts: str, **kwargs: str) -> str:
        """Generate a cache key from parts and kwargs."""
        key = ":".join(str(p) for p in parts if p)
        if kwargs:
            kw_part = "&".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = f"{key}:{kw_part}"
        return key

    def info(self) -> dict:
        """Return a dict of cache statistics and metadata."""
        return {
            "hits": getattr(self, "hit_count", 0),
            "misses": getattr(self, "miss_count", 0),
            "sets": getattr(self, "set_count", 0),
            "size": getattr(self, "size", 0) if hasattr(type(self), "size") and isinstance(getattr(type(self), "size", None), property) else len(getattr(self, "_store", {})),
            "backend_type": type(self).__name__,
        }

    @property
    def stats(self) -> CacheStats:
        """Return a CacheStats dataclass for the current cache state."""
        info = self.info()
        hits = info["hits"]
        misses = info["misses"]
        total = hits + misses
        hit_rate = hits / total if total > 0 else 0.0
        return CacheStats(
            hits=hits,
            misses=misses,
            sets=info["sets"],
            size=info["size"],
            hit_rate=hit_rate,
            memory_estimate=getattr(self, "_estimate_memory", lambda: 0)(),
            backend_type=info["backend_type"],
        )

    def _estimate_memory(self) -> int:
        return 0


__all__ = [
    "CacheBackend",
    "CacheStats",
]
