"""D2 diagram renderer — uses the ``d2`` CLI tool."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pimd.diagrams.models import DiagramResult
from pimd.diagrams.renderers.base import DiagramRenderer


class D2Renderer(DiagramRenderer):
    """Render D2 diagrams using the ``d2`` CLI.

    Requires D2 (https://d2lang.com) installed on the system.
    """

    language = "d2"
    name = "D2"
    version = "1.0.0"
    description = "Render D2 language diagrams"
    priority = 40

    def is_available(self) -> bool:
        return self._which("d2")

    def render(self, source: str, **options: Any) -> DiagramResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.d2"
            output_path = Path(tmpdir) / "output"
            svg_path = output_path.with_suffix(".svg")
            png_path = output_path.with_suffix(".png")

            input_path.write_text(source, encoding="utf-8")

            # D2 renders to SVG by default
            subprocess.run(
                ["d2", str(input_path), str(svg_path)],
                check=True,
                capture_output=True,
                timeout=60,
            )
            svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None

            # Try PNG
            png: bytes | None = None
            try:
                subprocess.run(
                    ["d2", str(input_path), str(png_path)],
                    check=True,
                    capture_output=True,
                    timeout=60,
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
