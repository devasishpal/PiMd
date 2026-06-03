"""Template data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TemplateType(str, Enum):
    """Built-in template categories."""

    PROFESSIONAL = "professional"
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    BUSINESS = "business"
    BOOK = "book"
    PROPOSAL = "proposal"
    INVOICE = "invoice"
    RESUME = "resume"
    MANUAL = "manual"
    API = "api"
    CUSTOM = "custom"


@dataclass
class TemplateMetadata:
    """Metadata describing a template."""

    name: str
    type: TemplateType
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class TemplateConfig:
    """Configuration applied when a template is used."""

    page_size: str = "A4"
    margin_top: float = 2.54
    margin_bottom: float = 2.54
    margin_left: float = 2.54
    margin_right: float = 2.54
    default_font: str = "Calibri"
    default_font_size: int = 11
    heading_font: str = "Calibri"
    line_spacing: float = 1.15
    paragraph_spacing: float = 6.0
    page_numbers: bool = True
    generate_toc: bool = False
    cover_page: bool = False
    header_text: str = ""
    footer_text: str = ""
    watermark_text: str = ""
    watermark_enabled: bool = False
    custom_styles: dict[str, dict[str, object]] = field(default_factory=dict)


@dataclass
class Template:
    """A reusable document template."""

    metadata: TemplateMetadata
    config: TemplateConfig = field(default_factory=TemplateConfig)
    docx_template_path: Path | None = None
    content_before: str = ""
    content_after: str = ""

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def type(self) -> TemplateType:
        return self.metadata.type

    def merge_config(self, overrides: dict[str, object]) -> TemplateConfig:
        """Produce a new config merging template defaults with user overrides."""
        merged = TemplateConfig(
            **{k: v for k, v in self.config.__dict__.items() if not k.startswith("_")}
        )
        for key, value in overrides.items():
            if hasattr(merged, key):
                setattr(merged, key, value)
        return merged
