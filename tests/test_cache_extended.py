"""Extended tests for the PiMD caching framework."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pimd.caching.base import CacheBackend, CacheStats
from pimd.caching.diagnostics import diagnose_cache, format_cache_info
from pimd.caching.filesystem import FileSystemCache
from pimd.caching.memory import MemoryCache
from pimd.caching.metrics import CacheMetricsCollector


class TestFileSystemCache:
    def test_set_and_get(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_returns_none(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        assert cache.get("nonexistent") is None

    def test_get_expired_entry_returns_none(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.set("expire-key", "data", ttl=0)
        assert cache.get("expire-key") is None

    def test_delete_removes_entry(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.set("del-key", "value")
        assert cache.get("del-key") == "value"
        cache.delete("del-key")
        assert cache.get("del-key") is None

    def test_delete_nonexistent_does_not_raise(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.delete("does-not-exist")

    def test_clear_removes_all(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.size >= 2
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.size == 0

    def test_clear_resets_counters(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.get("x")
        cache.set("y", 1)
        cache.get("y")
        assert cache.hit_count > 0 or cache.miss_count > 0
        cache.clear()
        assert cache.hit_count == 0
        assert cache.miss_count == 0
        assert cache.set_count == 0

    def test_keys_returns_valid_keys(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.set("k1", 1)
        cache.set("k2", 2)
        keys = cache.keys()
        assert len(keys) == 2

    def test_keys_excludes_expired(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.set("good", "val")
        cache.set("bad", "val", ttl=0)
        keys = cache.keys()
        assert len(keys) == 1

    def test_len(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        assert len(cache) == 0
        cache.set("a", 1)
        assert len(cache) == 1

    def test_contains(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.set("present", "x")
        assert "present" in cache
        assert "missing" not in cache

    def test_info_returns_expected_keys(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        info = cache.info()
        assert "hits" in info
        assert "misses" in info
        assert "sets" in info
        assert "size" in info
        assert "directory" in info
        assert "default_ttl" in info
        assert "backend_type" in info
        assert info["backend_type"] == "FileSystemCache"

    def test_info_counts(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.set("x", 1)
        cache.get("x")
        cache.get("missing")
        info = cache.info()
        assert info["sets"] == 1
        assert info["hits"] == 1
        assert info["misses"] == 1

    def test_stats_dataclass(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.set("a", 1)
        cache.get("a")
        cache.get("miss")
        stats = cache.stats
        assert isinstance(stats, CacheStats)
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.sets == 1
        assert stats.backend_type == "FileSystemCache"
        assert 0 < stats.hit_rate < 1

    def test_default_ttl_applied(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path), default_ttl=999)
        assert cache._default_ttl == 999

    def test_set_with_custom_ttl(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        cache.set("custom-ttl", "val", ttl=9999)
        assert cache.get("custom-ttl") == "val"


class TestFileSystemCacheDirectoryCreation:
    def test_creates_directory(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "new-cache-dir"
        assert not cache_dir.exists()
        FileSystemCache(directory=str(cache_dir))
        assert cache_dir.exists()

    def test_make_key_format(self) -> None:
        cache = FileSystemCache(directory="~/.pimd/cache")
        key = cache.make_key("a", "b", c="d")
        assert "a:b" in key
        assert "c=d" in key


class TestMemoryCache:
    def test_set_and_get(self) -> None:
        cache = MemoryCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_get_missing_returns_none(self) -> None:
        cache = MemoryCache()
        assert cache.get("nonexistent") is None

    def test_get_expired_entry_returns_none(self) -> None:
        cache = MemoryCache()
        cache.set("exp-key", "data", ttl=0)
        assert cache.get("exp-key") is None

    def test_delete(self) -> None:
        cache = MemoryCache()
        cache.set("del-me", "val")
        cache.delete("del-me")
        assert cache.get("del-me") is None

    def test_clear(self) -> None:
        cache = MemoryCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.size == 0

    def test_hit_count_tracking(self) -> None:
        cache = MemoryCache()
        cache.set("x", 1)
        cache.get("x")
        cache.get("x")
        assert cache.hit_count == 2

    def test_miss_count_tracking(self) -> None:
        cache = MemoryCache()
        cache.get("miss1")
        cache.get("miss2")
        assert cache.miss_count == 2

    def test_set_count_tracking(self) -> None:
        cache = MemoryCache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.set_count == 2

    def test_keys(self) -> None:
        cache = MemoryCache()
        cache.set("k1", 1)
        cache.set("k2", 2)
        keys = cache.keys()
        assert len(keys) == 2
        assert "k1" in keys
        assert "k2" in keys

    def test_len(self) -> None:
        cache = MemoryCache()
        assert len(cache) == 0
        cache.set("a", 1)
        assert len(cache) == 1

    def test_contains(self) -> None:
        cache = MemoryCache()
        cache.set("yes", "val")
        assert "yes" in cache
        assert "no" not in cache

    def test_info(self) -> None:
        cache = MemoryCache()
        info = cache.info()
        assert info["backend_type"] == "MemoryCache"
        assert "hits" in info
        assert "misses" in info
        assert "sets" in info
        assert "size" in info

    def test_stats(self) -> None:
        cache = MemoryCache()
        cache.set("a", 1)
        cache.get("a")
        cache.get("miss")
        stats = cache.stats
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.backend_type == "MemoryCache"


class TestCacheMetricsCollector:
    def test_record_hit(self) -> None:
        collector = CacheMetricsCollector()
        collector.record_hit("memory", "key1")
        collector.record_hit("memory", "key1")
        report = collector.report()
        assert report["per_backend"]["memory"]["hits"] == 2

    def test_record_miss(self) -> None:
        collector = CacheMetricsCollector()
        collector.record_miss("redis", "rkey")
        report = collector.report()
        assert report["per_backend"]["redis"]["misses"] == 1

    def test_record_set(self) -> None:
        collector = CacheMetricsCollector()
        collector.record_set("fs", "fkey")
        report = collector.report()
        assert report["per_backend"]["fs"]["sets"] == 1

    def test_report_overall_counts(self) -> None:
        collector = CacheMetricsCollector()
        collector.record_hit("a", "k1")
        collector.record_miss("a", "k2")
        collector.record_set("a", "k3")
        report = collector.report()
        overall = report["overall"]
        assert overall["hits"] == 1
        assert overall["misses"] == 1
        assert overall["sets"] == 1
        assert overall["total_ops"] == 3
        assert overall["hit_rate"] == 0.5

    def test_report_multiple_backends(self) -> None:
        collector = CacheMetricsCollector()
        collector.record_hit("mem", "k")
        collector.record_hit("fs", "k")
        collector.record_miss("mem", "k2")
        report = collector.report()
        assert set(report["per_backend"].keys()) == {"fs", "mem"}

    def test_report_uptime(self) -> None:
        collector = CacheMetricsCollector()
        report = collector.report()
        assert report["overall"]["uptime_seconds"] >= 0
        assert "start_time" in report["overall"]

    def test_clear_resets(self) -> None:
        collector = CacheMetricsCollector()
        collector.record_hit("mem", "k")
        collector.clear()
        report = collector.report()
        assert report["overall"]["hits"] == 0
        assert report["overall"]["misses"] == 0

    def test_empty_report(self) -> None:
        collector = CacheMetricsCollector()
        report = collector.report()
        assert report["overall"]["total_ops"] == 0
        assert report["per_backend"] == {}
        assert report["overall"]["hit_rate"] == 0.0


class TestDiagnoseCache:
    def test_diagnose_filesystem_cache(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        result = diagnose_cache(cache)
        assert isinstance(result, dict)
        assert "all_passed" in result
        assert "checks" in result
        assert result["all_passed"] is True

    def test_diagnose_memory_cache(self) -> None:
        cache = MemoryCache()
        result = diagnose_cache(cache)
        assert result["all_passed"] is True

    def test_diagnose_basic_io(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        result = diagnose_cache(cache)
        assert result["checks"]["basic-io"]["passed"] is True

    def test_diagnose_ttl_expiry(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        result = diagnose_cache(cache)
        assert result["checks"]["ttl-expiry"]["passed"] is True

    def test_diagnose_overwrite(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        result = diagnose_cache(cache)
        assert result["checks"]["overwrite"]["passed"] is True

    def test_diagnose_clear(self, tmp_path: Path) -> None:
        cache = FileSystemCache(directory=str(tmp_path))
        result = diagnose_cache(cache)
        assert result["checks"]["clear"]["passed"] is True


class TestFormatCacheInfo:
    def test_format_info_includes_key_fields(self) -> None:
        info = {
            "backend_type": "MemoryCache",
            "hits": 10,
            "misses": 2,
            "sets": 5,
            "size": 3,
            "backend": "memory",
        }
        output = format_cache_info(info)
        assert "MemoryCache" in output
        assert "10" in output
        assert "2" in output
        assert "5" in output
        assert "3" in output

    def test_format_info_with_directory(self) -> None:
        info = {
            "backend_type": "FileSystemCache",
            "hits": 1,
            "misses": 1,
            "sets": 1,
            "size": 1,
            "directory": "/tmp/cache",
            "default_ttl": 3600,
        }
        output = format_cache_info(info)
        assert "/tmp/cache" in output
        assert "3600s" in output
        assert "50.0%" in output or "50%" in output

    def test_format_info_empty_hits(self) -> None:
        info = {
            "backend_type": "MemoryCache",
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "size": 0,
        }
        output = format_cache_info(info)
        assert "0.0%" in output


class TestCacheBackend:
    def test_make_key_with_parts(self) -> None:
        class DummyBackend(CacheBackend):
            def get(self, key: str) -> Any:
                return None
            def set(self, key: str, value: Any, ttl: int | None = None) -> None:
                pass
            def delete(self, key: str) -> None:
                pass
            def clear(self) -> None:
                pass

        backend = DummyBackend()
        key = backend.make_key("diagram", "mermaid", fmt="svg")
        assert "diagram:mermaid" in key
        assert "fmt=svg" in key

    def test_info_defaults(self) -> None:
        class DummyBackend(CacheBackend):
            def get(self, key: str) -> Any:
                return None
            def set(self, key: str, value: Any, ttl: int | None = None) -> None:
                pass
            def delete(self, key: str) -> None:
                pass
            def clear(self) -> None:
                pass

        backend = DummyBackend()
        info = backend.info()
        assert info["hits"] == 0
        assert info["misses"] == 0
        assert info["sets"] == 0
        assert "backend_type" in info

    def test_stats_zero_division(self) -> None:
        class DummyBackend(CacheBackend):
            def get(self, key: str) -> Any:
                return None
            def set(self, key: str, value: Any, ttl: int | None = None) -> None:
                pass
            def delete(self, key: str) -> None:
                pass
            def clear(self) -> None:
                pass

        backend = DummyBackend()
        stats = backend.stats
        assert stats.hit_rate == 0.0
