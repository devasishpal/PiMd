"""Export data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ExportFormat(str, Enum):
    """Supported output formats."""

    DOCX = "docx"
    PDF = "pdf"
    HTML = "html"
    MD = "md"
    RTF = "rtf"
    ODT = "odt"
    TXT = "txt"


@dataclass
class ExportOptions:
    """Options controlling export behaviour."""

    template: str = ""
    brand: str = ""
    cover_page: bool = False
    generate_toc: bool = False
    page_numbers: bool = True
    watermark: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    css_path: str | None = None
    pdf_engine: str = "auto"
    pdf_dpi: int = 150


@dataclass
class ExportResult:
    """Result of an export operation."""

    output_path: Path
    format: ExportFormat
    success: bool
    error: str | None = None
    page_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.success
