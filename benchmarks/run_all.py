#!/usr/bin/env python
"""Run all PiMD benchmarks and generate a summary report.

Usage:
    py benchmarks/run_all.py
    py benchmarks/run_all.py --json
    py benchmarks/run_all.py --json --output report.json
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path when run as a script
if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import argparse
import json
import sys
import time
from typing import Any

# Benchmarks — each module exposes a `run()` that returns list[dict]
_BENCHMARKS = [
    ("bench_parsing", "Parsing"),
    ("bench_conversion", "Conversion"),
    ("bench_diagrams", "Diagrams"),
]

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _import_bench(name: str):
    """Dynamically import a benchmark module by name."""
    return __import__(f"benchmarks.{name}", fromlist=["run"])


def run_all(verbose: bool = True) -> dict[str, Any]:
    """Execute every benchmark and return aggregated results."""
    report: dict[str, Any] = {
        "metadata": {
            "pimd_version": _get_pimd_version(),
            "python_version": sys.version,
            "platform": sys.platform,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "benchmarks": {},
    }

    for mod_name, label in _BENCHMARKS:
        if verbose:
            print()

        try:
            mod = _import_bench(mod_name)
        except ImportError as exc:
            report["benchmarks"][mod_name] = {"error": str(exc), "results": []}
            if verbose:
                print(f"  [{label}] SKIPPED — {exc}")
            continue

        try:
            results = mod.run()
            report["benchmarks"][mod_name] = {"results": results}
        except Exception as exc:
            report["benchmarks"][mod_name] = {"error": str(exc), "results": []}
            if verbose:
                print(f"  [{label}] ERROR — {exc}")

    return report


def _get_pimd_version() -> str:
    try:
        from pimd import __version__  # type: ignore
        return __version__
    except (ImportError, AttributeError):
        try:
            from importlib.metadata import version
            return version("pimd")
        except Exception:
            return "unknown"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(report: dict[str, Any]) -> None:
    """Print a human-readable summary of all benchmark results."""
    print()
    print("=" * 60)
    print("  PiMD Benchmark Summary")
    print("=" * 60)
    meta = report["metadata"]
    print(f"  Version:   {meta['pimd_version']}")
    print(f"  Python:    {meta['python_version'].split()[0]}")
    print(f"  Platform:  {meta['platform']}")
    print(f"  Timestamp: {meta['timestamp']}")
    print()

    for mod_name, bench in report["benchmarks"].items():
        label = dict(_BENCHMARKS).get(mod_name, mod_name)
        err = bench.get("error")
        results = bench.get("results", [])

        if err:
            print(f"  [{label}] ERROR: {err}")
            continue
        if not results:
            print(f"  [{label}] No results")

        if results:
            print(f"  [{label}]")
            # Pick a meaningful subset of keys
            if "throughput_mbps" in results[0]:
                max_tp = max(r.get("throughput_mbps", 0) or 0 for r in results)
                max_sz = results[-1].get("size", "")
                print(f"    Max throughput:   {max_tp:.2f} MB/s  ({max_sz})")
            if "total_s" in results[0]:
                total = sum(r.get("total_s", 0) or 0 for r in results)
                print(f"    Total time:       {total:.4f}s")
            if "time_s" in results[0]:
                times = [r.get("time_s", 0) or 0 for r in results]
                avg = sum(times) / len(times) if times else 0
                print(f"    Fastest:          {min(times):.4f}s")
                print(f"    Slowest:          {max(times):.4f}s")
                print(f"    Average:          {avg:.4f}s")
        print()


def _get_label(mod_name: str) -> str:
    return dict(_BENCHMARKS).get(mod_name, mod_name)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PiMD benchmarks")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--output", default="", help="Write report to file")
    args = parser.parse_args()

    report = run_all(verbose=not args.json)

    if args.json or args.output:
        json_str = json.dumps(report, indent=2, default=str)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_str)
            print(f"Report written to {args.output}")
        if args.json:
            print(json_str)
    else:
        print_summary(report)


if __name__ == "__main__":
    main()
