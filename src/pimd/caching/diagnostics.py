"""Cache diagnostics utilities."""

from __future__ import annotations

from pimd.caching.base import CacheBackend


def diagnose_cache(backend: CacheBackend) -> dict:
    """Run a set of diagnostic checks against *backend* and return results.

    Performs the following checks:

    * **basic-io** — set a value, read it back, delete it
    * **ttl-expiry** — set with ``ttl=0`` and verify it returns ``None``
    * **overwrite** — set twice with same key, verify latest value wins
    * **clear** — set two keys, clear, verify store is empty
    """
    results: dict[str, dict] = {}

    # basic-io
    try:
        backend.set("__diag_key__", "diagnostic-value")
        val = backend.get("__diag_key__")
        backend.delete("__diag_key__")
        passed = val == "diagnostic-value"
        results["basic-io"] = {"passed": passed, "detail": None if passed else repr(val)}
    except Exception as exc:
        results["basic-io"] = {"passed": False, "detail": str(exc)}

    # ttl-expiry
    try:
        backend.set("__diag_ttl__", "expire-me", ttl=0)
        val = backend.get("__diag_ttl__")
        passed = val is None
        results["ttl-expiry"] = {"passed": passed, "detail": None if passed else repr(val)}
    except Exception as exc:
        results["ttl-expiry"] = {"passed": False, "detail": str(exc)}

    # overwrite
    try:
        backend.set("__diag_over__", "first")
        backend.set("__diag_over__", "second")
        val = backend.get("__diag_over__")
        backend.delete("__diag_over__")
        passed = val == "second"
        results["overwrite"] = {"passed": passed, "detail": None if passed else repr(val)}
    except Exception as exc:
        results["overwrite"] = {"passed": False, "detail": str(exc)}

    # clear
    try:
        backend.set("__diag_a__", 1)
        backend.set("__diag_b__", 2)
        backend.clear()
        a = backend.get("__diag_a__")
        b = backend.get("__diag_b__")
        passed = a is None and b is None
        results["clear"] = {"passed": passed, "detail": None if passed else f"a={a!r}, b={b!r}"}
    except Exception as exc:
        results["clear"] = {"passed": False, "detail": str(exc)}

    # Basic info
    try:
        info = backend.info()
        results["info"] = {"passed": True, "detail": info}
    except Exception as exc:
        results["info"] = {"passed": False, "detail": str(exc)}

    all_passed = all(v["passed"] for v in results.values())
    return {
        "all_passed": all_passed,
        "checks": results,
    }


def format_cache_info(info: dict) -> str:
    """Format a cache *info* dict into a human-readable string."""
    lines: list[str] = []
    lines.append(f"  Backend type:  {info.get('backend_type', 'unknown')}")
    lines.append(f"  Hits:           {info.get('hits', 0)}")
    lines.append(f"  Misses:         {info.get('misses', 0)}")
    lines.append(f"  Sets:           {info.get('sets', 0)}")
    lines.append(f"  Size (entries): {info.get('size', 0)}")

    # MemoryCache
    if "default_ttl" in info:
        lines.append(f"  Default TTL:    {info['default_ttl']}s")
    # FileSystemCache extras
    if "directory" in info:
        lines.append(f"  Directory:      {info['directory']}")
    if "default_ttl" in info:
        lines.append(f"  Default TTL:    {info['default_ttl']}s")

    total = info.get("hits", 0) + info.get("misses", 0)
    hit_rate = info["hits"] / total if total > 0 else 0.0
    lines.append(f"  Hit rate:       {hit_rate:.1%}")

    return "\n".join(lines)


__all__ = [
    "diagnose_cache",
    "format_cache_info",
]
