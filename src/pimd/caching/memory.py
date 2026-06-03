"""Simple in-memory TTL cache."""

from __future__ import annotations

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

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        if effective_ttl > 0:
            expires_at = time.monotonic() + effective_ttl
        else:
            expires_at = -1.0  # expired immediately
        self._store[key] = _Entry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


class _Entry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, expires_at: float | None) -> None:
        self.value = value
        self.expires_at = expires_at
