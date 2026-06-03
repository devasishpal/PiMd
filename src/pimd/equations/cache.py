"""Equation cache — avoid re-rendering the same equation twice."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from pimd.equations.models import EquationResult


class EquationCache:
    """Abstract cache for rendered equations."""

    def get(self, key: str) -> EquationResult | None:
        raise NotImplementedError

    def set(self, key: str, result: EquationResult, ttl: int | None = None) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    @staticmethod
    def make_key(latex: str, display: bool = False, **extra: Any) -> str:
        hasher = hashlib.sha256()
        hasher.update(latex.encode("utf-8"))
        hasher.update(b":display" if display else b":inline")
        for k, v in sorted(extra.items()):
            hasher.update(str(k).encode())
            hasher.update(str(v).encode())
        return f"eq:{hasher.hexdigest()[:32]}"


class MemoryEquationCache(EquationCache):
    """In-memory equation cache with TTL."""

    def __init__(self, default_ttl: int = 7200) -> None:
        self._default_ttl = default_ttl
        self._store: dict[str, tuple[EquationResult, float]] = {}

    def get(self, key: str) -> EquationResult | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        result, expires = entry
        if expires > 0 and time.monotonic() > expires:
            del self._store[key]
            return None
        return result

    def set(self, key: str, result: EquationResult, ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires = time.monotonic() + effective_ttl if effective_ttl > 0 else 0
        self._store[key] = (result, expires)

    def clear(self) -> None:
        self._store.clear()

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
