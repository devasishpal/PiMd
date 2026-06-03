"""BPMN diagram renderer — uses bpmn-js via Node.js or REST API."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pimd.diagrams.models import DiagramResult
from pimd.diagrams.renderers.base import DiagramRenderer


class BPMNRenderer(DiagramRenderer):
    """Render BPMN diagrams using bpmn-to-svg or bpmn-js.

    Requires Node.js with bpmn-to-svg installed:
        npm install -g bpmn-to-svg
    """

    language = "bpmn"
    name = "BPMN"
    version = "1.0.0"
    description = "Render BPMN 2.0 business process diagrams"
    priority = 80

    def is_available(self) -> bool:
        return self._which("bpmn-to-svg")

    def render(self, source: str, **options: Any) -> DiagramResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "diagram.bpmn"
            svg_path = Path(tmpdir) / "output.svg"

            input_path.write_text(source, encoding="utf-8")

            try:
                subprocess.run(
                    ["bpmn-to-svg", str(input_path), "-o", str(svg_path)],
                    check=True, capture_output=True, timeout=60,
                )
            except subprocess.CalledProcessError as exc:
                return DiagramResult(
                    source=source,
                    language=self.language,
                    error=f"BPMN rendering failed: {exc.stderr.decode(errors='replace')}",
                )
            except FileNotFoundError:
                return DiagramResult(
                    source=source,
                    language=self.language,
                    error="BPMN renderer not available. Install: npm install -g bpmn-to-svg",
                )

            svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None

            return DiagramResult(
                source=source,
                language=self.language,
                svg=svg,
            )
