"""Simple in-memory TTL cache."""

from __future__ import annotations

import sys
import time
from typing import Any

from pimd.caching.base import CacheBackend


class MemoryCache(CacheBackend):
    """Thread-safe in-memory cache with optional TTL.

    Usage::

        cache = MemoryCache(default_ttl=60)
        cache.set("key", {"data": 42})
        value = cache.get("key")
    """

    def __init__(self, default_ttl: int = 300) -> None:
        self._default_ttl = default_ttl
        self._store: dict[str, _Entry] = {}
        self.hit_count: int = 0
        self.miss_count: int = 0
        self.set_count: int = 0

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            self.miss_count += 1
            return None
        if entry.expires_at is not None and time.monotonic() > entry.expires_at:
            del self._store[key]
            self.miss_count += 1
            return None
        self.hit_count += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        if effective_ttl > 0:
            expires_at = time.monotonic() + effective_ttl
        else:
            expires_at = -1.0
        self._store[key] = _Entry(value=value, expires_at=expires_at)
        self.set_count += 1

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def keys(self) -> list[str]:
        now = time.monotonic()
        return [
            k
            for k, v in self._store.items()
            if v.expires_at is None or now <= v.expires_at
        ]

    @property
    def size(self) -> int:
        return len(self._store)

    def __len__(self) -> int:
        return self.size

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def info(self) -> dict:
        return {
            "hits": self.hit_count,
            "misses": self.miss_count,
            "sets": self.set_count,
            "size": self.size,
            "backend_type": type(self).__name__,
        }

    def _estimate_memory(self) -> int:
        return sys.getsizeof(self._store) + sum(
            sys.getsizeof(k) + sys.getsizeof(v.value)
            for k, v in self._store.items()
        )


class _Entry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, expires_at: float | None) -> None:
        self.value = value
        self.expires_at = expires_at


__all__ = [
    "MemoryCache",
]
