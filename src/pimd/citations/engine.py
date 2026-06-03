"""Citation engine — parse BibTeX, format in any style, generate bibliographies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CitationStyle(str, Enum):
    """Supported citation styles."""

    APA = "apa"
    IEEE = "ieee"
    MLA = "mla"
    CHICAGO = "chicago"


@dataclass
class CitationEntry:
    """A single bibliographic entry."""

    key: str
    type: str = "article"
    title: str = ""
    author: str = ""
    year: str = ""
    journal: str = ""
    booktitle: str = ""
    publisher: str = ""
    address: str = ""
    volume: str = ""
    number: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    isbn: str = ""
    note: str = ""

    def format_apa(self) -> str:
        """Format as APA."""
        auth = self.author if self.author else "Unknown"
        year = f"({self.year})" if self.year else "(n.d.)"
        title = self.title if self.title else "Untitled"
        journal = self._italic(self.journal) if self.journal else ""
        vol = self.volume if self.volume else ""
        pages = self.pages if self.pages else ""
        parts = [f"{auth} {year}.", title]
        if self.type == "article" and journal:
            parts.append(journal)
            if vol:
                parts.append(f"*{vol}*")
            if pages:
                parts.append(f", {pages}")
        elif self.type in ("book", "inbook"):
            if self.publisher:
                parts.append(self.publisher)
        elif self.type == "inproceedings":
            if self.booktitle:
                parts.append(f"In {self._italic(self.booktitle)}")
        if self.doi:
            parts.append(f"https://doi.org/{self.doi}")
        return ". ".join(parts) + "."

    def format_ieee(self) -> str:
        """Format as IEEE."""
        auth = self._format_authors_initials()
        title = f'"{self.title},"' if self.title else ""
        if self.type == "article":
            journal = self.journal if self.journal else ""
            vol = f"vol. {self.volume}" if self.volume else ""
            no = f"no. {self.number}" if self.number else ""
            pages = f"pp. {self.pages}" if self.pages else ""
            year = self.year if self.year else ""
            parts = [a for a in [auth, title, journal, vol, no, pages, year] if a]
            return ", ".join(parts) + "."
        return f"{auth}, {title}" if title else auth

    def format_mla(self) -> str:
        """Format as MLA."""
        auth = self.author if self.author else ""
        title = f'"{self.title}."' if self.title else ""
        journal = self.journal if self.journal else ""
        vol = self.volume if self.volume else ""
        year = self.year if self.year else ""
        parts = [auth, title, journal, vol, year]
        return " ".join(p for p in parts if p) + "."

    def format_chicago(self) -> str:
        """Format as Chicago."""
        auth = self.author if self.author else ""
        title = self.title if self.title else ""
        year = f"({self.year})" if self.year else ""
        if self.type == "article":
            journal = self.journal if self.journal else ""
            vol = self.volume if self.volume else ""
            parts = [auth, title, journal, vol, year]
            return ". ".join(p for p in parts if p) + "."
        return (
            f"{auth}. {title}. {self.publisher}, {year}." if self.publisher else f"{auth}. {title}."
        )

    def format(self, style: CitationStyle) -> str:
        """Format entry in the given style."""
        style_map = {
            CitationStyle.APA: self.format_apa,
            CitationStyle.IEEE: self.format_ieee,
            CitationStyle.MLA: self.format_mla,
            CitationStyle.CHICAGO: self.format_chicago,
        }
        fmt = style_map.get(style)
        return fmt() if fmt else self.format_apa()

    @staticmethod
    def _italic(text: str) -> str:
        return f"*{text}*"

    def _format_authors_initials(self) -> str:
        """Format author names as initials + last name (IEEE style)."""
        if not self.author:
            return ""
        parts = self.author.split(" and ")
        formatted: list[str] = []
        for part in parts:
            names = part.strip().split(", ")
            if len(names) >= 2:
                formatted.append(f"{names[1][0]}. {names[0]}")
            else:
                formatted.append(part.strip())
        return ", ".join(formatted)


_BIBTEX_ENTRY = re.compile(r"@(\w+)\s*\{(\w+)\s*,", re.DOTALL)


def _parse_bibtex_string(content: str) -> list[CitationEntry]:
    """Parse BibTeX content and return citation entries."""
    entries: list[CitationEntry] = []
    pos = 0
    while True:
        match = _BIBTEX_ENTRY.search(content, pos)
        if not match:
            break
        entry_type = match.group(1).lower()
        key = match.group(2)
        start = match.end()
        depth = 1
        i = start
        while i < len(content) and depth > 0:
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
            i += 1
        body = content[start : i - 1]
        entry = CitationEntry(key=key, type=entry_type)
        _parse_bibtex_fields(body, entry)
        entries.append(entry)
        pos = i
    return entries


def _parse_bibtex_fields(body: str, entry: CitationEntry) -> None:
    """Parse BibTeX field assignments from entry body."""
    i = 0
    while i < len(body):
        # Skip whitespace and commas
        while i < len(body) and body[i] in " \t\n\r,":
            i += 1
        if i >= len(body):
            break
        # Match field name
        name_match = re.match(r"(\w+)\s*=\s*\{", body[i:])
        if not name_match:
            i += 1
            continue
        field_name = name_match.group(1).lower()
        i += name_match.end()
        # Read balanced braces for value
        depth = 1
        start_val = i
        while i < len(body) and depth > 0:
            if body[i] == "{":
                depth += 1
            elif body[i] == "}":
                depth -= 1
            i += 1
        field_value = body[start_val : i - 1].strip()
        if hasattr(entry, field_name):
            setattr(entry, field_name, field_value)


class CitationEngine:
    """Manage citations, parse BibTeX, and generate formatted bibliographies."""

    def __init__(self) -> None:
        self._entries: dict[str, CitationEntry] = {}
        self._cited_keys: set[str] = set()

    def load_bibtex(self, source: str | Path) -> None:
        """Load citations from a BibTeX file or string."""
        if isinstance(source, Path) or (isinstance(source, str) and Path(source).is_file()):
            content = Path(source).read_text(encoding="utf-8")
        else:
            content = source
        entries = _parse_bibtex_string(content)
        for entry in entries:
            self._entries[entry.key] = entry

    def get(self, key: str) -> CitationEntry | None:
        """Retrieve a citation entry, marking it as cited."""
        entry = self._entries.get(key)
        if entry is not None:
            self._cited_keys.add(key)
        return entry

    def cite(self, key: str, style: CitationStyle = CitationStyle.APA) -> str:
        """Generate an inline citation for the given key."""
        entry = self.get(key)
        if entry is None:
            return f"[?{key}]"
        if style == CitationStyle.IEEE:
            return self._format_ieee_inline(key)
        if style == CitationStyle.APA:
            return f"({entry.author}, {entry.year})" if entry.author and entry.year else f"[{key}]"
        if style == CitationStyle.MLA:
            return f"({entry.author})" if entry.author else f"[{key}]"
        if style == CitationStyle.CHICAGO:
            return f"{entry.author} {entry.year}" if entry.author and entry.year else f"[{key}]"
        return f"[{key}]"

    def bibliography(self, style: CitationStyle = CitationStyle.APA) -> str:
        """Generate a formatted bibliography of all cited entries."""
        if not self._cited_keys:
            self._cited_keys = set(self._entries.keys())
        sorted_keys = sorted(self._cited_keys)
        if style == CitationStyle.IEEE:
            sorted_keys = sorted(sorted_keys, key=lambda k: list(self._entries.keys()).index(k))
        lines: list[str] = ["# References\n"]
        for key in sorted_keys:
            entry = self._entries.get(key)
            if entry is not None:
                lines.append(entry.format(style))
                lines.append("")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all entries and citation state."""
        self._entries.clear()
        self._cited_keys.clear()

    def all_entries(self) -> list[CitationEntry]:
        """Return all loaded entries."""
        return list(self._entries.values())

    def _format_ieee_inline(self, key: str) -> str:
        """Format an IEEE-style bracketed citation."""
        keys = sorted(self._entries.keys())
        try:
            num = keys.index(key) + 1
            return f"[{num}]"
        except ValueError:
            return f"[?{key}]"
