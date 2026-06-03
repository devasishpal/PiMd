"""Accessibility validation engine for documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from pimd.models import (
    BulletList,
    CodeBlock,
    Diagram,
    Document,
    Heading,
    Image,
    OrderedList,
    Paragraph,
    Table,
)


class AccessibilitySeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class AccessibilityIssue:
    type: str
    message: str
    block_index: int = -1
    severity: AccessibilitySeverity = AccessibilitySeverity.WARNING
    wcag_criterion: str = ""
    suggestion: str = ""


@dataclass
class HeadingHierarchyIssue(AccessibilityIssue):
    level: int = 0
    expected_level: int = 0


@dataclass
class ImageAltIssue(AccessibilityIssue):
    url: str = ""


@dataclass
class ReadingOrderIssue(AccessibilityIssue):
    pass


@dataclass
class TableAccessibilityIssue(AccessibilityIssue):
    pass


@dataclass
class StructureIssue(AccessibilityIssue):
    pass


@dataclass
class AccessibilityReport:
    valid: bool
    score: float
    issues: list[AccessibilityIssue] = field(default_factory=list)
    document_path: str = ""

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == AccessibilitySeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == AccessibilitySeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == AccessibilitySeverity.INFO)

    def summary(self) -> str:
        return (
            f"{'PASS' if self.valid else 'FAIL'}: "
            f"{self.error_count} errors, {self.warning_count} warnings, "
            f"{self.info_count} info — score {self.score:.0f}/100"
        )

    def to_markdown(self) -> str:
        lines: list[str] = ["# Accessibility Report\n"]
        lines.append(f"**Score:** {self.score:.0f}/100  \n")
        lines.append(f"**Status:** {'PASS' if self.valid else 'FAIL'}  \n")
        lines.append("")
        if not self.issues:
            lines.append("_No issues found._")
            return "\n".join(lines)
        for issue in self.issues:
            icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(
                issue.severity.value, "⚪"
            )
            wcag = f" [WCAG {issue.wcag_criterion}]" if issue.wcag_criterion else ""
            lines.append(f"- {icon} **{issue.type}**: {issue.message}{wcag}")
            if issue.suggestion:
                lines.append(f"  - _Suggestion:_ {issue.suggestion}")
        return "\n".join(lines)


class AccessibilityEngine:
    """Validate document structure and content for accessibility compliance.

    Checks:
    - Image alt text presence
    - Heading hierarchy (no jumps, proper nesting)
    - Table accessibility (headers defined)
    - Reading order
    - Document structure completeness
    """

    def __init__(self) -> None:
        self._max_score = 100

    def validate(
        self, document: Document, source_path: str | Path | None = None
    ) -> AccessibilityReport:
        issues: list[AccessibilityIssue] = []

        self._check_images(document, issues)
        self._check_headings(document, issues)
        self._check_tables(document, issues)
        self._check_reading_order(document, issues)
        self._check_structure(document, issues)

        penalty = sum(
            {
                AccessibilitySeverity.ERROR: 10,
                AccessibilitySeverity.WARNING: 5,
                AccessibilitySeverity.INFO: 1,
            }.get(i.severity, 0)
            for i in issues
        )
        score = max(0, self._max_score - penalty)

        return AccessibilityReport(
            valid=not any(i.severity == AccessibilitySeverity.ERROR for i in issues),
            score=score,
            issues=issues,
            document_path=str(source_path or ""),
        )

    def validate_file(self, path: str | Path) -> AccessibilityReport:
        path = Path(path)
        if not path.is_file():
            return AccessibilityReport(
                valid=False,
                score=0,
                issues=[
                    AccessibilityIssue("file", f"File not found: {path}", severity=AccessibilitySeverity.ERROR)
                ],
                document_path=str(path),
            )
        from pimd.converters.markdown import MarkdownConverter
        content = path.read_text(encoding="utf-8")
        converter = MarkdownConverter()
        try:
            doc = converter.parse_text(content)
        except Exception as exc:
            return AccessibilityReport(
                valid=False,
                score=0,
                issues=[
                    AccessibilityIssue("parse", f"Parse error: {exc}", severity=AccessibilitySeverity.ERROR)
                ],
                document_path=str(path),
            )
        return self.validate(doc, path)

    def _check_images(self, document: Document, issues: list[AccessibilityIssue]) -> None:
        for i, block in enumerate(document.blocks):
            if isinstance(block, Image):
                if not block.alt or not block.alt.strip():
                    issues.append(
                        ImageAltIssue(
                            type="image_alt",
                            message=f"Image at block {i} is missing alt text",
                            block_index=i,
                            severity=AccessibilitySeverity.ERROR,
                            wcag_criterion="1.1.1",
                            suggestion="Add descriptive alt text describing the image content",
                            url=block.url,
                        )
                    )
                elif len(block.alt) < 5:
                    issues.append(
                        ImageAltIssue(
                            type="image_alt",
                            message=f"Image alt text is too short ({len(block.alt)} chars): '{block.alt}'",
                            block_index=i,
                            severity=AccessibilitySeverity.WARNING,
                            wcag_criterion="1.1.1",
                            suggestion="Provide meaningful alt text (5+ characters)",
                            url=block.url,
                        )
                    )
            elif isinstance(block, Diagram):
                if not block.alt or not block.alt.strip():
                    issues.append(
                        ImageAltIssue(
                            type="diagram_alt",
                            message=f"Diagram at block {i} is missing alt text",
                            block_index=i,
                            severity=AccessibilitySeverity.ERROR,
                            wcag_criterion="1.1.1",
                            suggestion="Add descriptive alt text summarizing the diagram",
                            url=block.alt,
                        )
                    )

    def _check_headings(self, document: Document, issues: list[AccessibilityIssue]) -> None:
        prev_level: int | None = None
        for i, block in enumerate(document.blocks):
            if isinstance(block, Heading):
                if prev_level is not None and block.level > prev_level + 1:
                    issues.append(
                        HeadingHierarchyIssue(
                            type="heading_jump",
                            message=(
                                f"Heading '{block.plain_text()}' jumps from level "
                                f"{prev_level} to {block.level} (skipped level {prev_level + 1})"
                            ),
                            block_index=i,
                            level=block.level,
                            expected_level=prev_level + 1,
                            severity=AccessibilitySeverity.WARNING,
                            wcag_criterion="2.4.10",
                            suggestion=f"Use heading level {prev_level + 1} instead of {block.level}",
                        )
                    )
                prev_level = block.level

        if not any(isinstance(b, Heading) for b in document.blocks):
            issues.append(
                HeadingHierarchyIssue(
                    type="no_headings",
                    message="Document has no headings — structure is unclear to screen readers",
                    severity=AccessibilitySeverity.WARNING,
                    wcag_criterion="2.4.10",
                    suggestion="Add at least one heading to structure the document",
                )
            )

        h1_count = sum(1 for b in document.blocks if isinstance(b, Heading) and b.level == 1)
        if h1_count > 1:
            issues.append(
                HeadingHierarchyIssue(
                    type="multiple_h1",
                    message=f"Document has {h1_count} H1 headings (expected 1)",
                    severity=AccessibilitySeverity.WARNING,
                    wcag_criterion="2.4.10",
                    suggestion="Use a single H1 as the document title, nest lower headings",
                )
            )

    def _check_tables(self, document: Document, issues: list[AccessibilityIssue]) -> None:
        for i, block in enumerate(document.blocks):
            if isinstance(block, Table):
                if not block.headers:
                    issues.append(
                        TableAccessibilityIssue(
                            type="table_headers",
                            message=f"Table at block {i} has no header row",
                            block_index=i,
                            severity=AccessibilitySeverity.ERROR,
                            wcag_criterion="1.3.1",
                            suggestion="Define header cells for the first row of the table",
                        )
                    )
                for row_idx, row in enumerate(block.rows):
                    for col_idx, cell in enumerate(row):
                        if len(cell) > 500:
                            issues.append(
                                TableAccessibilityIssue(
                                    type="table_cell_long",
                                    message=(
                                        f"Table cell [{row_idx},{col_idx}] has {len(cell)} "
                                        f"characters (max 500 recommended)"
                                    ),
                                    block_index=i,
                                    severity=AccessibilitySeverity.WARNING,
                                    wcag_criterion="1.4.8",
                                    suggestion="Break long cell content into multiple rows",
                                )
                            )

    def _check_reading_order(self, document: Document, issues: list[AccessibilityIssue]) -> None:
        for i, block in enumerate(document.blocks):
            if isinstance(block, Image) and block.alt and "decorative" in block.alt.lower():
                issues.append(
                    ReadingOrderIssue(
                        type="decorative_image",
                        message=f"Image marked decorative at block {i} — ensure it does not convey information",
                        block_index=i,
                        severity=AccessibilitySeverity.INFO,
                        wcag_criterion="1.1.1",
                        suggestion="Use role='presentation' or empty alt for decorative images",
                    )
                )

    def _check_structure(self, document: Document, issues: list[AccessibilityIssue]) -> None:
        total_blocks = len(document.blocks)
        if total_blocks == 0:
            issues.append(
                StructureIssue(
                    type="empty_document",
                    message="Document is empty — no content blocks found",
                    severity=AccessibilitySeverity.ERROR,
                    wcag_criterion="4.1.1",
                    suggestion="Add content to the document",
                )
            )
        para_count = sum(1 for b in document.blocks if isinstance(b, Paragraph))
        code_count = sum(1 for b in document.blocks if isinstance(b, CodeBlock))
        list_count = sum(
            1 for b in document.blocks if isinstance(b, (OrderedList, BulletList))
        )
        if para_count == 0 and code_count == 0 and list_count == 0 and total_blocks > 0:
            issues.append(
                StructureIssue(
                    type="no_body_content",
                    message="Document has no paragraphs, lists, or code blocks",
                    severity=AccessibilitySeverity.WARNING,
                    wcag_criterion="1.3.1",
                    suggestion="Add body content for screen reader navigation",
                )
            )
