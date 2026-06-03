"""Document merging — combine multiple Markdown or HTML files into one document."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pimd.export.converter import ExportConverter
from pimd.export.models import ExportFormat


class DocumentMerger:
    """Merge multiple source files into a single output document."""

    def __init__(self) -> None:
        self._warnings: list[str] = []

    @property
    def warnings(self) -> list[str]:
        return list(self._warnings)

    def merge(
        self,
        input_files: list[str | Path],
        output_path: str | Path,
        format: str | ExportFormat = ExportFormat.DOCX,
        **overrides: Any,
    ) -> Path:
        """Merge multiple input files into one output document.

        Args:
            input_files: List of paths to input files (MD or HTML).
            output_path: Destination for the merged document.
            format: Output format.
            **overrides: Additional export options.

        Returns:
            Path to the merged output file.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        combined = self._combine_files(input_files)
        md_path = out.with_suffix(".md")
        md_path.write_text(combined, encoding="utf-8")

        exporter = ExportConverter()
        result = exporter.convert(md_path, format, output_path=out, **overrides)
        if result.success:
            return result.output_path
        raise RuntimeError(f"Merge failed: {result.error}")

    def _combine_files(self, input_files: list[str | Path]) -> str:
        """Combine multiple input files into a single Markdown string."""
        parts: list[str] = []
        for i, fpath in enumerate(input_files):
            path = Path(fpath)
            if not path.is_file():
                self._warnings.append(f"File not found: {path}")
                continue
            content = path.read_text(encoding="utf-8")
            ext = path.suffix.lower()
            if ext in (".html", ".htm"):
                from pimd.converters.markdown import MarkdownConverter

                converter = MarkdownConverter()
                try:
                    doc = converter.parse_text(content)
                    md_lines: list[str] = []
                    for block in doc.blocks:
                        md_lines.append(block.plain_text())
                    content = "\n".join(md_lines)
                except Exception:
                    pass
            if i > 0:
                parts.append("\n\n---\n\n")
            parts.append(f"# {path.stem}\n\n{content}")
        return "\n".join(parts)
