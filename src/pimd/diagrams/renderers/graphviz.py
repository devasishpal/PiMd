"""Graphviz renderer — uses the ``dot`` CLI tool."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pimd.diagrams.models import DiagramResult
from pimd.diagrams.renderers.base import DiagramRenderer


class GraphvizRenderer(DiagramRenderer):
    """Render Graphviz DOT diagrams using the ``dot`` CLI.

    Requires Graphviz (https://graphviz.org) installed on the system.
    """

    language = "dot"
    name = "Graphviz"
    version = "1.0.0"
    description = "Render Graphviz DOT diagrams (digraph, graph)"
    priority = 30

    def is_available(self) -> bool:
        return self._which("dot")

    def render(self, source: str, **options: Any) -> DiagramResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.dot"
            svg_path = Path(tmpdir) / "output.svg"
            png_path = Path(tmpdir) / "output.png"

            content = source.strip()
            if not content.startswith("digraph") and not content.startswith("graph"):
                content = f"digraph {{\n{source}\n}}"
            input_path.write_text(content, encoding="utf-8")

            # SVG
            subprocess.run(
                ["dot", "-Tsvg", str(input_path), "-o", str(svg_path)],
                check=True,
                capture_output=True,
                timeout=30,
            )
            svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None

            # PNG
            png: bytes | None = None
            try:
                subprocess.run(
                    ["dot", "-Tpng", str(input_path), "-o", str(png_path)],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                png = png_path.read_bytes() if png_path.exists() else None
            except Exception:
                pass

            return DiagramResult(
                source=source,
                language=self.language,
                svg=svg,
                png=png,
            )
