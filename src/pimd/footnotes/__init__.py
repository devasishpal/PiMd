"""Footnote processing and DOCX rendering."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_FOOTNOTE_DEF_RE = re.compile(
    r"^\[\^([^\]]+)\]:\s*(.+?)(?:\n(?=\S)|$)",
    re.MULTILINE | re.DOTALL,
)

_FOOTNOTE_DEF_START_RE = re.compile(
    r"\[\^([^\]]+)\]:\s*",
)

_FOOTNOTE_REF_RE = re.compile(
    r"\[\^([^\]]+)\]",
)

_FOOTNOTE_CONTINUATION_RE = re.compile(
    r"^(?: {4}|\t)(.+)$",
    re.MULTILINE,
)

_NSMAP = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


@dataclass
class FootnoteConfig:
    """Configuration for footnote processing and rendering."""

    enable_backrefs: bool = True
    separator: str = "\u21a9"
    numbering_style: str = "decimal"
    start_number: int = 1
    reference_superscript: bool = True
    reference_brackets: bool = False


@dataclass
class FootnoteDefinition:
    """A single footnote definition with its content and assigned number."""

    key: str
    content: str
    number: int = 0
    multiline_content: list[str] = field(default_factory=list)
    references_count: int = 0

    @property
    def has_content(self) -> bool:
        return bool(self.content) or bool(self.multiline_content)

    @property
    def full_content(self) -> str:
        parts = [self.content] if self.content else []
        parts.extend(self.multiline_content)
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "content": self.content,
            "number": self.number,
            "multiline_content": self.multiline_content,
            "references_count": self.references_count,
        }


@dataclass
class FootnoteCollection:
    """Collection of footnote definitions and cross-references found in text."""

    definitions: dict[str, FootnoteDefinition] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.definitions)

    @property
    def used_count(self) -> int:
        return sum(1 for k in self.definitions if k in self.references)

    @property
    def unused_definitions(self) -> list[FootnoteDefinition]:
        return [d for k, d in self.definitions.items() if k not in set(self.references)]

    @property
    def unresolved_references(self) -> list[str]:
        defined = set(self.definitions)
        return [r for r in self.references if r not in defined]

    def has_key(self, key: str) -> bool:
        return key in self.definitions

    def get_by_number(self, number: int) -> FootnoteDefinition | None:
        for d in self.definitions.values():
            if d.number == number:
                return d
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "definitions": {k: v.to_dict() for k, v in self.definitions.items()},
            "references": self.references,
            "errors": self.errors,
            "count": self.count,
            "used_count": self.used_count,
        }


def parse_footnote_definition(
    text: str, start: int = 0
) -> tuple[FootnoteDefinition | None, int]:
    """Parse a single footnote definition starting at position *start*.

    Returns a tuple of (FootnoteDefinition or None, end_position).
    """
    match = _FOOTNOTE_DEF_START_RE.search(text, start)
    if not match:
        return None, start

    key = "^" + match.group(1)
    content_start = match.end()
    rest = text[content_start:]

    first_line_end = rest.find("\n")
    if first_line_end == -1:
        content = rest.strip()
        end = len(text)
        return FootnoteDefinition(key=key, content=content), end

    first_line = rest[:first_line_end].strip()
    continuation: list[str] = []
    pos = content_start + first_line_end + 1

    while pos < len(text):
        line = text[pos:]
        cont_match = _FOOTNOTE_CONTINUATION_RE.match(line)
        if cont_match:
            continuation.append(cont_match.group(1).strip())
            next_newline = line.find("\n")
            if next_newline == -1:
                pos = len(text)
            else:
                pos += next_newline + 1
        else:
            break

    end = pos
    return FootnoteDefinition(
        key=key,
        content=first_line,
        multiline_content=continuation,
    ), end


def parse_footnote_reference(
    text: str, start: int = 0
) -> tuple[str | None, int]:
    """Parse a single inline footnote reference ``[^key]`` starting at *start*.

    Returns a tuple of (key or None, end_position).
    """
    match = _FOOTNOTE_REF_RE.search(text, start)
    if not match:
        return None, start

    ref_start = match.start()
    if ref_start != start:
        return None, start

    return "^" + match.group(1), match.end()


def extract_footnotes(text: str) -> FootnoteCollection:
    """Extract all footnote definitions and inline references from *text*.

    Returns a :class:`FootnoteCollection` with definitions keyed by their
    identifier and an ordered list of references as they appear.
    """
    collection = FootnoteCollection()

    for match in _FOOTNOTE_DEF_RE.finditer(text):
        key = "^" + match.group(1)
        content = match.group(2).strip()
        if key in collection.definitions:
            collection.errors.append(
                f"Duplicate footnote definition: [{key}]"
            )
        collection.definitions[key] = FootnoteDefinition(
            key=key,
            content=content,
        )

    def_positions = {m.start() for m in _FOOTNOTE_DEF_START_RE.finditer(text)}
    for match in _FOOTNOTE_REF_RE.finditer(text):
        if match.start() not in def_positions:
            collection.references.append("^" + match.group(1))

    return collection


def number_footnotes(collection: FootnoteCollection) -> FootnoteCollection:
    """Assign sequential numbers to footnote definitions.

    Numbering follows the order of first appearance in the reference list.
    Definitions that are never referenced receive no number (0).
    """
    seen: set[str] = set()
    start = 1

    for key in collection.references:
        if key not in collection.definitions:
            continue
        definition = collection.definitions[key]
        definition.references_count += 1
        if key not in seen:
            seen.add(key)
            definition.number = start
            start += 1

    return collection


def render_footnotes_as_markdown(collection: FootnoteCollection) -> str:
    """Render all numbered footnote definitions as Markdown text."""
    lines: list[str] = []
    for key, definition in collection.definitions.items():
        if definition.number == 0:
            continue
        content = definition.full_content
        indent = "\n    " if "\n" in content else " "
        lines.append(f"[^{key}]:{indent}{content}")
    return "\n".join(lines)


def remove_footnote_definitions(text: str) -> str:
    """Strip footnote definition lines from *text*, returning the body only."""
    return _FOOTNOTE_DEF_RE.sub("", text)


def replace_footnote_references(
    text: str, collection: FootnoteCollection
) -> str:
    """Replace ``[^key]`` references with their assigned number.

    Each reference is replaced by a superscript number string
    (e.g. ``[1]`` or ``\u00b9``) depending on configuration.
    """
    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        if key in collection.definitions:
            num = collection.definitions[key].number
            if num > 0:
                return f"[{num}]"
        return match.group(0)

    return _FOOTNOTE_REF_RE.sub(_replacer, text)


def process_footnotes(
    text: str, config: FootnoteConfig | None = None
) -> str:
    """Full pipeline: extract, number, replace, and append footnote definitions."""
    config = config or FootnoteConfig()
    collection = extract_footnotes(text)
    number_footnotes(collection)

    body = remove_footnote_definitions(text)
    body = replace_footnote_references(body, collection)

    rendered = render_footnotes_as_markdown(collection)
    if rendered:
        body = body.rstrip() + "\n\n" + rendered

    return body


def footnote_to_docx_xml(footnote: FootnoteDefinition) -> str:
    """Generate a ``w:footnote`` XML element string for python-docx.

    Produces a full ``<w:footnote>`` element with ``<w:footnoteRef/>``
    mark and the footnote content. Suitable for insertion into the
    ``word/footnotes.xml`` part.
    """
    id_str = str(footnote.number)
    content = _xml_escape(footnote.full_content)

    return (
        f'<w:footnote '
        f'xmlns:w="{_NSMAP["w"]}" '
        f'xmlns:r="{_NSMAP["r"]}" '
        f'w:type="normal" w:id="{id_str}">'
        f"<w:p>"
        f"<w:pPr>"
        f'<w:pStyle w:val="FootnoteText"/>'
        f"</w:pPr>"
        f"<w:r>"
        f"<w:rPr>"
        f'<w:rStyle w:val="FootnoteReference"/>'
        f"</w:rPr>"
        f"<w:footnoteRef/>"
        f"</w:r>"
        f"<w:r>"
        f'<w:t xml:space="preserve"> {content}</w:t>'
        f"</w:r>"
        f"</w:p>"
        f"</w:footnote>"
    )


def merge_footnotes(
    target: FootnoteCollection, source: FootnoteCollection
) -> FootnoteCollection:
    """Merge two footnote collections into one.

    Definitions from *source* are added to *target* when the key does
    not yet exist. Duplicate keys are recorded as errors. References
    are appended in order.
    """
    result = FootnoteCollection(
        definitions=dict(target.definitions),
        references=list(target.references),
        errors=list(target.errors),
    )

    for key, definition in source.definitions.items():
        if key in result.definitions:
            result.errors.append(
                f"Duplicate footnote definition during merge: [{key}]"
            )
        result.definitions[key] = definition

    result.references.extend(source.references)
    result.errors.extend(source.errors)

    return result


def _xml_escape(text: str) -> str:
    """Escape special XML characters in a string."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


__all__ = [
    "FootnoteConfig",
    "FootnoteDefinition",
    "FootnoteCollection",
    "parse_footnote_definition",
    "parse_footnote_reference",
    "extract_footnotes",
    "number_footnotes",
    "render_footnotes_as_markdown",
    "remove_footnote_definitions",
    "replace_footnote_references",
    "process_footnotes",
    "footnote_to_docx_xml",
    "merge_footnotes",
]
