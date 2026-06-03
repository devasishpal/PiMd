"""Diagram data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiagramResult:
    """Result of rendering a single diagram."""

    source: str
    language: str
    svg: str | None = None
    png: bytes | None = None
    width: int | None = None
    height: int | None = None
    error: str | None = None
    cached: bool = False
    render_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.error is None and (self.svg is not None or self.png is not None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "width": self.width,
            "height": self.height,
            "error": self.error,
            "cached": self.cached,
            "render_time": round(self.render_time, 4),
            "success": self.success,
        }


@dataclass
class DiagramConfig:
    """Configuration for the diagram system."""

    default_width: int = 600
    default_height: int = 400
    max_width: int = 1200
    max_height: int = 1600
    dpi: int = 150
    add_captions: bool = True
    auto_number: bool = False
    fallback_to_code_block: bool = True
    max_concurrent: int = 4
    temp_dir: str | None = None


DIAGRAM_LANGUAGES: dict[str, str] = {
    "mermaid": "Mermaid",
    "mmd": "Mermaid",
    "plantuml": "PlantUML",
    "puml": "PlantUML",
    "dot": "Graphviz",
    "graphviz": "Graphviz",
    "d2": "D2",
    "ascii": "ASCII Diagram",
    "ditaa": "ASCII Diagram",
    "svg": "SVG",
}
