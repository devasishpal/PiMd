"""Vega and Vega-Lite diagram renderers — uses vg2svg CLI tool."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pimd.diagrams.models import DiagramResult
from pimd.diagrams.renderers.base import DiagramRenderer


class _VegaBaseRenderer(DiagramRenderer):
    """Base class for Vega and Vega-Lite renderers."""

    language: str = ""
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    priority: int = 90
    _tool: str = ""

    def is_available(self) -> bool:
        return self._which(self._tool)

    def render(self, source: str, **options: Any) -> DiagramResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "spec.json"
            svg_path = Path(tmpdir) / "output.svg"
            png_path = Path(tmpdir) / "output.png"

            input_path.write_text(source, encoding="utf-8")

            try:
                subprocess.run(
                    [self._tool, str(input_path), str(svg_path)],
                    check=True, capture_output=True, timeout=60,
                )
            except subprocess.CalledProcessError as exc:
                return DiagramResult(
                    source=source,
                    language=self.language,
                    error=f"{self.name} rendering failed: {exc.stderr.decode(errors='replace')}",
                )
            except FileNotFoundError:
                return DiagramResult(
                    source=source,
                    language=self.language,
                    error=f"{self._tool} not available. Install: npm install -g {self._tool}",
                )

            svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None

            png: bytes | None = None
            try:
                subprocess.run(
                    [self._tool, str(input_path), str(png_path)],
                    check=True, capture_output=True, timeout=60,
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


class VegaRenderer(_VegaBaseRenderer):
    language = "vega"
    name = "Vega"
    description = "Render Vega visualization grammar diagrams"
    _tool = "vg2svg"


class VegaLiteRenderer(_VegaBaseRenderer):
    language = "vega-lite"
    name = "Vega-Lite"
    description = "Render Vega-Lite visualization grammar diagrams"
    _tool = "vl2svg"
