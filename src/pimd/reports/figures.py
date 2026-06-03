"""Table of Figures — generate lists of diagrams, tables, equations, and figures."""

from __future__ import annotations

from dataclasses import dataclass, field

from pimd.models import Diagram, Document, EquationBlock, Image, Table


@dataclass
class FigureEntry:
    """A single entry in a table of figures."""

    caption: str
    number: int
    page: int = 0
    label: str = ""


@dataclass
class FigureList:
    """A complete list of figures of a given type."""

    title: str
    entries: list[FigureEntry] = field(default_factory=list)


class TableOfFigures:
    """Scan a document and extract lists of figures, tables, equations, etc."""

    def __init__(self) -> None:
        self.diagrams: list[FigureEntry] = []
        self.tables: list[FigureEntry] = []
        self.equations: list[FigureEntry] = []
        self.images: list[FigureEntry] = []

    def scan(self, document: Document) -> None:
        """Scan the document and populate figure lists."""
        diag_num = 0
        table_num = 0
        eq_num = 0
        img_num = 0
        for block in document.blocks:
            if isinstance(block, Diagram):
                diag_num += 1
                self.diagrams.append(
                    FigureEntry(
                        caption=block.caption or block.alt,
                        number=diag_num,
                        label=f"fig:{diag_num}",
                    )
                )
            elif isinstance(block, Table):
                table_num += 1
                self.tables.append(
                    FigureEntry(
                        caption=f"Table {table_num}",
                        number=table_num,
                        label=f"tbl:{table_num}",
                    )
                )
            elif isinstance(block, EquationBlock):
                eq_num += 1
                self.equations.append(
                    FigureEntry(
                        caption=f"Equation {eq_num}",
                        number=eq_num,
                        label=f"eq:{eq_num}",
                    )
                )
            elif isinstance(block, Image):
                img_num += 1
                self.images.append(
                    FigureEntry(
                        caption=block.alt,
                        number=img_num,
                        label=f"img:{img_num}",
                    )
                )

    def all_lists(self) -> dict[str, FigureList]:
        """Return all figure lists keyed by type."""
        result: dict[str, FigureList] = {}
        if self.diagrams:
            result["diagrams"] = FigureList(title="List of Diagrams", entries=self.diagrams)
        if self.tables:
            result["tables"] = FigureList(title="List of Tables", entries=self.tables)
        if self.equations:
            result["equations"] = FigureList(title="List of Equations", entries=self.equations)
        if self.images:
            result["images"] = FigureList(title="List of Figures", entries=self.images)
        return result

    def to_markdown(self) -> str:
        """Render all figure lists as Markdown."""
        lines: list[str] = []
        for list_type, figure_list in self.all_lists().items():
            lines.append(f"# {figure_list.title}\n")
            for entry in figure_list.entries:
                lines.append(f"- **{list_type.title()} {entry.number}:** {entry.caption}")
            lines.append("")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all collected entries."""
        self.diagrams.clear()
        self.tables.clear()
        self.equations.clear()
        self.images.clear()
