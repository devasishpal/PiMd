"""UnifiedCacheManager — single cache for all PiMD + PiDraw operations.

Levels:
  L1 — MemoryCache (fast, process-local)
  L2 — DiskCache   (persistent, configurable path)
  L3 — RedisCache  (distributed, optional)

PiMD and PiDraw share this single cache hierarchy.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CacheEntry:
    key: str
    data: Any
    created: float = field(default_factory=time.time)
    ttl: float = 0.0  # 0 = no expiry
    access_count: int = 0

    @property
    def expired(self) -> bool:
        return self.ttl > 0 and (time.time() - self.created) > self.ttl


@dataclass
class UnifiedCacheStats:
    l1_entries: int = 0
    l2_entries: int = 0
    l3_available: bool = False
    l3_entries: int = 0
    hits: int = 0
    misses: int = 0
    size_bytes: int = 0


class UnifiedCacheManager:
    """Single cache manager — frontend for all caching in PiMD.

    Usage::

        cache = UnifiedCacheManager()
        cache.set("diagram:mermaid:abc", result)
        cached = cache.get("diagram:mermaid:abc")
        cache.clear()
    """

    def __init__(self, cache_dir: str | None = None, max_l1: int = 500) -> None:
        self._lock = threading.Lock()
        self._l1: dict[str, CacheEntry] = {}
        self._max_l1 = max_l1
        self._cache_dir = Path(cache_dir or os.path.join(tempfile.gettempdir(), "pimd_cache"))
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._hits = 0
        self._misses = 0

        # L3 Redis (optional)
        self._redis = None
        self._redis_available = False
        try:
            from pimd.caching.redis_cache import RedisCacheBackend, redis_available
            if redis_available:
                self._redis = RedisCacheBackend()
                self._redis_available = True
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._l1.get(key)
            if entry is not None and not entry.expired:
                entry.access_count += 1
                self._hits += 1
                return entry.data
            if entry is not None and entry.expired:
                self._l1.pop(key, None)

        # L2 disk
        disk_val = self._read_disk(key)
        if disk_val is not None:
            with self._lock:
                self._l1[key] = CacheEntry(key=key, data=disk_val)
                self._hits += 1
            return disk_val

        # L3 Redis
        if self._redis_available:
            try:
                val = self._redis.get(key)
                if val is not None:
                    with self._lock:
                        self._l1[key] = CacheEntry(key=key, data=val)
                        self._hits += 1
                    return val
            except Exception:
                pass

        with self._lock:
            self._misses += 1
        return None

    def set(self, key: str, data: Any, ttl: float = 0.0) -> None:
        with self._lock:
            self._l1[key] = CacheEntry(key=key, data=data, ttl=ttl)
            self._evict_l1()

        self._write_disk(key, data)

        if self._redis_available:
            try:
                self._redis.set(key, data, ttl=ttl)
            except Exception:
                pass

    def clear(self) -> None:
        with self._lock:
            self._l1.clear()
        self._clear_disk()
        if self._redis_available:
            try:
                self._redis.clear()
            except Exception:
                pass

    def remove(self, key: str) -> None:
        with self._lock:
            self._l1.pop(key, None)
        disk_path = self._disk_path(key)
        if disk_path.exists():
            disk_path.unlink(missing_ok=True)
        if self._redis_available:
            try:
                self._redis.remove(key)
            except Exception:
                pass

    def stats(self) -> UnifiedCacheStats:
        with self._lock:
            return UnifiedCacheStats(
                l1_entries=len(self._l1),
                l2_entries=len(list(self._cache_dir.glob("*.json"))),
                l3_available=self._redis_available,
                l3_entries=self._redis_available and 0 or 0,
                hits=self._hits,
                misses=self._misses,
                size_bytes=sum(p.stat().st_size for p in self._cache_dir.glob("*.json") if p.is_file()),
            )

    def make_key(self, *parts: str) -> str:
        h = hashlib.sha256()
        for p in parts:
            h.update(p.encode("utf-8"))
        return f"pimd:{h.hexdigest()[:32]}"

    # ------------------------------------------------------------------
    # L1 eviction
    # ------------------------------------------------------------------

    def _evict_l1(self) -> None:
        while len(self._l1) > self._max_l1:
            oldest = min(self._l1.keys(), key=lambda k: self._l1[k].access_count)
            self._l1.pop(oldest, None)

    # ------------------------------------------------------------------
    # L2 disk helpers
    # ------------------------------------------------------------------

    def _disk_path(self, key: str) -> Path:
        safe = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self._cache_dir / f"{safe}.json"

    def _write_disk(self, key: str, data: Any) -> None:
        try:
            payload = {"key": key, "data": data}
            self._disk_path(key).write_text(json.dumps(payload, default=str), encoding="utf-8")
        except Exception:
            pass

    def _read_disk(self, key: str) -> Any | None:
        try:
            path = self._disk_path(key)
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                return payload.get("data")
        except Exception:
            pass
        return None

    def _clear_disk(self) -> None:
        for p in self._cache_dir.glob("*.json"):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass


_GLOBAL_UNIFIED_CACHE: UnifiedCacheManager | None = None


def get_cache() -> UnifiedCacheManager:
    global _GLOBAL_UNIFIED_CACHE
    if _GLOBAL_UNIFIED_CACHE is None:
        _GLOBAL_UNIFIED_CACHE = UnifiedCacheManager()
    return _GLOBAL_UNIFIED_CACHE


def reset_cache() -> None:
    global _GLOBAL_UNIFIED_CACHE
    _GLOBAL_UNIFIED_CACHE = None
