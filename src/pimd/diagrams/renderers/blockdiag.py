"""BlockDiag, SeqDiag, ActDiag, NwDiag, PacketDiag renderers."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pimd.diagrams.models import DiagramResult
from pimd.diagrams.renderers.base import DiagramRenderer

_BLOCKDIAG_TOOLS = {
    "blockdiag": "blockdiag",
    "seqdiag": "seqdiag",
    "actdiag": "actdiag",
    "nwdiag": "nwdiag",
    "packetdiag": "packetdiag",
}


class _BlockDiagBaseRenderer(DiagramRenderer):
    """Base class for BlockDiag-family renderers."""

    language: str = ""
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    priority: int = 70
    _tool: str = ""

    def is_available(self) -> bool:
        return self._which(self._tool)

    def render(self, source: str, **options: Any) -> DiagramResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.diag"
            svg_path = Path(tmpdir) / "output.svg"
            png_path = Path(tmpdir) / "output.png"

            input_path.write_text(source, encoding="utf-8")

            try:
                subprocess.run(
                    [self._tool, "-Tsvg", str(input_path), "-o", str(svg_path)],
                    check=True, capture_output=True, timeout=60,
                )
            except subprocess.CalledProcessError as exc:
                return DiagramResult(
                    source=source,
                    language=self.language,
                    error=f"{self.name} SVG rendering failed: {exc.stderr.decode(errors='replace')}",
                )

            svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None

            png: bytes | None = None
            try:
                subprocess.run(
                    [self._tool, "-Tpng", str(input_path), "-o", str(png_path)],
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


class BlockDiagRenderer(_BlockDiagBaseRenderer):
    language = "blockdiag"
    name = "BlockDiag"
    description = "Render block diagrams using blockdiag"
    _tool = "blockdiag"


class SeqDiagRenderer(_BlockDiagBaseRenderer):
    language = "seqdiag"
    name = "SeqDiag"
    description = "Render sequence diagrams using seqdiag"
    _tool = "seqdiag"


class ActDiagRenderer(_BlockDiagBaseRenderer):
    language = "actdiag"
    name = "ActDiag"
    description = "Render activity diagrams using actdiag"
    _tool = "actdiag"


class NwDiagRenderer(_BlockDiagBaseRenderer):
    language = "nwdiag"
    name = "NwDiag"
    description = "Render network diagrams using nwdiag"
    _tool = "nwdiag"


class PacketDiagRenderer(_BlockDiagBaseRenderer):
    language = "packetdiag"
    name = "PacketDiag"
    description = "Render packet diagrams using packetdiag"
    _tool = "packetdiag"
