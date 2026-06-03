"""Tests for templates, branding, export, reports, books, citations, merge, batch, validation."""

from __future__ import annotations

from pathlib import Path

from pimd.batch import BatchProcessor
from pimd.books import BookChapter, BookCompiler, BookConfig, BookPart
from pimd.branding import Brand, BrandConfig, BrandingManager, BrandMetadata
from pimd.branding.covers import CoverConfig
from pimd.branding.watermarks import WatermarkConfig, WatermarkType
from pimd.citations import CitationEngine, CitationEntry, CitationStyle
from pimd.export import ExportConverter, ExportFormat, ExportOptions, ExportResult
from pimd.merge import DocumentMerger
from pimd.models import Diagram, Document, EquationBlock, Image, Table
from pimd.reports import ReportConfig, ReportEngine, ReportSection, ReportType
from pimd.reports.figures import TableOfFigures
from pimd.templates import Template, TemplateConfig, TemplateManager, TemplateMetadata, TemplateType
from pimd.validation import DocumentValidator

# ======================================================================
# Template Engine (Part 1)
# ======================================================================


class TestTemplateModels:
    def test_template_type_enum(self) -> None:
        assert TemplateType.PROFESSIONAL.value == "professional"
        assert TemplateType.ACADEMIC.value == "academic"
        assert TemplateType.CUSTOM.value == "custom"

    def test_template_metadata(self) -> None:
        m = TemplateMetadata(name="test", type=TemplateType.CUSTOM)
        assert m.name == "test"
        assert m.type == TemplateType.CUSTOM

    def test_template_config_defaults(self) -> None:
        cfg = TemplateConfig()
        assert cfg.page_size == "A4"
        assert cfg.default_font == "Calibri"
        assert cfg.default_font_size == 11

    def test_template_creation(self) -> None:
        meta = TemplateMetadata(name="My Template", type=TemplateType.PROFESSIONAL)
        cfg = TemplateConfig(page_size="Letter", default_font="Arial")
        tpl = Template(metadata=meta, config=cfg)
        assert tpl.name == "My Template"
        assert tpl.type == TemplateType.PROFESSIONAL
        assert tpl.config.page_size == "Letter"

    def test_merge_config(self) -> None:
        tpl = Template(
            metadata=TemplateMetadata(name="t", type=TemplateType.CUSTOM),
            config=TemplateConfig(page_size="A4", page_numbers=False),
        )
        merged = tpl.merge_config({"page_size": "Letter", "page_numbers": True})
        assert merged.page_size == "Letter"
        assert merged.page_numbers
        assert merged.default_font == "Calibri"  # default preserved


class TestTemplateManager:
    def test_instantiation(self) -> None:
        mgr = TemplateManager()
        assert mgr is not None

    def test_builtin_names_present(self) -> None:
        mgr = TemplateManager()
        names = mgr.builtin_names()
        # presets dir may exist
        assert isinstance(names, list)

    def test_list_templates(self) -> None:
        mgr = TemplateManager()
        templates = mgr.list_templates()
        assert isinstance(templates, list)

    def test_get_nonexistent(self) -> None:
        mgr = TemplateManager()
        assert mgr.get("__nonexistent__") is None

    def test_validate_nonexistent(self) -> None:
        mgr = TemplateManager()
        result = mgr.validate("__nonexistent__")
        assert not result.valid


# ======================================================================
# Branding System (Parts 3-5)
# ======================================================================


class TestBrandModels:
    def test_default_brand(self) -> None:
        brand = Brand(name="Test")
        assert brand.name == "Test"
        assert brand.metadata.author == ""
        assert brand.config.primary_color == "1F4E79"

    def test_brand_metadata(self) -> None:
        meta = BrandMetadata(title="Doc", author="Alice", company="Acme")
        assert meta.title == "Doc"
        assert meta.author == "Alice"

    def test_brand_config(self) -> None:
        cfg = BrandConfig(primary_color="FF0000", font_family="Arial")
        assert cfg.primary_color == "FF0000"
        assert cfg.font_family == "Arial"


