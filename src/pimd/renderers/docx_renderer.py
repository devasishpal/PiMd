"""DOCX document renderer built on ``python-docx``."""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from pimd.exceptions import RendererError
from pimd.layout import apply_layout_to_doc
from pimd.models import (
    Block,
    Blockquote,
    BulletList,
    CodeBlock,
    Diagram,
    Document,
    EquationBlock,
    Heading,
    HorizontalRule,
    Image,
    ListItem,
    OrderedList,
    Paragraph,
    Span,
    Table,
)
from pimd.safety import SafetyGuard
from pimd.themes import ProfessionalTheme
from pimd.themes.base import Theme
from pimd.utils.logging import get_logger
from pimd.utils.text import sanitize_text

if TYPE_CHECKING:
    from docx.text.paragraph import Paragraph as DocxParagraph

logger = get_logger(__name__)

_MONO_FONT = "Courier New"
_MONO_SIZE = Pt(8.5)
_IMAGE_MAX_WIDTH = Cm(14)
_DIAGRAM_DPI = 150


class DocxRenderer:
    """Render PiMD's intermediate document model as a ``.docx`` file.

    Parameters
    ----------
    theme : Theme, optional
        Visual theme that controls typography, colours, and spacing.
        Defaults to :class:`ProfessionalTheme`.
    """

    def __init__(self, theme: Theme | None = None) -> None:
        self._doc: DocxDocument | None = None
        self._theme: Theme = theme or ProfessionalTheme()
        self._figure_counter: int = 0

    def render(
        self,
        document: Document,
        output_path: str | Path,
        *,
        generate_toc: bool = False,
        page_numbers: bool = False,
        header_text: str | None = None,
        footer_text: str | None = None,
        cover_page: bool = False,
        title: str | None = None,
        author: str | None = None,
        company: str | None = None,
        subject: str | None = None,
        keywords: list[str] | None = None,
        doc_version: str | None = None,
    ) -> None:
        """Render a :class:`Document` to a ``.docx`` file.

        Args:
            document: The intermediate document model.
            output_path: Destination path for the generated file.
            generate_toc: Insert a Word TOC field at the start.
            page_numbers: Add ``Page X`` to every page footer.
            header_text: Repeating text for the page header.
            footer_text: Repeating text for the page footer.
            cover_page: Prepend a title page.
            title: Document title (used in metadata and cover page).
            author: Document author (used in metadata and cover page).
            company: Company / organisation name.
            subject: Document subject (metadata only).
            keywords: List of keywords (metadata only).
            doc_version: Version string shown on the cover page.

        Raises:
            RendererError: If rendering fails.
        """
        try:
            self._doc = DocxDocument()
            apply_layout_to_doc(self._doc)
            self._theme.configure_styles(self._doc)
            self._set_metadata(title, author, company, subject, keywords)

            # -- Cover page (first section) --------------------------------
            if cover_page:
                self._add_cover_page(title, author, doc_version)
                self._doc.add_section()
                # Ensure headers / footers on the cover section are empty
                _clear_header_footer(self._doc.sections[0], link=False)

            # -- Table of contents -----------------------------------------
            if generate_toc:
                self._add_toc_heading()
                self._add_toc_field()
                self._doc.add_paragraph()

            # -- Main content ----------------------------------------------
            for block in document.blocks:
                self._render_block(block)

            # -- Configure headers / footers on the *last* section ---------
            content_section = self._doc.sections[-1]
            content_section.header.is_linked_to_previous = False
            content_section.footer.is_linked_to_previous = False

            if header_text:
                self._set_header(content_section, header_text)

            if page_numbers:
                self._add_page_numbers(content_section)
            elif footer_text:
                self._set_footer(content_section, footer_text)

            # Re-apply layout so that any sections added after the initial
            # call (cover, TOC, etc.) inherit the correct orientation & margins
            apply_layout_to_doc(self._doc)

            self._doc.save(str(output_path))
            logger.info("Rendered %s", output_path)
        except RendererError:
            raise
        except Exception as exc:
            raise RendererError(f"DOCX rendering failed: {exc}") from exc

    def render_to_bytes(
        self,
        document: Document,
        *,
        generate_toc: bool = False,
        page_numbers: bool = False,
        header_text: str | None = None,
        footer_text: str | None = None,
        cover_page: bool = False,
        title: str | None = None,
        author: str | None = None,
        company: str | None = None,
        subject: str | None = None,
        keywords: list[str] | None = None,
        doc_version: str | None = None,
    ) -> bytes:
        """Render a :class:`Document` to DOCX bytes without writing to disk.

        Accepts the same rendering options as :meth:`render`.

        Returns:
            The DOCX file contents as ``bytes``.
        """
        try:
            self._doc = DocxDocument()
            apply_layout_to_doc(self._doc)
            self._theme.configure_styles(self._doc)
            self._set_metadata(title, author, company, subject, keywords)

            if cover_page:
                self._add_cover_page(title, author, doc_version)
                self._doc.add_section()
                _clear_header_footer(self._doc.sections[0], link=False)

            if generate_toc:
                self._add_toc_heading()
                self._add_toc_field()
                self._doc.add_paragraph()

            for block in document.blocks:
                self._render_block(block)

            content_section = self._doc.sections[-1]
            content_section.header.is_linked_to_previous = False
            content_section.footer.is_linked_to_previous = False

            if header_text:
                self._set_header(content_section, header_text)

            if page_numbers:
                self._add_page_numbers(content_section)
            elif footer_text:
                self._set_footer(content_section, footer_text)

            apply_layout_to_doc(self._doc)

            buf = io.BytesIO()
            self._doc.save(buf)
            buf.seek(0)
            logger.info("Rendered DOCX to bytes (%d bytes)", len(buf.getvalue()))
            return buf.getvalue()
        except RendererError:
            raise
        except Exception as exc:
            raise RendererError(f"DOCX rendering failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _set_metadata(
        self,
        title: str | None,
        author: str | None,
        company: str | None,
        subject: str | None,
        keywords: list[str] | None,
    ) -> None:
        if title:
            self._doc.core_properties.title = title
        if author:
            self._doc.core_properties.author = author
        if company:
            self._doc.core_properties.category = company
        if subject:
            self._doc.core_properties.subject = subject
        if keywords:
            self._doc.core_properties.keywords = ", ".join(keywords)

    # ==================================================================
    # Cover page
    # ==================================================================

    def _add_cover_page(self, title: str | None, author: str | None, version: str | None) -> None:
        doc = self._doc

        for _ in range(6):
            doc.add_paragraph()

        # -- Title --
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(sanitize_text(title or "Untitled Document"))
        run.font.size = Pt(36)
        run.bold = True
        run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

        # -- Separator --
        self._render_horizontal_rule(doc)

        # -- Author --
        if author:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(sanitize_text(f"By {author}"))
            run.font.size = Pt(16)

        # -- Version / Date --
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        parts = []
        if version:
            parts.append(f"Version {version}")
        today = date.today().strftime("%B %d, %Y")
        parts.append(today)

        run = p.add_run(sanitize_text("  \u2022  ".join(parts)))
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        doc.add_paragraph()

    # ==================================================================
    # Table of contents
    # ==================================================================

    def _add_toc_heading(self) -> None:
        self._doc.add_heading("Table of Contents", level=1)

    def _add_toc_field(self) -> None:
        p = self._doc.add_paragraph()

        run = p.add_run()
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        run._r.append(fld_begin)

        run2 = p.add_run()
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = ' TOC \\o "1-6" \\h \\z \\u '
        run2._r.append(instr)

        run3 = p.add_run()
        fld_sep = OxmlElement("w:fldChar")
        fld_sep.set(qn("w:fldCharType"), "separate")
        run3._r.append(fld_sep)

        run4 = p.add_run()
        run4.text = "[Table of Contents \u2014 right-click and select \u201cUpdate Field\u201d]"
        run4.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
        run4.italic = True
        run4.font.size = Pt(9)

        run5 = p.add_run()
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        run5._r.append(fld_end)

    # ==================================================================
    # Headers / Footers / Page numbers
    # ==================================================================

    @staticmethod
    def _set_header(section, text: str) -> None:
        header = section.header
        header.is_linked_to_previous = False
        p = header.paragraphs[0]
        p.text = sanitize_text(text)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    @staticmethod
    def _set_footer(section, text: str) -> None:
        footer = section.footer
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0]
        p.text = sanitize_text(text)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    @staticmethod
    def _add_page_numbers(section) -> None:
        footer = section.footer
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        run = p.add_run("Page ")
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        run_num = p.add_run()
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        run_num._r.append(fld_begin)

        run_instr = p.add_run()
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = " PAGE "
        run_instr._r.append(instr)

        run_sep = p.add_run()
        fld_sep = OxmlElement("w:fldChar")
        fld_sep.set(qn("w:fldCharType"), "separate")
        run_sep._r.append(fld_sep)

        run_placeholder = p.add_run()
        run_placeholder.text = "1"
        run_placeholder.font.size = Pt(9)
        run_placeholder.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        run_end = p.add_run()
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        run_end._r.append(fld_end)

    # ------------------------------------------------------------------
    # Style setup (legacy, kept for backward compat — theme takes over)
    # ------------------------------------------------------------------

    def _configure_styles(self) -> None:
        pass  # handled by theme

    # ------------------------------------------------------------------
    # Block dispatch
    # ------------------------------------------------------------------

    def _render_block(self, block: Block) -> None:
        doc = self._doc

        if isinstance(block, Heading):
            self._render_heading(block)
        elif isinstance(block, Paragraph):
            self._render_paragraph(doc, block)
        elif isinstance(block, CodeBlock):
            self._render_code_block(doc, block)
        elif isinstance(block, Blockquote):
            self._render_blockquote(doc, block)
        elif isinstance(block, BulletList):
            self._render_bullet_list(doc, block, level=0)
        elif isinstance(block, OrderedList):
            self._render_ordered_list(doc, block, level=0)
        elif isinstance(block, Table):
            self._render_table(doc, block)
        elif isinstance(block, HorizontalRule):
            self._render_horizontal_rule(doc)
        elif isinstance(block, Image):
            self._render_image(doc, block)
        elif isinstance(block, Diagram):
            self._render_diagram(doc, block)
        elif isinstance(block, EquationBlock):
            self._render_equation_block(doc, block)
        elif isinstance(block, ListItem):
            self._render_list_item(doc, block)

    # ------------------------------------------------------------------
    # Heading
    # ------------------------------------------------------------------

    def _render_heading(self, block: Heading) -> None:
        level = min(max(block.level, 1), 6)
        text = sanitize_text(block.plain_text())
        self._doc.add_heading(text, level=level)

    # ------------------------------------------------------------------
    # Paragraph + spans
    # ------------------------------------------------------------------

    @staticmethod
    def _render_paragraph(doc: DocxDocument, block: Paragraph) -> None:
        p = doc.add_paragraph(style="Normal")
        p.paragraph_format.space_after = Pt(6)
        DocxRenderer._add_spans_to_paragraph(p, block.spans)

    @staticmethod
    def _add_spans_to_paragraph(p: DocxParagraph, spans: list[Span]) -> None:
        for span in spans:
            # Math span — inject OMML
            if span.math and span.omml is not None:
                p._p.append(span.omml)
                continue

            text = sanitize_text(span.text)
            if span.link_url:
                DocxRenderer._add_hyperlink(p, text, span.link_url)
            elif span.code:
                run = p.add_run(text)
                run.font.name = _MONO_FONT
                run.font.size = _MONO_SIZE
                run.font.color.rgb = RGBColor(0xE0, 0x3E, 0x2D)
            else:
                run = p.add_run(text)
                run.bold = span.bold
                run.italic = span.italic
                if span.underline:
                    run.underline = True

    @staticmethod
    def _add_hyperlink(paragraph: DocxParagraph, text: str, url: str) -> None:
        part = paragraph.part
        r_id = part.relate_to(
            url,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
            is_external=True,
        )

        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), r_id)

        run_elem = OxmlElement("w:r")
        run_props = OxmlElement("w:rPr")

        colour = OxmlElement("w:color")
        colour.set(qn("w:val"), "0563C1")
        run_props.append(colour)

        underline = OxmlElement("w:u")
        underline.set(qn("w:val"), "single")
        run_props.append(underline)

        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "22")
        run_props.append(sz)

        run_elem.append(run_props)
        run_elem.text = sanitize_text(text)
        hyperlink.append(run_elem)
        paragraph._p.append(hyperlink)

    # ------------------------------------------------------------------
    # Code block
    # ------------------------------------------------------------------

    @staticmethod
    def _render_code_block(doc: DocxDocument, block: CodeBlock) -> None:
        try:
            p = doc.add_paragraph(style="Code Block")
        except KeyError:
            p = doc.add_paragraph()

        run = p.add_run(sanitize_text(block.code))
        run.font.name = _MONO_FONT
        run.font.size = _MONO_SIZE
        run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # ------------------------------------------------------------------
    # Blockquote
    # ------------------------------------------------------------------

    @staticmethod
    def _render_blockquote(doc: DocxDocument, block: Blockquote) -> None:
        for child in block.children:
            if isinstance(child, Paragraph):
                try:
                    p = doc.add_paragraph(style="Blockquote")
                except KeyError:
                    p = doc.add_paragraph()
                    p.paragraph_format.left_indent = Cm(1.0)
                DocxRenderer._add_spans_to_paragraph(p, child.spans)
            else:
                DocxRenderer._render_blockquote(doc, child)

    # ------------------------------------------------------------------
    # Lists
    # ------------------------------------------------------------------

    def _render_bullet_list(self, doc: DocxDocument, block: BulletList, level: int) -> None:
        for item in block.items:
            self._render_list_item_with_prefix(doc, item, level, ordered=False, index=0)
            for child in item.children:
                if isinstance(child, BulletList):
                    self._render_bullet_list(doc, child, level + 1)

    def _render_ordered_list(self, doc: DocxDocument, block: OrderedList, level: int) -> None:
        for idx, item in enumerate(block.items):
            start = block.start
            self._render_list_item_with_prefix(doc, item, level, ordered=True, index=start + idx)
            for child in item.children:
                if isinstance(child, OrderedList):
                    self._render_ordered_list(doc, child, level + 1)

    def _render_list_item_with_prefix(
        self,
        doc: DocxDocument,
        item: ListItem,
        level: int,
        ordered: bool,
        index: int,
    ) -> None:
        indent = Cm(1.27 * (level + 1))
        first = True

        for child in item.children:
            if isinstance(child, Paragraph):
                p = doc.add_paragraph(style="Normal")
                p.paragraph_format.left_indent = indent
                p.paragraph_format.space_after = Pt(2)

                if first:
                    if ordered:
                        run = p.add_run(sanitize_text(f"{index}. "))
                    else:
                        bullets = ["\u2022", "\u25cb", "\u25a0"]
                        run = p.add_run(sanitize_text(f"{bullets[level % 3]} "))
                    run.font.size = Pt(10)
                    first = False

                self._add_spans_to_paragraph(p, child.spans)
            else:
                self._render_block(child)

    def _render_list_item(self, doc: DocxDocument, item: ListItem) -> None:
        for child in item.children:
            self._render_block(child)

    # ------------------------------------------------------------------
    # Table
    # ------------------------------------------------------------------

    @staticmethod
    def _render_table(doc: DocxDocument, block: Table) -> None:
        num_cols = max(len(block.headers), max((len(r) for r in block.rows), default=0))
        if num_cols == 0:
            return

        has_header = bool(block.headers)
        table = doc.add_table(rows=len(block.rows) + (1 if has_header else 0), cols=num_cols)
        table.autofit = True

        # -- Style borders via XML --
        tbl = table._tbl
        tbl_props = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
        borders = OxmlElement("w:tblBorders")
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = OxmlElement(f"w:{side}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "4")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "333333")
            borders.append(el)
        tbl_props.append(borders)

        row_idx = 0

        if has_header:
            for col_idx, text in enumerate(block.headers):
                cell = table.rows[0].cells[col_idx]
                cell.text = sanitize_text(text)
                tc_props = cell._tc.get_or_add_tcPr()
                shading = OxmlElement("w:shd")
                shading.set(qn("w:fill"), "1A1A2E")
                shading.set(qn("w:val"), "clear")
                tc_props.append(shading)
                for par in cell.paragraphs:
                    for run in par.runs:
                        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                        run.bold = True
            row_idx = 1

        for row_data in block.rows:
            for col_idx, text in enumerate(row_data):
                if col_idx < num_cols:
                    cell = table.rows[row_idx].cells[col_idx]
                    cell.text = sanitize_text(text)
            row_idx += 1

        doc.add_paragraph()

    # ------------------------------------------------------------------
    # Horizontal rule
    # ------------------------------------------------------------------

    @staticmethod
    def _render_horizontal_rule(doc: DocxDocument) -> None:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)

        p_props = p._p.get_or_add_pPr()
        p_border = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "999999")
        p_border.append(bottom)
        p_props.append(p_border)

    # ------------------------------------------------------------------
    # Image
    # ------------------------------------------------------------------

    @staticmethod
    def _render_image(doc: DocxDocument, block: Image) -> None:
        try:
            resolved = SafetyGuard().check_path_traversal(block.url)
        except Exception:
            logger.warning("Image path blocked (security): %s", block.url)
            p = doc.add_paragraph(style="Normal")
            run = p.add_run(sanitize_text(f"[Image: {block.alt}]"))
            run.italic = True
            run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            return

        path = Path(resolved)
        if not path.exists():
            logger.warning("Image not found, skipping: %s", block.url)
            p = doc.add_paragraph(style="Normal")
            run = p.add_run(sanitize_text(f"[Image: {block.alt}]"))
            run.italic = True
            run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            return

        try:
            doc.add_picture(str(path), width=_IMAGE_MAX_WIDTH)
        except Exception as exc:
            raise RendererError(f"Failed to insert image {block.url}: {exc}") from exc

    # ------------------------------------------------------------------
    # Diagram
    # ------------------------------------------------------------------

    def _render_diagram(self, doc: DocxDocument, block: Diagram) -> None:
        """Embed a rendered diagram into the document with professional formatting.

        Features:
        - Center alignment
        - Figure numbering (auto-incrementing)
        - Caption support
        - Proper scaling with DPI awareness
        - SVG preferred, PNG fallback
        - Error placeholder on render failure
        - Word compatibility
        """
        # -- Error placeholder if no image data --
        if not block.png_bytes and not block.svg_bytes:
            p = doc.add_paragraph(style="Normal")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(sanitize_text(f"[Diagram: {block.alt}]"))
            run.italic = True
            run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            run.font.size = Pt(9)
            if block.error:
                err_p = doc.add_paragraph(style="Normal")
                err_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                err_r = err_p.add_run(sanitize_text(f"Error: {block.error}"))
                err_r.italic = True
                err_r.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
                err_r.font.size = Pt(8)
            return

        # -- Determine image bytes (prefer PNG for DOCX compatibility) --
        img_data = block.png_bytes or block.svg_bytes or b""

        # -- Center-aligned paragraph for the image --
        p = doc.add_paragraph(style="Normal")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(3)

        img_stream = io.BytesIO(img_data)
        try:
            run = p.add_run()
            inline = run._r
            drawing = OxmlElement("w:drawing")
            inline.append(drawing)

            # Word-compatible inline image shape
            wp = OxmlElement("wp:inline")
            wp.set(qn("xmlns:wp"), "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing")
            wp.set(qn("distT"), "0")
            wp.set(qn("distB"), "0")
            wp.set(qn("distL"), "0")
            wp.set(qn("distR"), "0")

            extent = OxmlElement("wp:extent")
            cx = int(_IMAGE_MAX_WIDTH.emus)
            extent.set(qn("cx"), str(cx))
            extent.set(qn("cy"), str(int(cx * 0.6)))
            wp.append(extent)

            effect_extent = OxmlElement("wp:effectExtent")
            effect_extent.set(qn("l"), "0")
            effect_extent.set(qn("t"), "0")
            effect_extent.set(qn("r"), "0")
            effect_extent.set(qn("b"), "0")
            wp.append(effect_extent)

            doc_pr = OxmlElement("wp:docPr")
            doc_pr.set(qn("id"), "1")
            doc_pr.set(qn("name"), f"Diagram {block.language}")
            if block.caption:
                doc_pr.set(qn("descr"), sanitize_text(block.caption))
            wp.append(doc_pr)

            c_nv_pr = OxmlElement("wp:cNvGraphicFramePr")
            graphic_frame = OxmlElement("a:graphicFrameLocks")
            graphic_frame.set(qn("xmlns:a"), "http://schemas.openxmlformats.org/drawingml/2006/main")
            graphic_frame.set(qn("noChangeAspect"), "1")
            c_nv_pr.append(graphic_frame)
            wp.append(c_nv_pr)

            graphic = OxmlElement("a:graphic")
            graphic.set(qn("xmlns:a"), "http://schemas.openxmlformats.org/drawingml/2006/main")

            graphic_data = OxmlElement("a:graphicData")
            graphic_data.set(qn("uri"), "http://schemas.openxmlformats.org/drawingml/2006/picture")

            pic = OxmlElement("pic:pic")
            pic.set(qn("xmlns:pic"), "http://schemas.openxmlformats.org/drawingml/2006/picture")

            nv_pic_pr = OxmlElement("pic:nvPicPr")
            c_nv_pr_pic = OxmlElement("pic:cNvPr")
            c_nv_pr_pic.set(qn("id"), "0")
            c_nv_pr_pic.set(qn("name"), f"Diagram_{block.language}")
            nv_pic_pr.append(c_nv_pr_pic)
            c_nv_pic_pr_pic = OxmlElement("pic:cNvPicPr")
            nv_pic_pr.append(c_nv_pic_pr_pic)
            pic.append(nv_pic_pr)

            blip_fill = OxmlElement("pic:blipFill")
            blip = OxmlElement("a:blip")
            r_id = p.part.relate_to(
                img_stream,
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                is_external=False,
            )
            blip.set(qn("r:embed"), r_id)
            blip_fill.append(blip)
            stretch = OxmlElement("a:stretch")
            fill_rect = OxmlElement("a:fillRect")
            stretch.append(fill_rect)
            blip_fill.append(stretch)
            pic.append(blip_fill)

            sp_pr = OxmlElement("pic:spPr")
            xfrm = OxmlElement("a:xfrm")
            off = OxmlElement("a:off")
            off.set(qn("x"), "0")
            off.set(qn("y"), "0")
            xfrm.append(off)
            ext = OxmlElement("a:ext")
            ext.set(qn("cx"), str(cx))
            ext.set(qn("cy"), str(int(cx * 0.6)))
            xfrm.append(ext)
            sp_pr.append(xfrm)
            prst_geom = OxmlElement("a:prstGeom")
            prst_geom.set(qn("prst"), "rect")
            sp_pr.append(prst_geom)
            pic.append(sp_pr)

            graphic_data.append(pic)
            graphic.append(graphic_data)
            wp.append(graphic)
            drawing.append(wp)

        except Exception as exc:
            logger.warning("Failed to embed diagram via XML, falling back: %s", exc)
            try:
                img_stream.seek(0)
                doc.add_picture(img_stream, width=_IMAGE_MAX_WIDTH)
            except Exception as exc2:
                logger.warning("Failed to embed diagram: %s", exc2)
                p2 = doc.add_paragraph(style="Normal")
                p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run2 = p2.add_run(sanitize_text(f"[Diagram: {block.alt}]"))
                run2.italic = True
                run2.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

        # -- Error message below diagram --
        if block.error:
            err_p = doc.add_paragraph(style="Normal")
            err_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            err_r = err_p.add_run(sanitize_text(f"Warning: {block.error}"))
            err_r.italic = True
            err_r.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
            err_r.font.size = Pt(8)
            err_p.paragraph_format.space_after = Pt(6)

        # -- Caption with figure numbering --
        if block.caption:
            self._figure_counter += 1
            cap = doc.add_paragraph(style="Normal")
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.paragraph_format.space_before = Pt(2)
            cap.paragraph_format.space_after = Pt(8)

            caption_text = f"Figure {self._figure_counter}: {block.caption}"
            r = cap.add_run(sanitize_text(caption_text))
            r.font.size = Pt(9)
            r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
            r.italic = True

    # ------------------------------------------------------------------
    # Equation block
    # ------------------------------------------------------------------

    @staticmethod
    def _render_equation_block(doc: DocxDocument, block: EquationBlock) -> None:
        """Render a display equation as OMML (native) or SVG fallback."""
        p = doc.add_paragraph(style="Normal")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # OMML — native Word equation
        if block.omml is not None:
            p._p.append(block.omml)

        # Fallback — show LaTeX source (SVG embedding requires future enhancement)
        elif block.error:
            run = p.add_run(sanitize_text(f"[Equation Error: {block.error}]"))
            run.italic = True
            run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
        else:
            run = p.add_run(sanitize_text(f"[Equation: {block.latex[:60]}]"))
            run.italic = True
            run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

        # Equation number (right-aligned)
        if block.number is not None:
            p2 = doc.add_paragraph(style="Normal")
            p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r = p2.add_run(sanitize_text(f"({block.number})"))
            r.font.size = Pt(9)
            r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)


# ======================================================================
# Helper
# ======================================================================


def _clear_header_footer(section, link: bool = False) -> None:
    """Remove all content from a section's header and footer."""
    section.header.is_linked_to_previous = link
    section.footer.is_linked_to_previous = link
    for p in section.header.paragraphs:
        p.text = ""
    for p in section.footer.paragraphs:
        p.text = ""
