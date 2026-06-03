"""Benchmark diagram rendering for each available renderer."""

from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from typing import Any

from benchmarks.conftest import format_benchmark_results, timer

try:
    from pimd.diagrams import DiagramEngine, DiagramRegistry
    from pimd.diagrams.renderers import (
        AsciiRenderer,
        D2Renderer,
        GraphvizRenderer,
        MermaidRenderer,
        PlantUMLRenderer,
        SvgRenderer,
    )

    HAS_PIMD = True
except ImportError:
    DiagramEngine = None  # type: ignore
    DiagramRegistry = None  # type: ignore
    HAS_PIMD = False

# Sample diagrams for each language
SAMPLE_DIAGRAMS: dict[str, str] = {
    "mermaid": """graph TD
    A[Start] --> B{Is it?}
    B -- Yes --> C[OK]
    C --> D[Rethink]
    D --> B
    B -- No ----> E[End]
""",
    "plantuml": """@startuml
Alice -> Bob: Authentication Request
Bob --> Alice: Authentication Response
Alice -> Bob: Another authentication Request
Alice <-- Bob: another response
@enduml
""",
    "dot": """digraph G {
    rankdir=LR;
    A -> B -> C;
    B -> D;
}
""",
    "d2": """x -> y -> z
x -> z
""",
    "ascii": """+-------+     +-------+
|  A    | --> |  B    |
+-------+     +-------+
""",
    "svg": """<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="40" stroke="green" stroke-width="4" fill="yellow" />
</svg>
""",
}


def _build_engine() -> DiagramEngine | None:
    """Build a DiagramEngine with all available renderers."""
    registry = DiagramRegistry()
    for renderer_cls in (
        MermaidRenderer,
        PlantUMLRenderer,
        GraphvizRenderer,
        D2Renderer,
        AsciiRenderer,
        SvgRenderer,
    ):
        r = renderer_cls()
        if r.is_available():
            registry.register(r)
    if len(registry) == 0:
        return None
    return DiagramEngine(registry=registry)


def bench_renderer(engine: DiagramEngine, language: str, source: str) -> dict[str, Any]:
    """Render a single diagram and return timing results."""
    with timer() as t:
        result = engine.render(source, language)
    return {
        "language": language,
        "available": "OK" if result.success else "FAIL",
        "time_s": round(t[0], 4),
        "png_size": len(result.png) if result.png else 0,
        "error": result.error or "",
    }


def run() -> list[dict[str, Any]]:
    """Run all diagram benchmarks and print results."""
    if not HAS_PIMD:
        print("Skipping bench_diagrams — pimd not available")
        return []

    engine = _build_engine()
    if engine is None:
        print("No diagram renderers available — skipping bench_diagrams")
        return []

    print("=" * 60)
    print("  Diagram Rendering Benchmark")
    print("=" * 60)

    results: list[dict[str, Any]] = []
    for language, source in SAMPLE_DIAGRAMS.items():
        row = bench_renderer(engine, language, source)
        results.append(row)
        status = row["available"]
        print(f"  {language:>12s} … {status:4s}  {row['time_s']:.4f}s  png:{row['png_size']} bytes")

    print()
    table = format_benchmark_results(
        results,
        key_order=["language", "available", "time_s", "png_size", "error"],
    )
    print(table)
    print()

    return results


if __name__ == "__main__":
    run()