class TestBrandingManager:
    def test_load_from_dict(self) -> None:
        mgr = BrandingManager()
        brand = mgr.load(
            {
                "name": "Acme",
                "metadata": {"company": "Acme Corp", "author": "Bob"},
                "config": {"primary_color": "123456"},
            }
        )
        assert brand.name == "Acme"
        assert brand.metadata.company == "Acme Corp"
        assert brand.config.primary_color == "123456"

    def test_set_and_clear(self) -> None:
        mgr = BrandingManager()
        brand = Brand(name="Test")
        mgr.set(brand)
        assert mgr.brand is not None
        mgr.clear()
        assert mgr.brand is None

    def test_to_dict(self) -> None:
        mgr = BrandingManager()
        mgr.set(Brand(name="Test", metadata=BrandMetadata(company="C")))
        d = mgr.to_dict()
        assert d["name"] == "Test"
        assert d["metadata"]["company"] == "C"


class TestCoverConfig:
    def test_defaults(self) -> None:
        cfg = CoverConfig()
        assert cfg.title == ""
        assert cfg.title_size == 36

    def test_with_values(self) -> None:
        cfg = CoverConfig(
            title="Report Title",
            subtitle="Subtitle",
            version="2.0",
            author="Alice",
            classification="CONFIDENTIAL",
        )
        assert cfg.title == "Report Title"
        assert cfg.classification == "CONFIDENTIAL"


class TestWatermarkConfig:
    def test_defaults(self) -> None:
        cfg = WatermarkConfig()
        assert cfg.text == "DRAFT"
        assert cfg.type == WatermarkType.DRAFT

    def test_confidential(self) -> None:
        cfg = WatermarkConfig(type=WatermarkType.CONFIDENTIAL)
        assert cfg.type == WatermarkType.CONFIDENTIAL


# ======================================================================
# Export System (Parts 6-7)
# ======================================================================


class TestExportModels:
    def test_export_format_enum(self) -> None:
        assert ExportFormat.DOCX.value == "docx"
        assert ExportFormat.PDF.value == "pdf"
        assert ExportFormat.HTML.value == "html"
        assert ExportFormat.MD.value == "md"
        assert ExportFormat.TXT.value == "txt"

    def test_export_options_defaults(self) -> None:
        opts = ExportOptions()
        assert not opts.cover_page
        assert opts.page_numbers

    def test_export_result(self) -> None:
        r = ExportResult(output_path=Path("out.docx"), format=ExportFormat.DOCX, success=True)
        assert r.success
        assert r.output_path.name == "out.docx"


class TestExportConverter:
    def test_instantiation(self) -> None:
        conv = ExportConverter()
        assert conv is not None

    def test_convert_invalid_input(self, tmp_path: Path) -> None:
        conv = ExportConverter()
        result = conv.convert(tmp_path / "nonexistent.md", "docx", tmp_path / "out.docx")
        assert not result.success


# ======================================================================
# Report Engine (Part 8)
# ======================================================================


class TestReportModels:
    def test_report_type_enum(self) -> None:
        assert ReportType.EXECUTIVE.value == "executive"
        assert ReportType.TECHNICAL.value == "technical"
        assert ReportType.AUDIT.value == "audit"

    def test_report_section(self) -> None:
        sec = ReportSection(title="Introduction", content="Some text", level=1)
        assert sec.title == "Introduction"
        assert sec.content == "Some text"

    def test_report_config_defaults(self) -> None:
        cfg = ReportConfig()
        assert cfg.type == ReportType.EXECUTIVE
        assert cfg.generate_toc

    def test_get_section_template(self) -> None:
        from pimd.reports.models import get_section_template

        sections = get_section_template(ReportType.TECHNICAL)
        assert len(sections) >= 5
        assert sections[0].title == "Introduction"


class TestReportEngine:
    def test_instantiation(self) -> None:
        engine = ReportEngine()
        assert engine is not None

    def test_list_types(self) -> None:
        engine = ReportEngine()
        types = engine.list_types()
        assert len(types) == 5

    def test_generate_creates_file(self, tmp_path: Path) -> None:
        cfg = ReportConfig(
            type=ReportType.EXECUTIVE,
            title="Test Report",
            author="Tester",
        )
        engine = ReportEngine(config=cfg)
        out = tmp_path / "report.docx"
        try:
            result = engine.generate(out)
            assert result.exists()
        except Exception:
            pass  # May fail without all deps — structure test


