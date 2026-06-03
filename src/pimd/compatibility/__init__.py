"""Markdown flavor detection and compatibility layer.

Auto-detects the source Markdown flavor and normalizes content so PiMD's
pipeline can process any dialect uniformly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from re import Pattern


class MarkdownFlavor(Enum):
    """Supported Markdown dialects."""

    GFM = "gfm"
    GITLAB = "gitlab"
    MKDOCS = "mkdocs"
    SPHINX = "sphinx"
    DOCUSAURUS = "docusaurus"
    OBSIDIAN = "obsidian"
    QUARTZ = "quartz"
    COMMONMARK = "commonmark"
    UNKNOWN = "unknown"


FLAVOR_ALIASES: dict[str, MarkdownFlavor] = {
    "github": MarkdownFlavor.GFM,
    "gh": MarkdownFlavor.GFM,
    "gl": MarkdownFlavor.GITLAB,
    "readthedocs": MarkdownFlavor.SPHINX,
    "rtd": MarkdownFlavor.SPHINX,
    "foam": MarkdownFlavor.OBSIDIAN,
    "dendron": MarkdownFlavor.OBSIDIAN,
    "hugo": MarkdownFlavor.QUARTZ,
    "jekyll": MarkdownFlavor.QUARTZ,
}

FLAVOR_MIMETYPES: dict[str, MarkdownFlavor] = {
    "text/x-gfm": MarkdownFlavor.GFM,
    "text/x-gitlab": MarkdownFlavor.GITLAB,
}

FLAVOR_EXTENSIONS: dict[str, MarkdownFlavor] = {
    ".mdx": MarkdownFlavor.DOCUSAURUS,
}


# ── Detection signatures ──────────────────────────────────────────────

_FLAVOR_SIGNATURES: list[tuple[MarkdownFlavor, list[Pattern[str]]]] = [
    (
        MarkdownFlavor.GFM,
        [
            re.compile(r"(?im)^\[[\w\- ]+\]:\s*\S+.*$"),  # reference-style links
            re.compile(r"(?im)^- \[[ x]\]"),  # task lists
            re.compile(r"(?im)^> \[!(NOTE|TIP|WARNING|CAUTION)\]"),  # GitHub alerts
            re.compile(r"(?i)\[\!(NOTE|TIP|WARNING|CAUTION|IMPORTANT)\]"),  # GFM alert (variant)
            re.compile(r"\|(.+)\|\n\|[-:| ]+\|\n\|(.+)\|", re.MULTILINE),  # tables
        ],
    ),
    (
        MarkdownFlavor.GITLAB,
        [
            re.compile(r"(?im)^> \[!(NOTE|TIP|WARNING|CAUTION|INFO|SUCCESS|QUESTION|DANGER)\]"),
            re.compile(r"\|(.+)\|\n\|[-:| ]+\|\n\|(.+)\|", re.MULTILINE),
        ],
    ),
    (
        MarkdownFlavor.OBSIDIAN,
        [
            re.compile(r"\[\[[\w\s/.#|]+\]\]"),  # wiki links
            re.compile(r"(?im)^> \[!(NOTE|TIP|WARNING|DANGER|INFO|SUCCESS|QUESTION|ABSTRACT|TODO|FAILURE|BUG|DANGER|EXAMPLE|QUOTE)\]"),  # obsidian callouts
            re.compile(r"!\[\[[\w\s./|]+\]\]"),  # embeds
            re.compile(r"---\n.*?\n(?:tags:|aliases:|cssclass:)", re.DOTALL),  # obsidian-style frontmatter
        ],
    ),
    (
        MarkdownFlavor.SPHINX,
        [
            re.compile(r"\.\.\s+\w+::"),  # directives
            re.compile(r":(?:ref|doc|class|func|mod):`[^`]+`"),  # cross-references
            re.compile(r"\.\.\s+(?:code|code-block|sourcecode)::"),  # code directives
            re.compile(r"\.\.\s+(?:note|warning|tip|important|caution|attention|hint)::"),
        ],
    ),
    (
        MarkdownFlavor.MKDOCS,
        [
            re.compile(r"(?im)^(?:nav|site_name|theme|plugins|markdown_extensions):"),
            re.compile(r"<!--\s*(?:BEGIN|END)\s+\w+\s*-->"),  # mkdocs material blocks
        ],
    ),
    (
        MarkdownFlavor.DOCUSAURUS,
        [
            re.compile(r"(?im)^(?:sidebar_position|sidebar_label|sidebar_class_name):"),
            re.compile(r"---\n.*?\n(?:id:|slug:|sidebar_position:)", re.DOTALL),
            re.compile(r"import\s+\w+\s+from\s+['\"]@site/"),
            re.compile(r"import\s+Admonition|import\s+Tabs"),
            re.compile(r"<Admonition\s+type="),
        ],
    ),
    (
        MarkdownFlavor.QUARTZ,
        [
            re.compile(r"---\n.*?\n(?:title|date|draft|tags):", re.DOTALL),
            re.compile(r"```(?:mermaid|plantuml|graphviz)"),  # Quartz supports diagrams
        ],
    ),
]


@dataclass
class FlavorDetectionResult:
    flavor: MarkdownFlavor = MarkdownFlavor.UNKNOWN
    confidence: float = 0.0
    signals: list[str] = field(default_factory=list)
    path_hint: str | None = None


# ── Public API ────────────────────────────────────────────────────────


def detect_flavor(
    text: str | None = None,
    path: str | Path | None = None,
) -> FlavorDetectionResult:
    """Detect the Markdown flavor from content and/or file path.

    Args:
        text: Markdown content to analyze.
        path: File path (used for extension and naming hints).

    Returns:
        A ``FlavorDetectionResult`` with the best-guess flavor.
    """
    result = FlavorDetectionResult()

    if path is not None:
        p = Path(path)
        ext = p.suffix.lower()
        name = p.name.lower()
        parent = p.parent.name.lower()

        if ext in FLAVOR_EXTENSIONS:
            result.flavor = FLAVOR_EXTENSIONS[ext]
            result.confidence = 0.9
            result.path_hint = str(p)
            return result

        if name == "mkdocs.yml":
            result.flavor = MarkdownFlavor.MKDOCS
            result.confidence = 0.95
            result.path_hint = str(p)
            return result

        if "sidebars" in name or parent == "sidebars":
            result.flavor = MarkdownFlavor.DOCUSAURUS
            result.confidence = 0.8
            result.path_hint = str(p)

        if parent == "_obsidian" or ".obsidian" in str(p):
            result.flavor = MarkdownFlavor.OBSIDIAN
            result.confidence = 0.8
            result.path_hint = str(p)

    if text is None:
        if result.flavor != MarkdownFlavor.UNKNOWN:
            return result
        return FlavorDetectionResult()

    scores: dict[MarkdownFlavor, float] = {}
    for flavor, patterns in _FLAVOR_SIGNATURES:
        for pat in patterns:
            matches = pat.findall(text)
            if matches:
                scores.setdefault(flavor, 0.0)
                scores[flavor] += len(matches) * 0.15
                result.signals.append(f"{flavor.value}: {pat.pattern[:50]}...")

    if not scores:
        result.flavor = MarkdownFlavor.COMMONMARK
        result.confidence = 0.3
        return result

    best_flavor = max(scores, key=scores.get)
    best_score = scores[best_flavor]
    total = sum(scores.values())

    result.flavor = best_flavor
    result.confidence = min(best_score / max(total, 0.01), 1.0)

    if result.flavor == MarkdownFlavor.UNKNOWN and result.confidence < 0.3:
        result.flavor = MarkdownFlavor.COMMONMARK

    return result


def detect_flavor_from_file(
    path: str | Path,
    max_bytes: int = 65536,
) -> FlavorDetectionResult:
    """Detect the Markdown flavor of a file.

    Reads the first *max_bytes* of the file and runs detection
    against both the path and the content.
    """
    p = Path(path)
    if not p.is_file():
        return FlavorDetectionResult(flavor=MarkdownFlavor.UNKNOWN, confidence=0.0)

    try:
        text = p.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except Exception:
        text = None

    return detect_flavor(text=text, path=p)


# ── Compatibility layer ───────────────────────────────────────────────


@dataclass
class CompatTransform:
    """A single compatibility transformation."""

    name: str
    description: str
    transform: str


class CompatibilityLayer:
    """Normalizes content from any supported Markdown flavor into PiMD's
    internal CommonMark-like representation.
    """

    def __init__(self) -> None:
        self._transforms: list[CompatTransform] = []

    def normalize(self, text: str, flavor: MarkdownFlavor | None = None) -> str:
        """Detect flavor (if not provided) and apply transforms.

        Returns the normalized text, plus records which transforms were
        applied (available via ``applied_transforms``).
        """
        self._transforms.clear()

        if flavor is None or flavor == MarkdownFlavor.UNKNOWN:
            detection = detect_flavor(text=text)
            flavor = detection.flavor

        if flavor == MarkdownFlavor.GFM or flavor == MarkdownFlavor.GITLAB:
            text = self._normalize_gfm_alerts(text)
        if flavor == MarkdownFlavor.GITLAB:
            text = self._normalize_gitlab_alerts(text)
        if flavor == MarkdownFlavor.OBSIDIAN:
            text = self._normalize_obsidian_wikilinks(text)
            text = self._normalize_obsidian_callouts(text)
            text = self._normalize_obsidian_embeds(text)
        if flavor == MarkdownFlavor.SPHINX:
            text = self._normalize_sphinx_directives(text)
        if flavor == MarkdownFlavor.MKDOCS:
            text = self._normalize_mkdocs(text)
        if flavor == MarkdownFlavor.DOCUSAURUS:
            text = self._normalize_docusaurus(text)
        if flavor == MarkdownFlavor.QUARTZ:
            text = self._normalize_quartz(text)

        return text

    @property
    def applied_transforms(self) -> list[CompatTransform]:
        return list(self._transforms)

    def _record(self, name: str, description: str, sample: str) -> None:
        self._transforms.append(
            CompatTransform(name=name, description=description, transform=sample[:120])
        )

    # ── Flavor-specific normalizers ───────────────────────────────────

    def _normalize_gfm_alerts(self, text: str) -> str:
        """GitHub Alert blocks → generic blockquote with label."""
        result = re.sub(
            r"(?im)^> \[!(NOTE|TIP|WARNING|CAUTION)\]\s*\n",
            lambda m: self._record(
                "gfm_alert",
                f"GitHub Alert [{m.group(1)}] → blockquote label",
                m.group(0),
            ).__str__() or f"> **{m.group(1).title()}:** ",
            text,
        )
        return result

    def _normalize_gitlab_alerts(self, text: str) -> str:
        """GitLab-specific alert blocks."""
        result = re.sub(
            r"(?im)^> \[!(INFO|SUCCESS|QUESTION|DANGER)\]\s*\n",
            lambda m: self._record(
                "gitlab_alert",
                f"GitLab Alert [{m.group(1)}] → blockquote label",
                m.group(0),
            ).__str__() or f"> **{m.group(1).title()}:** ",
            text,
        )
        return result

    def _normalize_obsidian_wikilinks(self, text: str) -> str:
        """[[Wiki Links]] → [display text](relative/path)."""
        def _replace_wikilink(m: re.Match) -> str:
            self._record("obsidian_wikilink", "[[Wiki Link]] → [text](path)", m.group(0))
            inner = m.group(1)
            if "|" in inner:
                target, display = inner.split("|", 1)
            else:
                target = inner
                display = target.split("/")[-1].replace(".md", "")
            return f"[{display}]({target})"

        result = re.sub(r"\[\[([\w\s/.#|_-]+)\]\]", _replace_wikilink, text)
        return result

    def _normalize_obsidian_callouts(self, text: str) -> str:
        """Obsidian callout blocks → blockquote with bold label."""
        def _replace_callout(m: re.Match) -> str:
            self._record("obsidian_callout", f"Obsidian callout [{m.group(1)}]", m.group(0))
            return f"> **{m.group(1).title()}:** "

        result = re.sub(
            r"(?im)^> \[!(NOTE|TIP|WARNING|DANGER|INFO|SUCCESS|QUESTION|ABSTRACT|TODO|FAILURE|BUG|EXAMPLE|QUOTE)\]([+-]?)\s*$",
            _replace_callout,
            text,
        )
        return result

    def _normalize_obsidian_embeds(self, text: str) -> str:
        """![[Embed]] → ![](path)."""
        def _replace_embed(m: re.Match) -> str:
            self._record("obsidian_embed", "![[Embed]] → ![](path)", m.group(0))
            inner = m.group(1)
            return f"![]({inner})"

        result = re.sub(r"!\[\[([\w\s/.#|_-]+)\]\]", _replace_embed, text)
        return result

    def _normalize_sphinx_directives(self, text: str) -> str:
        """Sphinx directives → fenced code blocks for preservation."""
        def _replace_directive(m: re.Match) -> str:
            self._record("sphinx_directive", f"Sphinx directive {m.group(0)[:40]}", m.group(0))
            directive = m.group(0).strip()
            return f"```{{sphinx}}\n{directive}\n```\n"

        result = re.sub(r"\.\.\s+\w+::[^\n]*(\n(?:\s{3,}[^\n]*)*)*", _replace_directive, text)
        return result

    def _normalize_mkdocs(self, text: str) -> str:
        self._record("mkdocs_metadata", "MkDocs-specific metadata filtered", "")
        lines = []
        for line in text.split("\n"):
            if re.match(r"^\s*(?:nav|site_name|theme|plugins|markdown_extensions):", line):
                continue
            lines.append(line)
        return "\n".join(lines)

    def _normalize_docusaurus(self, text: str) -> str:
        self._record("docusaurus_imports", "Docusaurus JSX imports stripped", "")
        lines = []
        for line in text.split("\n"):
            if re.match(r"^\s*import\s+\w+\s+from\s+['\"]@site/", line):
                continue
            if re.match(r"^\s*import\s+(?:Admonition|Tabs|TabItem)", line):
                continue
            lines.append(line)
        return "\n".join(lines)

    def _normalize_quartz(self, text: str) -> str:
        self._record("quartz_hugo", "Quartz/Hugo frontmatter (if present) preserved", "")
        return text


__all__ = [
    "MarkdownFlavor",
    "FlavorDetectionResult",
    "detect_flavor",
    "detect_flavor_from_file",
    "CompatibilityLayer",
    "CompatTransform",
    "FLAVOR_ALIASES",
    "FLAVOR_EXTENSIONS",
]
