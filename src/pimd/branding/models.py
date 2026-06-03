"""Brand data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BrandMetadata:
    """Document metadata fields set by branding."""

    title: str = ""
    subtitle: str = ""
    author: str = ""
    company: str = ""
    subject: str = ""
    keywords: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    revision: str = ""


@dataclass
class BrandConfig:
    """Branding configuration for visual identity."""

    primary_color: str = "1F4E79"
    secondary_color: str = "2E75B6"
    accent_color: str = "C00000"
    background_color: str = "FFFFFF"
    text_color: str = "000000"
    font_family: str = "Calibri"
    heading_font: str = "Calibri"
    font_size_base: int = 11
    logo_path: str | None = None
    logo_width_mm: float = 40.0
    logo_height_mm: float = 20.0
    footer_text: str = ""
    header_text: str = ""
    website: str = ""
    address: str = ""


@dataclass
class Brand:
    """Complete brand identity for a document or organisation."""

    name: str
    metadata: BrandMetadata = field(default_factory=BrandMetadata)
    config: BrandConfig = field(default_factory=BrandConfig)

    @property
    def logo_abs_path(self) -> Path | None:
        if self.config.logo_path is None:
            return None
        p = Path(self.config.logo_path)
        if p.is_absolute():
            return p if p.is_file() else None
        resolved = Path.cwd() / p
        return resolved if resolved.is_file() else None