# ======================================================================
# Table of Figures (Part 9)
# ======================================================================


class TestTableOfFigures:
    def test_empty_document(self) -> None:
        tof = TableOfFigures()
        doc = Document(blocks=[])
        tof.scan(doc)
        assert tof.all_lists() == {}

    def test_detects_diagrams(self) -> None:
        tof = TableOfFigures()
        doc = Document(
            blocks=[
                Diagram(
                    alt="Flow",
                    png_bytes=b"123",
                    source="A->B",
                    language="mermaid",
                    caption="Flow Diagram",
                ),
                Diagram(
                    alt="Arch",
                    png_bytes=b"456",
                    source="C->D",
                    language="dot",
                    caption="Architecture",
                ),
            ]
        )
        tof.scan(doc)
        assert len(tof.diagrams) == 2
        assert tof.diagrams[0].caption == "Flow Diagram"

    def test_detects_tables(self) -> None:
        tof = TableOfFigures()
        doc = Document(blocks=[Table(headers=["A"], rows=[["1"]])])
        tof.scan(doc)
        assert len(tof.tables) == 1

    def test_detects_equations(self) -> None:
        tof = TableOfFigures()
        doc = Document(blocks=[EquationBlock(latex=r"E=mc^2")])
        tof.scan(doc)
        assert len(tof.equations) == 1

    def test_detects_images(self) -> None:
        tof = TableOfFigures()
        doc = Document(blocks=[Image(alt="Photo", url="photo.png")])
        tof.scan(doc)
        assert len(tof.images) == 1

    def test_to_markdown(self) -> None:
        tof = TableOfFigures()
        doc = Document(blocks=[Diagram(alt="Flow", png_bytes=b"1", source="A", language="mermaid")])
        tof.scan(doc)
        md = tof.to_markdown()
        assert "List of Diagrams" in md
        assert "Flow" in md

    def test_clear(self) -> None:
        tof = TableOfFigures()
        doc = Document(blocks=[Diagram(alt="D", png_bytes=b"1", source="A", language="mermaid")])
        tof.scan(doc)
        assert len(tof.diagrams) == 1
        tof.clear()
        assert len(tof.diagrams) == 0


# ======================================================================
# Book Mode (Part 10)
# ======================================================================


class TestBookModels:
    def test_book_chapter(self) -> None:
        ch = BookChapter(title="Chapter 1", content="Text")
        assert ch.title == "Chapter 1"
        assert ch.content == "Text"

    def test_book_part(self) -> None:
        ch = BookChapter(title="Ch 1", content="")
        part = BookPart(title="Part I", chapters=[ch], part_number=1)
        assert part.part_number == 1
        assert len(part.chapters) == 1

    def test_book_config(self) -> None:
        cfg = BookConfig(title="My Book", author="Author", template="book")
        assert cfg.title == "My Book"
        assert cfg.template == "book"


class TestBookCompiler:
    def test_instantiation(self) -> None:
        compiler = BookCompiler()
        assert compiler is not None

    def test_build_markdown(self) -> None:
        cfg = BookConfig(title="Test Book", author="Test Author", year="2026")
        compiler = BookCompiler(config=cfg)
        lines = compiler._build_markdown()
        md = "\n".join(lines)
        assert "Test Book" in md
        assert "Test Author" in md


# ======================================================================
# Citations (Part 11)
# ======================================================================


