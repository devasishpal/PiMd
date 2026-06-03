"""Diagram caching — memory, filesystem, and Redis-ready architecture."""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pimd.diagrams.models import DiagramResult


class DiagramCache(ABC):
    """Abstract cache backend for rendered diagrams."""

    @abstractmethod
    def get(self, key: str) -> DiagramResult | None: ...

    @abstractmethod
    def set(self, key: str, result: DiagramResult, ttl: int | None = None) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @staticmethod
    def make_key(source: str, language: str, **extra: Any) -> str:
        """Generate a deterministic cache key from source and language."""
        hasher = hashlib.sha256()
        hasher.update(source.encode("utf-8"))
        hasher.update(language.encode("utf-8"))
        for k, v in sorted(extra.items()):
            hasher.update(str(k).encode())
            hasher.update(str(v).encode())
        return f"diagram:{language}:{hasher.hexdigest()[:32]}"


class MemoryDiagramCache(DiagramCache):
    """In-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 3600) -> None:
        self._default_ttl = default_ttl
        self._store: dict[str, tuple[DiagramResult, float]] = {}

    def get(self, key: str) -> DiagramResult | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        result, expires = entry
        if expires > 0 and time.monotonic() > expires:
            del self._store[key]
            return None
        return result

    def set(self, key: str, result: DiagramResult, ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires = time.monotonic() + effective_ttl if effective_ttl > 0 else 0
        self._store[key] = (result, expires)

    def clear(self) -> None:
        self._store.clear()

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


class FileSystemDiagramCache(DiagramCache):
    """Filesystem-based cache. Stores rendered PNG/SVG files."""

    def __init__(self, cache_dir: str | Path) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._metadata: dict[str, tuple[float, str]] = {}  # key -> (expires, format)

    def _path_for(self, key: str, ext: str) -> Path:
        return self._cache_dir / f"{key}.{ext}"

    def get(self, key: str) -> DiagramResult | None:
        meta = self._metadata.get(key)
        if meta is None:
            return None
        expires, fmt = meta
        if expires > 0 and time.time() > expires:
            self.delete(key)
            return None

        png_path = self._path_for(key, "png")
        svg_path = self._path_for(key, "svg")
        png = png_path.read_bytes() if png_path.exists() else None
        svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None
        if png is None and svg is None:
            return None
        return DiagramResult(source="", language=fmt, svg=svg, png=png, cached=True)

    def set(self, key: str, result: DiagramResult, ttl: int | None = None) -> None:
        expires = time.time() + ttl if ttl and ttl > 0 else 0
        if result.svg:
            self._path_for(key, "svg").write_text(result.svg, encoding="utf-8")
        if result.png:
            self._path_for(key, "png").write_bytes(result.png)
        self._metadata[key] = (expires, result.language)

    def clear(self) -> None:
        for f in self._cache_dir.glob("*"):
            f.unlink()
        self._metadata.clear()

    def delete(self, key: str) -> None:
        for ext in ("png", "svg"):
            p = self._path_for(key, ext)
            if p.exists():
                p.unlink()
        self._metadata.pop(key, None)
