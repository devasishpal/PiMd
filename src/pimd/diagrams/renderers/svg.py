"""SVG renderer — embed inline and external SVG as PNG in DOCX."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pimd.diagrams.models import DiagramResult
from pimd.diagrams.renderers.base import DiagramRenderer


class SvgRenderer(DiagramRenderer):
    """Render SVG content for DOCX embedding.

    Since python-docx does not natively support SVG, this renderer
    converts SVG to PNG using available tools (cairosvg, inkscape,
    or rsvg-convert).
    """

    language = "svg"
    name = "SVG"
    version = "1.0.0"
    description = "Embed SVG images (converted to PNG for DOCX)"
    priority = 60

    def is_available(self) -> bool:
        return True  # We handle inline SVGs even without conversion tools

    def render(self, source: str, **options: Any) -> DiagramResult:
        # Determine if source is a file path or inline SVG
        path = Path(source)
        if path.exists() and path.suffix.lower() in (".svg",):
            svg = path.read_text(encoding="utf-8")
        else:
            svg = source

        png = self._convert_to_png(svg, **options)

        return DiagramResult(
            source=source,
            language=self.language,
            svg=svg,
            png=png,
        )

    def _convert_to_png(self, svg: str, **options: Any) -> bytes | None:
        """Convert SVG string to PNG bytes."""

        # Try cairosvg first (pure Python)
        png = self._try_cairosvg(svg, **options)
        if png:
            return png

        # Try rsvg-convert
        png = self._try_rsvg_convert(svg)
        if png:
            return png

        # Try inkscape
        png = self._try_inkscape(svg)
        if png:
            return png

        return None

    @staticmethod
    def _try_cairosvg(svg: str, **options: Any) -> bytes | None:
        try:
            import cairosvg

            width = options.get("width")
            kwargs = {}
            if width:
                kwargs["output_width"] = width
            return cairosvg.svg2png(bytestring=svg.encode("utf-8"), **kwargs)
        except ImportError:
            return None
        except Exception:
            return None

    @staticmethod
    def _try_rsvg_convert(svg: str) -> bytes | None:
        import subprocess
        import tempfile
        from pathlib import Path

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                svg_path = Path(tmpdir) / "input.svg"
                png_path = Path(tmpdir) / "output.png"
                svg_path.write_text(svg, encoding="utf-8")
                subprocess.run(
                    ["rsvg-convert", str(svg_path), "-o", str(png_path)],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                return png_path.read_bytes() if png_path.exists() else None
        except Exception:
            return None

    @staticmethod
    def _try_inkscape(svg: str) -> bytes | None:
        import subprocess
        import tempfile
        from pathlib import Path

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                svg_path = Path(tmpdir) / "input.svg"
                png_path = Path(tmpdir) / "output.png"
                svg_path.write_text(svg, encoding="utf-8")
                subprocess.run(
                    ["inkscape", str(svg_path), "--export-filename", str(png_path)],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                return png_path.read_bytes() if png_path.exists() else None
        except Exception:
            return None
