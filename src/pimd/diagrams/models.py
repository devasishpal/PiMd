"""Diagram data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DiagramScaleMode(str, Enum):
    """How a diagram should be scaled to fit the page."""

    FIT_WIDTH = "fit_width"
    FIT_HEIGHT = "fit_height"
    FIT_PAGE = "fit_page"
    ORIGINAL = "original"
    CUSTOM = "custom"


class DiagramPlacement(str, Enum):
    """Where a diagram should be placed on the page."""

    INLINE = "inline"
    CENTER = "center"
    FLOAT_LEFT = "float_left"
    FLOAT_RIGHT = "float_right"
    PAGE_BREAK = "page_break"


@dataclass
class DiagramContext:
    """Rich context passed through the diagram rendering pipeline.

    Carries configuration, source metadata, plugin state, and results.
    Designed for extensibility — third-party plugins can attach custom
    data via the *metadata* dict.
    """

    source: str
    language: str | None = None
    config: DiagramConfig | None = None
    scale_mode: DiagramScaleMode = DiagramScaleMode.FIT_WIDTH
    placement: DiagramPlacement = DiagramPlacement.CENTER
    custom_width: int | None = None
    custom_height: int | None = None
    caption: str | None = None
    label: str | None = None
    figure_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    result: DiagramResult | None = None
    renderer_name: str | None = None
    plugin_data: dict[str, Any] = field(default_factory=dict)

    @property
    def resolved_width(self) -> int:
        if self.custom_width:
            return self.custom_width
        if self.config:
            return self.config.default_width
        return 600

    @property
    def resolved_height(self) -> int:
        if self.custom_height:
            return self.custom_height
        if self.config:
            return self.config.default_height
        return 400


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


RenderResult = DiagramResult


@dataclass
class DiagramConfig:
    """Configuration for the diagram system."""

    cache: bool = True
    svg_preferred: bool = True
    max_width: float = 6.5  # inches
    figure_captions: bool = True
    auto_number: bool = True
    default_width: int = 600
    default_height: int = 400
    max_width_px: int = 1200
    max_height_px: int = 1600
    dpi: int = 150
    add_captions: bool = True
    fallback_to_code_block: bool = True
    max_concurrent: int = 4
    temp_dir: str | None = None
    detect_diagrams: bool = True


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
    "blockdiag": "BlockDiag",
    "seqdiag": "SeqDiag",
    "actdiag": "ActDiag",
    "nwdiag": "NwDiag",
    "packetdiag": "PacketDiag",
    "bpmn": "BPMN",
    "vega": "Vega",
    "vega-lite": "Vega-Lite",
}


DIAGRAM_LANGUAGE_ALIASES: dict[str, str] = {
    "mmd": "mermaid",
    "puml": "plantuml",
    "graphviz": "dot",
    "ditaa": "ascii",
    "blockdiag": "blockdiag",
    "seqdiag": "seqdiag",
    "actdiag": "actdiag",
    "nwdiag": "nwdiag",
    "packetdiag": "packetdiag",
    "vega-lite": "vega-lite",
}


AUTO_DETECT_PATTERNS: dict[str, str] = {
    "mermaid": r"^\s*(graph\s+(TB|TD|BT|RL|LR)|sequenceDiagram|classDiagram|stateDiagram-v2|erDiagram|gantt|pie\s+show|pie\s+title|flowchart\s+(TB|TD|BT|RL|LR)|journey|gitgraph|mindmap|timeline|quadrantChart|requirementDiagram|xychart-beta)",
    "plantuml": r"^\s*@start\w+",
    "dot": r"^\s*(di(g|)raph\s+\w+\s*\{|graph\s+\w+\s*\{)",
    "d2": r"^\s*\w+\s*->\s*\w+",
    "vega-lite": r'^\s*\{[\s\S]*"\$schema"[\s\S]*"mark"[\s\S]*\}',
    "vega": r'^\s*\{[\s\S]*"\$schema"[\s\S]*"marks"[\s\S]*\}',
}