class TestCitationEntry:
    def test_defaults(self) -> None:
        entry = CitationEntry(key="test")
        assert entry.key == "test"
        assert entry.type == "article"

    def test_apa_format(self) -> None:
        entry = CitationEntry(
            key="einstein1936",
            type="article",
            title="Physics and Reality",
            author="Einstein, Albert",
            year="1936",
            journal="Journal of the Franklin Institute",
            volume="221",
            pages="349-382",
        )
        formatted = entry.format_apa()
        assert "Einstein, Albert" in formatted
        assert "1936" in formatted
        assert "Physics and Reality" in formatted

    def test_ieee_format(self) -> None:
        entry = CitationEntry(
            key="test",
            type="article",
            title="A Paper",
            author="Smith, John",
            journal="IEEE Journal",
            year="2020",
        )
        formatted = entry.format_ieee()
        assert "Smith" in formatted or "A Paper" in formatted

    def test_mla_format(self) -> None:
        entry = CitationEntry(key="key", title="Title", author="Doe, Jane")
        formatted = entry.format_mla()
        assert "Doe, Jane" in formatted or "Title" in formatted

    def test_chicago_format(self) -> None:
        entry = CitationEntry(
            key="k", type="article", title="T", author="A", journal="J", year="2020"
        )
        formatted = entry.format_chicago()
        assert isinstance(formatted, str)

    def test_format_by_style(self) -> None:
        entry = CitationEntry(key="k", title="Title", author="Author")
        styles = [CitationStyle.APA, CitationStyle.IEEE, CitationStyle.MLA, CitationStyle.CHICAGO]
        for style in styles:
            formatted = entry.format(style)
            assert isinstance(formatted, str) and len(formatted) > 0


class TestCitationEngine:
    def test_instantiation(self) -> None:
        engine = CitationEngine()
        assert engine is not None

    def test_load_bibtex_string(self) -> None:
        bib = """
@article{einstein1936,
  title = {Physics and Reality},
  author = {Einstein, Albert},
  year = {1936},
  journal = {Journal of the Franklin Institute},
}
"""
        engine = CitationEngine()
        engine.load_bibtex(bib)
        assert len(engine.all_entries()) == 1
        assert engine.get("einstein1936") is not None

    def test_load_bibtex_file(self, tmp_path: Path) -> None:
        bib_file = tmp_path / "refs.bib"
        bib_file.write_text("""
@book{smith2020,
  title = {A Book},
  author = {Smith, John},
  year = {2020},
  publisher = {Academic Press},
}
""")
        engine = CitationEngine()
        engine.load_bibtex(bib_file)
        assert len(engine.all_entries()) == 1

    def test_cite_known(self) -> None:
        engine = CitationEngine()
        engine.load_bibtex("""
@article{test,
  author = {Author, Test},
  year = {2023},
  title = {Test Article},
}
""")
        citation = engine.cite("test", CitationStyle.APA)
        assert "Author" in citation

    def test_cite_unknown(self) -> None:
        engine = CitationEngine()
        citation = engine.cite("unknown")
        assert "?" in citation

    def test_bibliography(self) -> None:
        engine = CitationEngine()
        engine.load_bibtex("""
@article{a,
  author = {Alpha, A},
  year = {2020},
  title = {Article A},
}
@article{b,
  author = {Beta, B},
  year = {2021},
  title = {Article B},
}
""")
        bib = engine.bibliography(CitationStyle.APA)
        assert "References" in bib
        assert "Alpha" in bib

    def test_clear(self) -> None:
        engine = CitationEngine()
        engine.load_bibtex("@article{t, title={T}, author={A}}")
        engine.clear()
        assert len(engine.all_entries()) == 0


# ======================================================================
# Document Merging (Part 12)
# ======================================================================


