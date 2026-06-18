"""Tests for pimd.caching.unified — UnifiedCacheManager."""

from __future__ import annotations

from pimd.caching.unified import UnifiedCacheManager, get_cache, reset_cache


class TestUnifiedCache:
    def setup_method(self) -> None:
        reset_cache()

    def test_get_set(self) -> None:
        cache = UnifiedCacheManager()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self) -> None:
        cache = UnifiedCacheManager()
        assert cache.get("nonexistent") is None

    def test_remove(self) -> None:
        cache = UnifiedCacheManager()
        cache.set("key2", "value2")
        cache.remove("key2")
        assert cache.get("key2") is None

    def test_clear(self) -> None:
        cache = UnifiedCacheManager()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_stats(self) -> None:
        cache = UnifiedCacheManager()
        stats = cache.stats()
        assert stats.hits == 0
        assert stats.misses == 0

        cache.set("x", "val")
        cache.get("x")
        stats = cache.stats()
        assert stats.hits >= 1
        assert stats.l1_entries >= 1

    def test_make_key(self) -> None:
        cache = UnifiedCacheManager()
        key = cache.make_key("prefix", "suffix", "123")
        assert key.startswith("pimd:")
        assert len(key) == 5 + 32

    def test_l1_ttl_expiry(self) -> None:
        import time

        cache = UnifiedCacheManager()
        cache.set("exp", "value", ttl=0.01)
        time.sleep(0.02)
        cached = cache._l1.get("exp")
        if cached is not None:
            assert cached.expired is True
        else:
            pass  # already evicted, which is also fine

    def test_global_cache(self) -> None:
        reset_cache()
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2

    def test_reset_cache(self) -> None:
        reset_cache()
        c1 = get_cache()
        reset_cache()
        c2 = get_cache()
        assert c1 is not c2

    def test_l1_eviction(self) -> None:
        cache = UnifiedCacheManager(max_l1=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)
        assert len(cache._l1) <= 3

    def test_disk_persistence(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = UnifiedCacheManager(cache_dir=tmpdir)
            cache.set("disk_test", "persisted")
            assert cache.get("disk_test") == "persisted"
