"""Document layout configuration — page size, margins, orientation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


class PageSize(str, Enum):
    """Standard page sizes."""

    A4 = "A4"
    A3 = "A3"
    A5 = "A5"
    LETTER = "LETTER"
    LEGAL = "LEGAL"
    TABLOID = "TABLOID"


class PageOrientation(str, Enum):
    """Page orientation."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


_PAGE_SIZE_MM: dict[PageSize, tuple[int, int]] = {
    PageSize.A4: (210, 297),
    PageSize.A3: (297, 420),
    PageSize.A5: (148, 210),
    PageSize.LETTER: (216, 279),
    PageSize.LEGAL: (216, 356),
    PageSize.TABLOID: (279, 432),
}


@dataclass
class Margins:
    """Page margins in inches."""

    top: float = 0.5
    bottom: float = 0.5
    left: float = 0.5
    right: float = 0.5

    @classmethod
    def narrow(cls) -> Margins:
        return cls(top=0.5, bottom=0.5, left=0.5, right=0.5)

    @classmethod
    def normal(cls) -> Margins:
        return cls(top=1.0, bottom=1.0, left=1.0, right=1.0)

    @classmethod
    def wide(cls) -> Margins:
        return cls(top=1.0, bottom=1.0, left=2.0, right=2.0)

    def to_inches(self) -> dict[str, float]:
        return {"top": self.top, "bottom": self.bottom, "left": self.left, "right": self.right}

    def to_cm(self) -> dict[str, float]:
        return {k: v * 2.54 for k, v in self.to_inches().items()}


@dataclass
class DocumentLayoutConfig:
    """Document layout and quality defaults.

    Applied automatically on every conversion.
    Users may override individual fields.

    Default: A4 portrait, narrow 0.5\" margins.
    """

    page_size: PageSize = PageSize.A4
    orientation: PageOrientation = PageOrientation.PORTRAIT
    margins: Margins = field(default_factory=Margins.narrow)
    default_font_size: int = 11
    default_font: str = "Calibri"
    heading_font: str = "Calibri"
    paragraph_spacing_after: int = 6
    line_spacing: float = 1.15

    def page_size_mm(self) -> tuple[int, int]:
        w, h = _PAGE_SIZE_MM[self.page_size]
        if self.orientation == PageOrientation.LANDSCAPE:
            return h, w
        return w, h

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_size": self.page_size.value,
            "orientation": self.orientation.value,
            "margins": self.margins.to_inches(),
            "default_font_size": self.default_font_size,
            "default_font": self.default_font,
            "heading_font": self.heading_font,
            "paragraph_spacing_after": self.paragraph_spacing_after,
            "line_spacing": self.line_spacing,
        }


def default_layout() -> DocumentLayoutConfig:
    """Return a fresh default layout configuration."""
    return DocumentLayoutConfig()


DEFAULT_LAYOUT = DocumentLayoutConfig()


def apply_layout_to_doc(doc: Any, layout: DocumentLayoutConfig | None = None) -> None:
    """Apply layout settings to a python-docx document.

    Sets page size, margins, orientation on all sections.
    """
    cfg = layout or DEFAULT_LAYOUT
    w, h = cfg.page_size_mm()
    width_twips = round(w / 25.4 * 1440)
    height_twips = round(h / 25.4 * 1440)
    orient = "landscape" if cfg.orientation == PageOrientation.LANDSCAPE else "portrait"

    for section in doc.sections:
        sect_pr = section._sectPr
        pg_sz = sect_pr.find(qn("w:pgSz"))
        if pg_sz is None:
            pg_sz = OxmlElement("w:pgSz")
            sect_pr.append(pg_sz)
        pg_sz.set(qn("w:w"), str(width_twips))
        pg_sz.set(qn("w:h"), str(height_twips))
        pg_sz.set(qn("w:orient"), orient)

        section.top_margin = Inches(cfg.margins.top)
        section.bottom_margin = Inches(cfg.margins.bottom)
        section.left_margin = Inches(cfg.margins.left)
        section.right_margin = Inches(cfg.margins.right)

        try:
            style = doc.styles["Normal"]
            style.font.name = cfg.default_font
            style.font.size = Pt(cfg.default_font_size)
            pf = style.paragraph_format
            pf.space_after = Pt(cfg.paragraph_spacing_after)
            pf.line_spacing = cfg.line_spacing
        except Exception:
            pass
