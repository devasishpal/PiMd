"""Mermaid diagram renderer — CLI and API fallback."""

from __future__ import annotations

import base64
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen

from pimd.diagrams.models import DiagramResult
from pimd.diagrams.renderers.base import DiagramRenderer


class MermaidRenderer(DiagramRenderer):
    """Render Mermaid diagrams to SVG (primary) or PNG (fallback).

    Uses ``mmdc`` (mermaid-cli) for local rendering with a fallback to
    the ``mermaid.ink`` API for environments without Node.js.
    """

    language = "mermaid"
    name = "Mermaid"
    version = "1.0.0"
    description = "Render Mermaid.js diagrams (flowchart, sequenceDiagram, gantt, etc.)"
    priority = 10

    def is_available(self) -> bool:
        return self._which("mmdc")

    def render(self, source: str, **options: Any) -> DiagramResult:
        if self.is_available():
            return self._render_via_cli(source, **options)
        return self._render_via_api(source, **options)

    # ------------------------------------------------------------------
    # CLI rendering (mmdc)
    # ------------------------------------------------------------------

    def _render_via_cli(self, source: str, **options: Any) -> DiagramResult:
        width = options.get("width", 800)
        with tempfile.TemporaryDirectory() as tmpdir:
            mmd_path = Path(tmpdir) / "diagram.mmd"
            svg_path = Path(tmpdir) / "diagram.svg"
            png_path = Path(tmpdir) / "diagram.png"

            mmd_path.write_text(source, encoding="utf-8")

            cmd = [
                "mmdc",
                "-i",
                str(mmd_path),
                "-o",
                str(svg_path),
                "-w",
                str(width),
                "--backgroundColor",
                "white",
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)

            svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None

            # Also render PNG
            png: bytes | None = None
            try:
                png_cmd = [
                    "mmdc",
                    "-i",
                    str(mmd_path),
                    "-o",
                    str(png_path),
                    "-w",
                    str(width),
                    "--backgroundColor",
                    "white",
                ]
                subprocess.run(png_cmd, check=True, capture_output=True, timeout=60)
                png = png_path.read_bytes() if png_path.exists() else None
            except Exception:
                pass

            # Extract dimensions from SVG
            width_val, height_val = self._svg_dimensions(svg) if svg else (None, None)

            return DiagramResult(
                source=source,
                language=self.language,
                svg=svg,
                png=png,
                width=width_val,
                height=height_val,
            )

    # ------------------------------------------------------------------
    # API fallback (mermaid.ink)
    # ------------------------------------------------------------------

    def _render_via_api(self, source: str, **options: Any) -> DiagramResult:
        try:
            encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
            url = f"https://mermaid.ink/img/{quote(encoded, safe='')}"
            resp = urlopen(url, timeout=30)
            png = resp.read()

            # Also try SVG
            svg: str | None = None
            try:
                svg_url = f"https://mermaid.ink/svg/{quote(encoded, safe='')}"
                svg_resp = urlopen(svg_url, timeout=15)
                svg = svg_resp.read().decode("utf-8")
            except Exception:
                pass

            width_val, height_val = None, None
            if svg:
                width_val, height_val = self._svg_dimensions(svg)

            return DiagramResult(
                source=source,
                language=self.language,
                svg=svg,
                png=png,
                width=width_val,
                height=height_val,
            )
        except Exception as exc:
            return DiagramResult(
                source=source,
                language=self.language,
                error=f"Mermaid API fallback failed: {exc}",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _svg_dimensions(svg: str) -> tuple[int | None, int | None]:
        """Extract width and height from an SVG string."""
        import re

        w_match = re.search(r'width="(\d+)"', svg)
        h_match = re.search(r'height="(\d+)"', svg)
        w = int(w_match.group(1)) if w_match else None
        h = int(h_match.group(1)) if h_match else None
        return w, h
