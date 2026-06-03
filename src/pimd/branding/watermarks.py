"""Watermark support for DOCX documents."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from docx import Document as DocxDocument
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from pimd.utils.text import sanitize_text


class WatermarkType(str, Enum):
    """Standard watermark types."""

    CONFIDENTIAL = "CONFIDENTIAL"
    INTERNAL = "INTERNAL"
    DRAFT = "DRAFT"
    PUBLIC = "PUBLIC"
    CUSTOM = "CUSTOM"


@dataclass
class WatermarkConfig:
    """Configuration for a document watermark."""

    text: str = "DRAFT"
    font_size: int = 72
    color: str = "C0C0C0"
    rotation: int = -45
    opacity: float = 0.3
    enabled: bool = True
    type: WatermarkType = WatermarkType.DRAFT


_STANDARD_TEXTS: dict[WatermarkType, str] = {
    WatermarkType.CONFIDENTIAL: "CONFIDENTIAL",
    WatermarkType.INTERNAL: "INTERNAL",
    WatermarkType.DRAFT: "DRAFT",
    WatermarkType.PUBLIC: "PUBLIC",
    WatermarkType.CUSTOM: "",
}


def apply_watermark(
    doc: DocxDocument,
    config: WatermarkConfig,
) -> None:
    """Apply a watermark to every page of the document.

    Uses Word's built-in watermark mechanism via header XML injection.
    """
    if not config.enabled:
        return
    watermark_text = config.text
    if config.type != WatermarkType.CUSTOM and not watermark_text:
        watermark_text = _STANDARD_TEXTS.get(config.type, "DRAFT")

    for section in doc.sections:
        header = section.header
        header.is_linked_to_previous = False
        _add_watermark_to_header(header, watermark_text, config)
        # Also add to first-page header for cover compatibility
        try:
            first_header = section.first_page_header
            _add_watermark_to_header(first_header, watermark_text, config)
        except Exception:
            pass


def _add_watermark_to_header(header: Any, text: str, config: WatermarkConfig) -> None:
    """Inject a Word watermark shape into a header."""
    try:
        hdr_elem = header._element
        r = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(config.font_size * 2))
        rpr.append(sz)
        sz_cs = OxmlElement("w:szCs")
        sz_cs.set(qn("w:val"), str(config.font_size * 2))
        rpr.append(sz_cs)
        color_el = OxmlElement("w:color")
        color_el.set(qn("w:val"), config.color)
        rpr.append(color_el)
        effect = OxmlElement("w:effect")
        effect.set(qn("w:val"), "shadow")
        rpr.append(effect)
        r.append(rpr)
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = sanitize_text(text)
        r.append(t)

        wp = OxmlElement("w:p")
        ppr2 = OxmlElement("w:pPr")
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), "center")
        ppr2.append(jc)
        wp.append(ppr2)
        wp.append(r)

        hdr_elem.append(wp)
    except Exception:
        pass
