"""Document validation engine — check for broken links, missing images, malformed content."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pimd.models import CodeBlock, Document, EquationBlock, Image


@dataclass
class ValidationIssue:
    """A single issue found during document validation."""

    type: str
    message: str
    block_index: int = -1
    severity: str = "warning"


@dataclass
class ValidationReport:
    """Complete validation report for a document."""

    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    document_path: str = ""

    def summary(self) -> str:
        errors = sum(1 for i in self.issues if i.severity == "error")
        warnings = sum(1 for i in self.issues if i.severity == "warning")
        return f"{'PASS' if self.valid else 'FAIL'}: {errors} errors, {warnings} warnings"


class DocumentValidator:
    """Validate documents for common issues."""

    def validate(
        self, document: Document, source_path: str | Path | None = None
    ) -> ValidationReport:
        """Validate a document model.

        Args:
            document: The document to validate.
            source_path: Optional source file path for resolving relative references.

        Returns:
            ValidationReport with all found issues.
        """
        issues: list[ValidationIssue] = []
        base_dir = Path(source_path).parent if source_path else Path.cwd()

        for i, block in enumerate(document.blocks):
            if isinstance(block, Image):
                issues.extend(self._check_image(block, i, base_dir))
            elif isinstance(block, EquationBlock):
                issues.extend(self._check_equation(block, i))
            elif isinstance(block, CodeBlock):
                issues.extend(self._check_code_block(block, i))

        # Check for missing references in links
        self._check_links(document, issues)

        return ValidationReport(
            valid=not any(i.severity == "error" for i in issues),
            issues=issues,
            document_path=str(source_path or ""),
        )

    def validate_file(self, path: str | Path) -> ValidationReport:
        """Parse and validate a file directly."""
        from pimd.converters.markdown import MarkdownConverter

        path = Path(path)
        if not path.is_file():
            return ValidationReport(
                valid=False,
                issues=[ValidationIssue("file", f"File not found: {path}", severity="error")],
                document_path=str(path),
            )
        content = path.read_text(encoding="utf-8")
        converter = MarkdownConverter()
        try:
            doc = converter.parse_text(content)
        except Exception as exc:
            return ValidationReport(
                valid=False,
                issues=[ValidationIssue("parse", f"Parse error: {exc}", severity="error")],
                document_path=str(path),
            )
        return self.validate(doc, path)

    def _check_image(self, block: Image, index: int, base_dir: Path) -> list[ValidationIssue]:
        """Validate an image block."""
        issues: list[ValidationIssue] = []
        if not block.url:
            issues.append(ValidationIssue("image", "Image with empty URL", index))
        elif not block.alt:
            issues.append(ValidationIssue("image", "Image without alt text", index, "warning"))
        else:
            img_path = Path(block.url)
            if not img_path.is_absolute():
                img_path = base_dir / img_path
            if not img_path.is_file():
                issues.append(
                    ValidationIssue("image", f"Image not found: {block.url}", index, "error")
                )
        return issues

    def _check_equation(self, block: EquationBlock, index: int) -> list[ValidationIssue]:
        """Validate an equation block."""
        issues: list[ValidationIssue] = []
        if not block.latex:
            issues.append(ValidationIssue("equation", "Empty equation", index))
        elif block.error:
            issues.append(
                ValidationIssue("equation", f"Equation error: {block.error}", index, "error")
            )
        if block.label:
            pass
        return issues

    def _check_code_block(self, block: CodeBlock, index: int) -> list[ValidationIssue]:
        """Validate a code block."""
        issues: list[ValidationIssue] = []
        if not block.code:
            issues.append(ValidationIssue("code", "Empty code block", index, "warning"))
        return issues

    def _check_links(self, document: Document, issues: list[ValidationIssue]) -> None:
        """Check for broken internal references."""
        import re

        all_text = " ".join(
            block.plain_text() if hasattr(block, "plain_text") else "" for block in document.blocks
        )
        refs = re.findall(r"\\ref\{(\w+)\}", all_text) + re.findall(r"\\label\{(\w+)\}", all_text)
        labels = set()
        for block in document.blocks:
            if isinstance(block, EquationBlock) and block.label:
                labels.add(block.label)
        for ref in refs:
            if ref not in labels:
                issues.append(
                    ValidationIssue("reference", f"Missing reference: {ref}", severity="error")
                )
