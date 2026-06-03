"""Optional Redis cache backend with graceful fallback when Redis is unavailable."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from pimd.caching import CacheBackend

logger = logging.getLogger("pimd.redis")

_REDIS_AVAILABLE: bool = False
_redis_module = None

try:
    import redis as _redis_module

    _REDIS_AVAILABLE = True
except ImportError:
    _redis_module = None
    _REDIS_AVAILABLE = False


def redis_available() -> bool:
    return _REDIS_AVAILABLE


def _get_redis_url() -> str:
    return os.environ.get("PIMD_REDIS_URL", "redis://localhost:6379/0")


class RedisCacheBackend(CacheBackend):
    """Redis-based cache backend.

    Gracefully falls back to a no-op cache if Redis is unavailable
    or the connection fails.
    """

    def __init__(
        self,
        url: str | None = None,
        prefix: str = "pimd:",
        ttl: int = 7200,
    ) -> None:
        self.prefix = prefix
        self.ttl = ttl
        self._client: Any = None
        self._available = False
        self._connect(url or _get_redis_url())

    def _connect(self, url: str) -> None:
        if not _REDIS_AVAILABLE:
            logger.info("Redis package not installed; using no-op cache")
            return
        try:
            self._client = _redis_module.Redis.from_url(
                url, decode_responses=True, socket_timeout=2
            )
            self._client.ping()
            self._available = True
            logger.info("Connected to Redis at %s", url)
        except Exception as exc:
            self._available = False
            logger.warning("Redis connection failed (%s); using no-op cache", exc)

    def get(self, key: str) -> Any | None:
        if not self._available or self._client is None:
            return None
        try:
            val = self._client.get(self.prefix + key)
            if val is not None:
                return json.loads(val)
            return None
        except Exception:
            return None

    def set(self, key: str, value: Any) -> None:
        if not self._available or self._client is None:
            return
        try:
            self._client.setex(self.prefix + key, self.ttl, json.dumps(value))
        except Exception:
            pass

    def delete(self, key: str) -> None:
        if not self._available or self._client is None:
            return
        try:
            self._client.delete(self.prefix + key)
        except Exception:
            pass

    def clear(self) -> None:
        if not self._available or self._client is None:
            return
        try:
            for k in self._client.scan_iter(match=self.prefix + "*"):
                self._client.delete(k)
        except Exception:
            pass

    def is_available(self) -> bool:
        return self._available

    def health_check(self) -> dict[str, Any]:
        if not self._available:
            return {"available": False, "reason": "Not connected"}
        try:
            self._client.ping()
            return {
                "available": True,
                "ping_ms": self._client.ping(),
                "info": self._client.info().get("redis_version", "unknown"),
            }
        except Exception as exc:
            return {"available": False, "reason": str(exc)}

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "available": self._available,
            "backend": "redis",
            "prefix": self.prefix,
            "ttl": self.ttl,
        }


class RedisDiagramCache(RedisCacheBackend):
    """Redis-backed diagram cache."""

    def __init__(self, url: str | None = None, ttl: int = 86400) -> None:
        super().__init__(url=url, prefix="pimd:diagram:", ttl=ttl)


class RedisEquationCache(RedisCacheBackend):
    """Redis-backed equation cache."""

    def __init__(self, url: str | None = None, ttl: int = 86400) -> None:
        super().__init__(url=url, prefix="pimd:equation:", ttl=ttl)


def create_redis_cache(
    backend: str = "default", url: str | None = None
) -> RedisCacheBackend | None:
    """Factory: create a Redis cache backend if available."""
    if not _REDIS_AVAILABLE:
        return None
    try:
        return RedisCacheBackend(url=url)
    except Exception:
        return None
