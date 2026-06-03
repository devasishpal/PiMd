"""Filesystem-backed cache with JSON serialization and TTL."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from pimd.caching.base import CacheBackend


class FileSystemCache(CacheBackend):
    """Cache backend that stores entries as JSON files on disk.

    Each cached entry is serialised to a JSON envelope file named by the
    SHA-256 hash of the cache key.  TTL is stored inside the envelope so
    that per-entry TTLs are supported.

    Usage::

        cache = FileSystemCache(directory="~/.pimd/cache", default_ttl=3600)
        cache.set("key", {"data": 42})
        value = cache.get("key")
    """

    def __init__(
        self,
        directory: str | None = None,
        default_ttl: int = 3600,
    ) -> None:
        self._directory = Path(os.path.expanduser(directory or "~/.pimd/cache"))
        self._default_ttl = default_ttl
        self.hit_count: int = 0
        self.miss_count: int = 0
        self.set_count: int = 0
        self._directory.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    def _path_for(self, key: str) -> Path:
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._directory / h

    def _is_expired(self, path: Path) -> bool:
        try:
            raw = path.read_text(encoding="utf-8")
            envelope = json.loads(raw)
            expires_at = envelope.get("_expires_at")
            if expires_at is None:
                return False
            return time.time() > expires_at
        except Exception:
            return True

    def _read_envelope(self, path: Path) -> dict | None:
        try:
            raw = path.read_text(encoding="utf-8")
            return json.loads(raw)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # CacheBackend interface
    # ------------------------------------------------------------------
    def get(self, key: str) -> Any | None:
        path = self._path_for(key)
        if not path.exists():
            self.miss_count += 1
            return None
        envelope = self._read_envelope(path)
        if envelope is None:
            self.miss_count += 1
            return None
        expires_at = envelope.get("_expires_at")
        if expires_at is not None and time.time() > expires_at:
            path.unlink(missing_ok=True)
            self.miss_count += 1
            return None
        self.hit_count += 1
        return envelope.get("_value")

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        path = self._path_for(key)
        effective_ttl = ttl if ttl is not None else self._default_ttl
        if effective_ttl > 0:
            expires_at = time.time() + effective_ttl
        else:
            expires_at = -1.0
        envelope = {"_expires_at": expires_at, "_value": value}
        try:
            data = json.dumps(envelope, ensure_ascii=False, default=str)
            path.write_text(data, encoding="utf-8")
            self.set_count += 1
        except Exception:
            pass

    def delete(self, key: str) -> None:
        path = self._path_for(key)
        path.unlink(missing_ok=True)

    def clear(self) -> None:
        for child in self._directory.iterdir():
            if child.is_file():
                child.unlink(missing_ok=True)
        self.hit_count = 0
        self.miss_count = 0
        self.set_count = 0

    # ------------------------------------------------------------------
    # Extra helpers
    # ------------------------------------------------------------------
    def keys(self) -> list[str]:
        valid: list[str] = []
        for child in self._directory.iterdir():
            if not child.is_file():
                continue
            if self._is_expired(child):
                child.unlink(missing_ok=True)
                continue
            valid.append(child.name)
        return valid

    @property
    def size(self) -> int:
        return len([p for p in self._directory.iterdir() if p.is_file()])

    def __len__(self) -> int:
        return self.size

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def info(self) -> dict:
        return {
            "hits": self.hit_count,
            "misses": self.miss_count,
            "sets": self.set_count,
            "size": self.size,
            "directory": str(self._directory),
            "default_ttl": self._default_ttl,
            "backend_type": type(self).__name__,
        }

    def _estimate_memory(self) -> int:
        total = 0
        for child in self._directory.iterdir():
            if child.is_file():
                try:
                    total += child.stat().st_size
                except OSError:
                    pass
        return total


__all__ = [
    "FileSystemCache",
]
