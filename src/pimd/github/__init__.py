"""GitHub-specific Markdown features.

Renders task lists, tables, alerts, footnotes, anchors, and reference
links in a form compatible with PiMD's internal pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TASK_LIST_RE = re.compile(r"^( *[-*+] \[([ xX])\]) (.*)", re.MULTILINE)
_TABLE_RE = re.compile(r"^\|(.+)\|\s*\n\|([-:| ]+)\|\s*\n(\|.+\|\s*\n)*", re.MULTILINE)
_ALERT_RE = re.compile(r"(?im)^> \[!(NOTE|TIP|WARNING|CAUTION|IMPORTANT)\]\s*\n")
_FOOTNOTE_DEF_RE = re.compile(r"^\[(\^[^\]]+)\]:\s*(.*)", re.MULTILINE)
_FOOTNOTE_REF_RE = re.compile(r"\[\^([^\]]+)\]")
_ANCHOR_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_REFERENCE_LINK_DEF_RE = re.compile(r"^\[([^\]]+)\]:\s*(\S+)(?:\s+(?:\"([^\"]*)\"|'([^']*)'|\(([^)]*)\)))?", re.MULTILINE)
_REFERENCE_LINK_REF_RE = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")


@dataclass
class GitHubFeaturesConfig:
    enable_task_lists: bool = True
    enable_tables: bool = True
    enable_alerts: bool = True
    enable_footnotes: bool = True
    enable_anchors: bool = True
    enable_reference_links: bool = True


@dataclass
class TaskList:
    checked: bool
    text: str
    indent: int = 0


@dataclass
class TableCell:
    text: str
    align: str = "left"


@dataclass
class TableRow:
    cells: list[TableCell] = field(default_factory=list)


@dataclass
class TableData:
    headers: list[str] = field(default_factory=list)
    rows: list[TableRow] = field(default_factory=list)


@dataclass
class Footnote:
    key: str
    text: str
    number: int = 0


@dataclass
class Anchor:
    level: int
    text: str
    slug: str = ""


def slugify(text: str) -> str:
    """Generate a GitHub-style anchor slug from heading text."""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


# ── Task list ─────────────────────────────────────────────────────────


def extract_task_lists(text: str) -> list[TaskList]:
    """Extract task list items from *text*."""
    tasks: list[TaskList] = []
    for m in _TASK_LIST_RE.finditer(text):
        indent = len(m.group(1)) - len(m.group(1).lstrip())
        tasks.append(
            TaskList(
                checked=m.group(2).lower() == "x",
                text=m.group(3).strip(),
                indent=indent,
            )
        )
    return tasks


def render_task_list_html(tasks: list[TaskList]) -> str:
    """Render task list items as HTML."""
    parts: list[str] = ['<ul class="task-list">']
    for task in tasks:
        checked = ' checked=""' if task.checked else ""
        parts.append(
            f'  <li class="task-list-item">'
            f'<input type="checkbox" disabled{checked}/> '
            f"{task.text}</li>"
        )
    parts.append("</ul>")
    return "\n".join(parts)


def render_task_list_markdown(tasks: list[TaskList]) -> str:
    """Render task list items as Markdown."""
    lines: list[str] = []
    for task in tasks:
        prefix = " " * task.indent
        mark = "x" if task.checked else " "
        lines.append(f"{prefix}- [{mark}] {task.text}")
    return "\n".join(lines)


def process_task_lists(text: str) -> str:
    """Convert task lists into a universal format (HTML)."""
    return _TASK_LIST_RE.sub(
        lambda m: f'<input type="checkbox" disabled{" checked" if m.group(2).lower() == "x" else ""}/> {m.group(3)}',
        text,
    )


# ── Tables ────────────────────────────────────────────────────────────


def parse_table(text: str) -> TableData | None:
    """Parse a GitHub Flavored Markdown table into *TableData*."""
    m = _TABLE_RE.match(text)
    if not m:
        return None

    header_line = m.group(1)
    separator_line = m.group(2)

    headers = [h.strip() for h in header_line.split("|") if h.strip()]
    aligns = _parse_alignments(separator_line)

    body_text = m.group(0).split("\n")[2:]
    rows: list[TableRow] = []

    for line in body_text:
        line = line.strip()
        if not line or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c or cells.index(c) > 0]
        if len(cells) > len(headers):
            cells = cells[: len(headers)]
        elif len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        row_cells = [
            TableCell(text=cells[i] if i < len(cells) else "", align=aligns[i] if i < len(aligns) else "left")
            for i in range(len(headers))
        ]
        rows.append(TableRow(cells=row_cells))

    return TableData(headers=headers, rows=rows)


def _parse_alignments(sep: str) -> list[str]:
    cols = sep.split("|")
    cols = [c.strip() for c in cols if c.strip()]
    aligns: list[str] = []
    for col in cols:
        if col.startswith(":") and col.endswith(":"):
            aligns.append("center")
        elif col.endswith(":"):
            aligns.append("right")
        else:
            aligns.append("left")
    return aligns


def render_table_html(table: TableData) -> str:
    """Render *TableData* as an HTML table."""
    parts: list[str] = ["<table>", "  <thead>", "    <tr>"]
    for h in table.headers:
        parts.append(f"      <th>{h}</th>")
    parts.extend(["    </tr>", "  </thead>", "  <tbody>"])
    for row in table.rows:
        parts.append("    <tr>")
        for cell in row.cells:
            align_attr = f' align="{cell.align}"' if cell.align != "left" else ""
            parts.append(f"      <td{align_attr}>{cell.text}</td>")
        parts.append("    </tr>")
    parts.extend(["  </tbody>", "</table>"])
    return "\n".join(parts)


# ── Alerts ────────────────────────────────────────────────────────────


def process_alerts(text: str) -> str:
    """Convert GitHub/GitLab Alert blocks to decorated blockquotes."""
    def _replace(m: re.Match) -> str:
        level = m.group(1).upper()
        icons = {
            "NOTE": "ℹ️",
            "TIP": "💡",
            "WARNING": "⚠️",
            "CAUTION": "⚠️",
            "IMPORTANT": "❗",
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "QUESTION": "❓",
            "DANGER": "🚨",
        }
        icon = icons.get(level, "")
        return f"> **{icon} {level.title()}:** "

    return _ALERT_RE.sub(_replace, text)


# ── Footnotes ─────────────────────────────────────────────────────────


@dataclass
class FootnotesCollection:
    definitions: dict[str, Footnote] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)


def extract_footnotes(text: str) -> FootnotesCollection:
    """Extract footnote definitions and references from *text*."""
    collection = FootnotesCollection()

    for m in _FOOTNOTE_DEF_RE.finditer(text):
        key = m.group(1)
        content = m.group(2).strip()
        collection.definitions[key] = Footnote(key=key, text=content)

    for m in _FOOTNOTE_REF_RE.finditer(text):
        ref = m.group(1)
        if ref not in collection.references:
            collection.references.append(ref)

    # Assign numbers
    for i, ref in enumerate(collection.references, 1):
        if ref in collection.definitions:
            collection.definitions[ref].number = i

    return collection


def process_footnotes(text: str) -> str:
    """Inline footnote references with superscript numbers.

    Footnote definitions are appended at the end of the document.
    """
    collection = extract_footnotes(text)

    # Remove definitions from body
    result = _FOOTNOTE_DEF_RE.sub("", text)

    # Replace references
    def _replace_ref(m: re.Match) -> str:
        key = m.group(1)
        if key in collection.definitions:
            num = collection.definitions[key].number
            return f"<sup id='fnref-{num}'><a href='#fn-{num}'>{num}</a></sup>"
        return m.group(0)

    result = _FOOTNOTE_REF_RE.sub(_replace_ref, result)

    # Append footnote definitions
    if collection.definitions:
        result += "\n\n---\n\n"
        for key, fn in collection.definitions.items():
            result += f"<sup id='fn-{fn.number}'>{fn.number}</sup> {fn.text} [↩](#fnref-{fn.number})\n\n"

    return result


# ── Anchors ───────────────────────────────────────────────────────────


def generate_anchors(text: str) -> str:
    """Generate GitHub-style anchor IDs for headings.

    Adds ``{#slug}`` after each heading line.
    """
    def _replace(m: re.Match) -> str:
        hashes = m.group(1)
        heading_text = m.group(2).strip()
        # Check for existing explicit anchor
        explicit = re.search(r"\{#([^}]+)\}\s*$", heading_text)
        if explicit:
            slug = explicit.group(1)
            heading_text = re.sub(r"\s*\{#[^}]+\}\s*$", "", heading_text)
            return f"{hashes} {heading_text} {{#{slug}}}"
        slug = slugify(heading_text)
        return f"{hashes} {heading_text} {{#{slug}}}"

    return _ANCHOR_RE.sub(_replace, text)


def extract_anchors(text: str) -> list[Anchor]:
    """Extract all heading anchors from *text*."""
    anchors: list[Anchor] = []
    for m in _ANCHOR_RE.finditer(text):
        level = len(m.group(1))
        heading_text = m.group(2).strip()
        # Use explicit anchor if present
        explicit = re.search(r"\{#([^}]+)\}", heading_text)
        if explicit:
            slug = explicit.group(1)
            heading_text = re.sub(r"\s*\{#[^}]+\}\s*$", "", heading_text)
        else:
            slug = slugify(heading_text)
        anchors.append(Anchor(level=level, text=heading_text, slug=slug))
    return anchors


# ── Reference links ───────────────────────────────────────────────────


@dataclass
class ReferenceLink:
    key: str
    url: str
    title: str = ""


def extract_reference_links(text: str) -> dict[str, ReferenceLink]:
    """Extract reference link definitions from *text*."""
    links: dict[str, ReferenceLink] = {}
    for m in _REFERENCE_LINK_DEF_RE.finditer(text):
        key = m.group(1).strip().lower()
        url = m.group(2).strip()
        title = m.group(3) or m.group(4) or m.group(5) or ""
        links[key] = ReferenceLink(key=key, url=url, title=title)
    return links


def resolve_reference_links(text: str) -> str:
    """Resolve all reference-style links inline.

    E.g. ``[text][ref]`` → ``[text](url)``.
    """
    links = extract_reference_links(text)

    def _replace_ref(m: re.Match) -> str:
        display = m.group(1)
        key = (m.group(2) or display).strip().lower()
        link = links.get(key)
        if link:
            title_attr = f' "{link.title}"' if link.title else ""
            return f"[{display}]({link.url}{title_attr})"
        return m.group(0)

    result = _REFERENCE_LINK_REF_RE.sub(_replace_ref, text)

    # Also handle implicit: [text][] → [text](url) if text is a key
    implicit_re = re.compile(r"\[([^\]]+)\]\[\]")
    result = implicit_re.sub(
        lambda m: (
            f"[{m.group(1)}]({links[m.group(1).strip().lower()].url})"
            if m.group(1).strip().lower() in links
            else m.group(0)
        ),
        result,
    )

    # Remove definition lines
    result = _REFERENCE_LINK_DEF_RE.sub("", result)

    return result


# ── Batch processing ──────────────────────────────────────────────────


class GitHubFeaturesProcessor:
    """Apply all GitHub-flavor Markdown features to a text."""

    def __init__(self, config: GitHubFeaturesConfig | None = None) -> None:
        self.config = config or GitHubFeaturesConfig()
        self._stats: dict[str, int] = {}

    def process(self, text: str) -> str:
        """Apply all enabled features to *text*."""
        self._stats = {}

        result = text

        if self.config.enable_reference_links:
            before = len(result)
            result = resolve_reference_links(result)
            self._stats["reference_links_resolved"] = len(result) - before

        if self.config.enable_task_lists:
            tasks = extract_task_lists(result)
            self._stats["task_list_items"] = len(tasks)
            result = process_task_lists(result)

        if self.config.enable_alerts:
            result = process_alerts(result)
            # Count alerts
            self._stats["alerts"] = len(_ALERT_RE.findall(text))

        if self.config.enable_footnotes:
            before = len(_FOOTNOTE_DEF_RE.findall(result))
            result = process_footnotes(result)
            self._stats["footnotes"] = before

        if self.config.enable_anchors:
            result = generate_anchors(result)
            self._stats["anchors"] = len(_ANCHOR_RE.findall(result))

        return result

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)


__all__ = [
    "GitHubFeaturesConfig",
    "GitHubFeaturesProcessor",
    "TaskList",
    "TableData",
    "TableRow",
    "TableCell",
    "Footnote",
    "Anchor",
    "ReferenceLink",
    "FootnotesCollection",
    "extract_task_lists",
    "render_task_list_html",
    "render_task_list_markdown",
    "process_task_lists",
    "parse_table",
    "render_table_html",
    "process_alerts",
    "extract_footnotes",
    "process_footnotes",
    "generate_anchors",
    "extract_anchors",
    "extract_reference_links",
    "resolve_reference_links",
    "slugify",
]
