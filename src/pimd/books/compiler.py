"""Book compiler — assemble chapters, parts, appendices into a complete book."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pimd.export.converter import ExportConverter
from pimd.export.models import ExportFormat
from pimd.templates.manager import TemplateManager


@dataclass
class BookChapter:
    """A single chapter in a book."""

    title: str
    content_file: str = ""
    content: str = ""
    level: int = 1
    subsections: list[BookChapter] = field(default_factory=list)


@dataclass
class BookPart:
    """A part grouping multiple chapters."""

    title: str
    chapters: list[BookChapter] = field(default_factory=list)
    part_number: int = 0


@dataclass
class BookConfig:
    """Configuration for book-mode generation."""

    title: str = ""
    subtitle: str = ""
    author: str = ""
    publisher: str = ""
    edition: str = "1st Edition"
    isbn: str = ""
    year: str = ""
    parts: list[BookPart] = field(default_factory=list)
    appendices: list[BookChapter] = field(default_factory=list)
    generate_index: bool = True
    generate_glossary: bool = True
    generate_toc: bool = True
    generate_lof: bool = True
    template: str = "book"
    output_dir: str = ""


class BookCompiler:
    """Compile book content from chapters, parts, and appendices."""

    def __init__(self, config: BookConfig | None = None) -> None:
        self.config = config or BookConfig()
        self.template_manager = TemplateManager()

    def compile(self, output_path: str | Path) -> Path:
        """Compile the complete book to a DOCX file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        lines = self._build_markdown()
        md_path = out.with_suffix(".md")
        md_path.write_text("\n".join(lines), encoding="utf-8")

        exporter = ExportConverter()
        result = exporter.convert(
            md_path,
            ExportFormat.DOCX,
            **{
                "template": self.config.template,
                "cover_page": True,
                "generate_toc": self.config.generate_toc,
            },
        )
        if result.success:
            return result.output_path
        raise RuntimeError(f"Book compilation failed: {result.error}")

    def _build_markdown(self) -> list[str]:
        """Build the full Markdown representation of the book."""
        lines: list[str] = []

        lines.append(f"# {self.config.title}")
        if self.config.subtitle:
            lines.append(f"\n## {self.config.subtitle}\n")
        lines.append(f"\n*{self.config.author}*  \n")
        if self.config.publisher:
            lines.append(f"*{self.config.publisher}*  \n")
        lines.append(f"\n{self.config.edition}, {self.config.year}\n")
        lines.append("\n\\newpage\n")

        if self.config.generate_toc:
            lines.append("# Table of Contents\n")
            lines.append("[TOC]\n")
            lines.append("\\newpage\n")

        for part in self.config.parts:
            lines.append(f"\\part{{{part.title}}}\n")
            lines.append("\\newpage\n")
            for chapter in part.chapters:
                self._render_chapter(lines, chapter)

        if self.config.appendices:
            lines.append("\\appendix\n")
            lines.append("\\newpage\n")
            for i, appendix in enumerate(self.config.appendices):
                appendix.title = f"Appendix {chr(65 + i)}: {appendix.title}"
                self._render_chapter(lines, appendix)

        if self.config.generate_glossary:
            lines.append("# Glossary\n")
            lines.append("\\newpage\n")
            lines.append("*Term* | Definition\n")
            lines.append("------|-----------\n")

        if self.config.generate_index:
            lines.append("# Index\n")
            lines.append("\\newpage\n")
            lines.append("[Index to be generated]\n")

        return lines

    def _render_chapter(self, lines: list[str], chapter: BookChapter) -> None:
        """Render a single chapter to Markdown."""
        prefix = "#" * chapter.level
        lines.append(f"{prefix} {chapter.title}\n")
        if chapter.content:
            lines.append(chapter.content + "\n")
        if chapter.content_file:
            cf = Path(chapter.content_file)
            if cf.is_file():
                lines.append(cf.read_text(encoding="utf-8") + "\n")
        for sub in chapter.subsections:
            self._render_chapter(lines, sub)
        lines.append("\\newpage\n")
