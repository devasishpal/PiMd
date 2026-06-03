"""Report generation engine — builds, formats, and exports reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pimd.export.converter import ExportConverter
from pimd.export.models import ExportFormat
from pimd.reports.models import (
    ReportConfig,
    ReportSection,
    ReportType,
    get_section_template,
)
from pimd.templates.manager import TemplateManager


class ReportEngine:
    """Generate structured reports from configuration and content."""

    def __init__(self, config: ReportConfig | None = None) -> None:
        self.config = config or ReportConfig()
        self.template_manager = TemplateManager()

    def generate(
        self,
        output_path: str | Path,
        sections: list[ReportSection] | None = None,
        **overrides: Any,
    ) -> Path:
        """Generate a complete report document.

        Args:
            output_path: Where to write the output file.
            sections: Optional list of sections. Uses template defaults if omitted.
            **overrides: Override report config fields.

        Returns:
            Path to the generated output file.
        """
        cfg = ReportConfig(**(self.config.__dict__ | overrides))
        if sections is None:
            sections = get_section_template(cfg.type)
        cfg.sections = sections

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        markdown = self._build_markdown(cfg)
        md_path = out.with_suffix(".md")
        md_path.write_text(markdown, encoding="utf-8")

        exporter = ExportConverter()
        result = exporter.convert(
            md_path,
            ExportFormat.DOCX,
            **{
                "template": cfg.template,
                "cover_page": cfg.cover_page,
                "generate_toc": cfg.generate_toc,
                "page_numbers": cfg.page_numbers,
                "watermark": cfg.watermark,
            },
        )
        if result.success:
            return result.output_path
        raise RuntimeError(f"Report generation failed: {result.error}")

    def _build_markdown(self, cfg: ReportConfig) -> str:
        """Build the full Markdown content from sections."""
        lines: list[str] = []

        if cfg.include_executive_summary and cfg.type != ReportType.EXECUTIVE:
            lines.append("# Executive Summary\n")
            lines.append("This report provides an overview of key findings and recommendations.\n")

        for section in cfg.sections:
            self._render_section(lines, section)

        if cfg.include_references:
            lines.append("# References\n")
            lines.append("[References to be added]\n")

        return "\n".join(lines)

    def _render_section(self, lines: list[str], section: ReportSection) -> None:
        """Render a single section and its subsections to Markdown."""
        prefix = "#" * section.level
        lines.append(f"{prefix} {section.title}\n")
        if section.content.strip():
            lines.append(section.content.strip() + "\n")
        for sub in section.subsections:
            self._render_section(lines, sub)

    def list_types(self) -> list[dict[str, str]]:
        """List available report types with descriptions."""
        return [
            {"type": t.value, "description": f"{t.name.replace('_', ' ').title()} reports"}
            for t in ReportType
        ]
