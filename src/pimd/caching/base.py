"""Abstract cache backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


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
