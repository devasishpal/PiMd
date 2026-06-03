# PiMD Redis Guide

## Overview

Redis is an **optional** dependency that provides distributed caching for PiMD conversions. When Redis is unavailable, PiMD gracefully falls back to in-memory caching.

## Installation

No special installation is needed. Redis support is auto-detected:

```bash
pip install redis
```

Or with PiMD extras:

```bash
pip install pimd[redis]
```

## Configuration

### Environment Variable

```bash
export PIMD_REDIS_URL="redis://:password@host:6379/0"
```

### Programmatic

```python
from pimd.caching.redis_cache import RedisCacheBackend, RedisEquationCache, RedisDiagramCache

# General cache
cache = RedisCacheBackend(url="redis://localhost:6379/0", prefix="pimd:", ttl=7200)

# Specialized caches
eq_cache = RedisEquationCache(url="redis://localhost:6379/0", ttl=86400)
diag_cache = RedisDiagramCache(url="redis://localhost:6379/0", ttl=86400)
```

### In Config File

```toml
[cache]
backend = "redis"
redis_url = "redis://localhost:6379/0"
```

## Graceful Fallback

Redis is never required. If:
- The `redis` package is not installed → memory caching
- The connection fails → memory caching
- A command times out → returns None (cache miss)

```python
from pimd.caching.redis_cache import redis_available

if redis_available():
    # Redis is installed and connected
    pass
else:
    # Using memory cache fallback
    pass
```

## Cache Types

| Cache | Prefix | Default TTL | Purpose |
|-------|--------|-------------|---------|
| `RedisCacheBackend` | `pimd:` | 7200s | General conversion cache |
| `RedisEquationCache` | `pimd:equation:` | 86400s | Rendered equations |
| `RedisDiagramCache` | `pimd:diagram:` | 86400s | Rendered diagrams |

## Health Check

```python
from pimd.caching.redis_cache import RedisCacheBackend

cache = RedisCacheBackend()
status = cache.health_check()
print(status)
# {'available': True, 'ping_ms': True, 'info': '7.2.0'}
```

## When to Use Redis

- **CI/CD pipelines**: Share caches across builds
- **Multi-server deployments**: Centralized cache
- **Large teams**: Avoid redundant rendering of equations/diagrams
- **Long TTL caches**: Equations and diagrams rarely change

## When NOT to Use Redis

- Single-user local development
- One-off conversions
- Memory cache is sufficient (< 1000 unique equations/diagrams)
