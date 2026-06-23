"""Professional document theme — clean, publication-quality typography."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from pimd.themes.base import Theme

if TYPE_CHECKING:
    from docx import Document as DocxDocument


_BODY_FONT = "Calibri"
_HEADING_FONT = "Calibri"
_MONO_FONT = "Courier New"
_BODY_SIZE = Pt(11)
_MONO_SIZE = Pt(8.5)


class ProfessionalTheme(Theme):
    """Clean, professional theme suitable for business and technical docs.

    Applies:
        - Calibri body and heading fonts
        - Dark navy headings
        - Shaded code blocks with monospace font
        - Indented blockquotes with left border
        - Professional table headers with dark background
        - Consistent paragraph spacing and line-height
    """

    name: str = "professional"

    def configure_styles(self, doc: DocxDocument) -> None:
        self._configure_normal(doc)
        self._configure_heading(doc)
        self._configure_title(doc)
        self._add_code_style(doc)
        self._add_blockquote_style(doc)

    # ------------------------------------------------------------------
    # Normal
    # ------------------------------------------------------------------

    @staticmethod
    def _configure_normal(doc: DocxDocument) -> None:
        style = doc.styles["Normal"]
        style.font.name = _BODY_FONT
        style.font.size = _BODY_SIZE
        style.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.line_spacing = 1.15

    # ------------------------------------------------------------------
    # Headings
    # ------------------------------------------------------------------

    @staticmethod
    def _configure_heading(doc: DocxDocument) -> None:
        sizes = {1: Pt(22), 2: Pt(18), 3: Pt(15), 4: Pt(13), 5: Pt(11.5), 6: Pt(10.5)}
        spaces_before = {1: Pt(24), 2: Pt(18), 3: Pt(12), 4: Pt(8), 5: Pt(6), 6: Pt(4)}

        for level in range(1, 7):
            style = doc.styles[f"Heading {level}"]
            style.font.name = _HEADING_FONT
            style.font.bold = True
            style.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
            style.font.size = sizes[level]
            style.paragraph_format.space_before = spaces_before[level]
            style.paragraph_format.space_after = Pt(4)
            style.paragraph_format.keep_with_next = True

    @staticmethod
    def _configure_title(doc: DocxDocument) -> None:
        style = doc.styles["Title"]
        style.font.name = _HEADING_FONT
        style.font.size = Pt(28)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
        style.paragraph_format.space_after = Pt(12)
        style.paragraph_format.alignment = 1  # CENTER

    # ------------------------------------------------------------------
    # Custom: Code Block
    # ------------------------------------------------------------------

    @staticmethod
    def _add_code_style(doc: DocxDocument) -> None:
        try:
            style = doc.styles["Code Block"]
        except KeyError:
            style = doc.styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = _MONO_FONT
        style.font.size = _MONO_SIZE
        style.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        style.paragraph_format.space_before = Pt(4)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.left_indent = Cm(0.5)
        style.paragraph_format.right_indent = Cm(0.5)
        style.paragraph_format.line_spacing = 1.0

        p_props = style.element.get_or_add_pPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "F5F5F5")
        shading.set(qn("w:val"), "clear")
        p_props.append(shading)

    # ------------------------------------------------------------------
    # Custom: Blockquote
    # ------------------------------------------------------------------

    @staticmethod
    def _add_blockquote_style(doc: DocxDocument) -> None:
        try:
            style = doc.styles["Blockquote"]
        except KeyError:
            style = doc.styles.add_style("Blockquote", WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = _BODY_FONT
        style.font.size = _BODY_SIZE
        style.font.italic = True
        style.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        style.paragraph_format.left_indent = Cm(1.0)
        style.paragraph_format.right_indent = Cm(1.0)
        style.paragraph_format.space_before = Pt(6)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.line_spacing = 1.15

        p_props = style.element.get_or_add_pPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "F9F9F9")
        shading.set(qn("w:val"), "clear")
        p_props.append(shading)