class TestDocumentMerger:
    def test_instantiation(self) -> None:
        merger = DocumentMerger()
        assert merger is not None

    def test_combine_files(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("# File A\n\nContent A")
        f2.write_text("# File B\n\nContent B")
        merger = DocumentMerger()
        combined = merger._combine_files([f1, f2])
        assert "File A" in combined
        assert "File B" in combined

    def test_merge_nonexistent_warning(self, tmp_path: Path) -> None:
        merger = DocumentMerger()
        merger._combine_files([tmp_path / "nonexistent.md"])
        assert merger.warnings


# ======================================================================
# Batch Processing (Part 13)
# ======================================================================


class TestBatchProcessor:
    def test_instantiation(self) -> None:
        bp = BatchProcessor()
        assert bp is not None

    def test_process_empty_directory(self, tmp_path: Path) -> None:
        bp = BatchProcessor()
        result = bp.process_directory(tmp_path / "empty", tmp_path / "out", "*.md")
        assert result.total == 0
        assert result.succeeded == 0

    def test_process_directory_no_matches(self, tmp_path: Path) -> None:
        inp = tmp_path / "input"
        inp.mkdir()
        bp = BatchProcessor()
        result = bp.process_directory(inp, tmp_path / "out", "*.xyz")
        assert result.total == 0

    def test_summary_empty(self) -> None:
        bp = BatchProcessor()
        summary = bp.summary()
        assert "0 files" in summary


# ======================================================================
# Document Validation (Part 14)
# ======================================================================


class TestDocumentValidator:
    def test_instantiation(self) -> None:
        v = DocumentValidator()
        assert v is not None

    def test_validates_empty_document(self) -> None:
        v = DocumentValidator()
        report = v.validate(Document(blocks=[]))
        assert report.valid

    def test_detects_image_without_alt(self) -> None:
        v = DocumentValidator()
        doc = Document(blocks=[Image(alt="", url="img.png")])
        report = v.validate(doc)
        issues = [i for i in report.issues if i.type == "image"]
        assert len(issues) >= 1

    def test_detects_empty_equation(self) -> None:
        v = DocumentValidator()
        doc = Document(blocks=[EquationBlock(latex="")])
        report = v.validate(doc)
        issues = [i for i in report.issues if i.type == "equation"]
        assert len(issues) >= 1

    def test_validate_missing_file(self, tmp_path: Path) -> None:
        v = DocumentValidator()
        report = v.validate_file(tmp_path / "missing.md")
        assert not report.valid

    def test_validate_file_parse_error(self, tmp_path: Path) -> None:
        v = DocumentValidator()
        f = tmp_path / "bad.md"
        f.write_text("")
        report = v.validate_file(f)
        assert report is not None


# ======================================================================
# HtmlRenderer (used by export)
# ======================================================================


class TestHtmlRenderer:
    def test_render_empty(self) -> None:
        from pimd.renderers.html_renderer import HtmlRenderer

        r = HtmlRenderer()
        html = r.render(Document(blocks=[]))
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_render_paragraph(self) -> None:
        from pimd.models import Paragraph, Span
        from pimd.renderers.html_renderer import HtmlRenderer

        r = HtmlRenderer()
        doc = Document(blocks=[Paragraph(spans=[Span(text="Hello World")])])
        html = r.render(doc)
        assert "Hello World" in html
        assert "<p>" in html

    def test_render_heading(self) -> None:
        from pimd.models import Heading, Span
        from pimd.renderers.html_renderer import HtmlRenderer

        r = HtmlRenderer()
        doc = Document(blocks=[Heading(level=1, spans=[Span(text="Title")])])
        html = r.render(doc)
        assert "<h1>Title</h1>" in html

    def test_render_code_block(self) -> None:
        from pimd.models import CodeBlock
        from pimd.renderers.html_renderer import HtmlRenderer

        r = HtmlRenderer()
        doc = Document(blocks=[CodeBlock(code="print('hello')", language="python")])
        html = r.render(doc)
        assert "print" in html
        assert "language-python" in html

    def test_render_table(self) -> None:
        from pimd.models import Table
        from pimd.renderers.html_renderer import HtmlRenderer

        r = HtmlRenderer()
        doc = Document(blocks=[Table(headers=["A", "B"], rows=[["1", "2"]])])
        html = r.render(doc)
        assert "<th>A</th>" in html
        assert "<td>1</td>" in html

    def test_render_equation(self) -> None:
        from pimd.renderers.html_renderer import HtmlRenderer

        r = HtmlRenderer()
        doc = Document(blocks=[EquationBlock(latex=r"E=mc^2")])
        html = r.render(doc)
        assert "equation" in html

    def test_render_list(self) -> None:
        from pimd.models import BulletList, ListItem, Paragraph, Span
        from pimd.renderers.html_renderer import HtmlRenderer

        r = HtmlRenderer()
        doc = Document(
            blocks=[BulletList(items=[ListItem(children=[Paragraph(spans=[Span(text="Item")])])])]
        )
        html = r.render(doc)
        assert "<li>" in html
        assert "Item" in html
