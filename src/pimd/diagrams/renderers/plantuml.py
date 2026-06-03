"""PlantUML diagram renderer — local Java-based rendering."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pimd.diagrams.models import DiagramResult
from pimd.diagrams.renderers.base import DiagramRenderer


class PlantUMLRenderer(DiagramRenderer):
    """Render PlantUML diagrams using ``plantuml.jar``.

    Requires Java Runtime Environment (JRE) and the plantuml.jar file
    accessible via the ``plantuml`` command or ``java -jar plantuml.jar``.
    """

    language = "plantuml"
    name = "PlantUML"
    version = "1.0.0"
    description = "Render PlantUML diagrams (sequence, activity, class, etc.)"
    priority = 20

    def is_available(self) -> bool:
        if self._which("plantuml"):
            return True
        if self._which("java"):
            # Check if plantuml.jar is findable
            return self._find_plantuml_jar() is not None
        return False

    def render(self, source: str, **options: Any) -> DiagramResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "diagram.puml"
            svg_path = Path(tmpdir) / "diagram.svg"
            png_path = Path(tmpdir) / "diagram.png"

            # Add PlantUML header if missing
            content = source
            if not source.strip().startswith("@start"):
                content = f"@startuml\n{source}\n@enduml"
            input_path.write_text(content, encoding="utf-8")

            cmd = self._build_command(input_path, svg_path, "svg")
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)

            svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None

            # Also render PNG
            png: bytes | None = None
            try:
                png_cmd = self._build_command(input_path, png_path, "png")
                subprocess.run(png_cmd, check=True, capture_output=True, timeout=60)
                png = png_path.read_bytes() if png_path.exists() else None
            except Exception:
                pass

            return DiagramResult(
                source=source,
                language=self.language,
                svg=svg,
                png=png,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_command(self, input_path: Path, output_path: Path, fmt: str) -> list[str]:
        if self._which("plantuml"):
            return [
                "plantuml",
                "-t" + fmt,
                str(input_path),
                "-o",
                str(output_path.parent),
            ]
        jar = self._find_plantuml_jar()
        if jar:
            return ["java", "-jar", jar, "-t" + fmt, str(input_path), "-o", str(output_path.parent)]
        return ["plantuml", "-t" + fmt, str(input_path)]

    @staticmethod
    def _find_plantuml_jar() -> str | None:
        import glob

        candidates = [
            "plantuml.jar",
            "plantuml*.jar",
            str(Path.home() / "plantuml*.jar"),
            str(Path.home() / ".pimd" / "plantuml*.jar"),
        ]
        for pattern in candidates:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
        return None
