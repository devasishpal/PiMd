"""Template validation — ensure templates are complete and well-formed."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pimd.templates.models import Template


@dataclass
class ValidationResult:
    """Result of template validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_template(template: Template) -> ValidationResult:
    """Validate a single template for completeness and correctness."""
    errors: list[str] = []
    warnings: list[str] = []

    if not template.name:
        errors.append("Template name is required")

    if template.docx_template_path is not None:
        if not template.docx_template_path.is_file():
            warnings.append(
                f"DOCX template '{template.docx_template_path}' not found — will use defaults"
            )

    cfg = template.config
    if cfg.margin_top < 0 or cfg.margin_bottom < 0 or cfg.margin_left < 0 or cfg.margin_right < 0:
        errors.append("Margins must be non-negative")

    if cfg.default_font_size < 6 or cfg.default_font_size > 72:
        warnings.append(f"Unusual font size: {cfg.default_font_size}")

    if cfg.line_spacing < 0.5 or cfg.line_spacing > 3.0:
        warnings.append(f"Unusual line spacing: {cfg.line_spacing}")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_template_directory(path: Path) -> list[ValidationResult]:
    """Validate all templates in a directory."""
    from pimd.templates.loader import discover_templates

    results: list[ValidationResult] = []
    for tpl in discover_templates():
        results.append(validate_template(tpl))
    return results
