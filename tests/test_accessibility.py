"""Tests for the Accessibility Engine."""

from pathlib import Path

import pytest

from pimd.accessibility import AccessibilityEngine
from pimd.accessibility.engine import AccessibilitySeverity
from pimd.models import (
    Diagram,
    Document,
    Heading,
    Image,
    Paragraph,
    Span,
    Table,
)


@pytest.fixture
def engine() -> AccessibilityEngine:
    return AccessibilityEngine()


class TestImageAltText:
    def test_image_with_alt(self, engine: AccessibilityEngine) -> None:
        doc = Document(
            blocks=[
                Heading(level=1, spans=[Span(text="Title")]),
                Paragraph(spans=[Span(text="Content")]),
                Image(alt="A red car", url="car.png"),
            ]
        )
        report = engine.validate(doc)
        assert report.valid
        assert report.score >= 90

    def test_image_without_alt(self, engine: AccessibilityEngine) -> None:
        doc = Document(
            blocks=[
                Heading(level=1, spans=[Span(text="Title")]),
                Paragraph(spans=[Span(text="Body")]),
                Image(alt="", url="car.png"),
            ]
        )
        report = engine.validate(doc)
        assert not report.valid
        image_errors = [i for i in report.issues if i.severity == AccessibilitySeverity.ERROR and "image" in i.type]
        assert len(image_errors) >= 1

    def test_image_without_alt_count(self, engine: AccessibilityEngine, monkeypatch: pytest.MonkeyPatch) -> None:
        doc = Document(
            blocks=[
                Image(alt="", url="1.png"),
                Image(alt="", url="2.png"),
            ]
        )
        report = engine.validate(doc)
        image_errors = [i for i in report.issues if "image" in i.type]
        assert len(image_errors) >= 1

    def test_diagram_without_alt(self, engine: AccessibilityEngine) -> None:
        doc = Document(blocks=[Diagram(alt="", png_bytes=b"abc", source="graph TD;", language="mermaid")])
        report = engine.validate(doc)
        assert not report.valid
        assert report.error_count == 1

    def test_image_alt_too_short(self, engine: AccessibilityEngine) -> None:
        doc = Document(
            blocks=[
                Heading(level=1, spans=[Span(text="Title")]),
                Paragraph(spans=[Span(text="Body")]),
                Image(alt="img", url="test.png"),
            ]
        )
        report = engine.validate(doc)
        image_issues = [i for i in report.issues if "image_alt" in i.type]
        assert len(image_issues) >= 1


class TestHeadingHierarchy:
    def test_flat_headings_valid(self, engine: AccessibilityEngine) -> None:
        doc = Document(
            blocks=[
                Heading(level=1, spans=[Span(text="Title")]),
                Heading(level=2, spans=[Span(text="Section 1")]),
                Heading(level=2, spans=[Span(text="Section 2")]),
            ]
        )
        report = engine.validate(doc)
        assert report.valid

    def test_heading_jump(self, engine: AccessibilityEngine) -> None:
        doc = Document(
            blocks=[
                Heading(level=1, spans=[Span(text="Title")]),
                Heading(level=3, spans=[Span(text="Skip H2")]),
            ]
        )
        report = engine.validate(doc)
        assert len(report.issues) >= 1
        assert any("heading_jump" in i.type for i in report.issues)
        assert report.warning_count >= 1

    def test_no_headings(self, engine: AccessibilityEngine) -> None:
        doc = Document(blocks=[Paragraph(spans=[Span(text="Hello")])])
        report = engine.validate(doc)
        assert any("no_headings" in i.type for i in report.issues)

    def test_multiple_h1(self, engine: AccessibilityEngine) -> None:
        doc = Document(
            blocks=[
                Heading(level=1, spans=[Span(text="Title")]),
                Heading(level=1, spans=[Span(text="Another Title")]),
            ]
        )
        report = engine.validate(doc)
        assert any("multiple_h1" in i.type for i in report.issues)


class TestTableAccessibility:
    def test_table_with_headers(self, engine: AccessibilityEngine) -> None:
        doc = Document(blocks=[Table(headers=["Name", "Age"], rows=[["Alice", "30"]])])
        report = engine.validate(doc)
        assert report.valid

    def test_table_without_headers(self, engine: AccessibilityEngine) -> None:
        doc = Document(blocks=[Table(rows=[["Alice", "30"]])])
        report = engine.validate(doc)
        assert not report.valid
        assert any("table_headers" in i.type for i in report.issues)


class TestReadingOrder:
    def test_decorative_image(self, engine: AccessibilityEngine) -> None:
        doc = Document(blocks=[Image(alt="decorative divider", url="divider.png")])
        report = engine.validate(doc)
        decorative_issues = [i for i in report.issues if "decorative_image" in i.type]
        assert len(decorative_issues) >= 1


class TestStructure:
    def test_empty_document(self, engine: AccessibilityEngine) -> None:
        doc = Document(blocks=[])
        report = engine.validate(doc)
        assert not report.valid
        assert any("empty_document" in i.type for i in report.issues)

    def test_no_body_content(self, engine: AccessibilityEngine) -> None:
        doc = Document(blocks=[Heading(level=1, spans=[Span(text="Title")])])
        report = engine.validate(doc)
        assert any("no_body_content" in i.type for i in report.issues)


class TestFileValidation:
    def test_file_not_found(self, engine: AccessibilityEngine) -> None:
        report = engine.validate_file(Path("/nonexistent/file.md"))
        assert not report.valid
        assert report.score == 0

    def test_temporary_markdown_file(self, engine: AccessibilityEngine, tmp_path: Path) -> None:
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\n\nThis is a paragraph.\n\n![alt](image.png)", encoding="utf-8")
        report = engine.validate_file(md_file)
        assert report.document_path == str(md_file)


class TestReportFormat:
    def test_to_markdown_no_issues(self, engine: AccessibilityEngine) -> None:
        doc = Document(blocks=[Paragraph(spans=[Span(text="Hello")])])
        report = engine.validate(doc)
        md = report.to_markdown()
        assert "PASS" in md or "# Accessibility Report" in md

    def test_summary_format(self, engine: AccessibilityEngine) -> None:
        doc = Document(blocks=[Image(alt="", url="test.png")])
        report = engine.validate(doc)
        summary = report.summary()
        assert "FAIL" in summary
        assert str(report.score) in summary


class TestAccessibilityScore:
    def test_perfect_score(self, engine: AccessibilityEngine) -> None:
        doc = Document(
            blocks=[
                Heading(level=1, spans=[Span(text="Title")]),
                Paragraph(spans=[Span(text="Content")]),
                Image(alt="A test image with meaningful description", url="test.png"),
            ]
        )
        report = engine.validate(doc)
        assert report.score >= 90

    def test_penalized_score(self, engine: AccessibilityEngine) -> None:
        doc = Document(
            blocks=[
                Image(alt="", url="1.png"),
                Image(alt="", url="2.png"),
            ]
        )
        report = engine.validate(doc)
        assert report.score <= 80
