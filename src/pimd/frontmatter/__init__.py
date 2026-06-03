"""Frontmatter metadata extraction and management.

Supports YAML, TOML, and JSON frontmatter blocks at the start of
Markdown files. Provides a unified ``Metadata`` object regardless of
the source format.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class FrontmatterFormat(Enum):
    YAML = "yaml"
    TOML = "toml"
    JSON = "json"
    NONE = "none"


_YAML_HEADER_RE = re.compile(r"^---\s*\n(.*?)\n(?:---|\.\.\.)\s*\n", re.DOTALL)
_TOML_HEADER_RE = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n", re.DOTALL)
_JSON_HEADER_RE = re.compile(r"^---\s*\n(\{.*?\})\s*\n---\s*\n", re.DOTALL)
_JSON_OPEN_BRACE_RE = re.compile(r"^\s*\{")


@dataclass
class Metadata:
    """Unified metadata extracted from a document's frontmatter.

    All field values are normalized to common keys regardless of the
    source format.
    """

    title: str = ""
    author: str = ""
    authors: list[str] = field(default_factory=list)
    date: date | datetime | str | None = None
    description: str = ""
    subject: str = ""
    keywords: list[str] = field(default_factory=list)
    category: str = ""
    tags: list[str] = field(default_factory=list)
    draft: bool = False
    slug: str = ""
    layout: str = ""
    template: str = ""
    language: str = ""
    version: str = ""
    status: str = ""
    custom: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k, v in self.__dict__.items():
            if v is not None and v != "" and v != [] and v != {} and v is not False:
                if isinstance(v, (date, datetime)):
                    d[k] = v.isoformat()
                else:
                    d[k] = v
        return d

    def as_docx_properties(self) -> dict[str, Any]:
        """Return properties suitable for python-docx core properties."""
        props: dict[str, Any] = {}
        if self.title:
            props["title"] = self.title
        if self.author or self.authors:
            props["author"] = self.author or ", ".join(self.authors)
        if self.subject:
            props["subject"] = self.subject
        if self.keywords:
            props["keywords"] = ", ".join(self.keywords)
        if self.description:
            props["comments"] = self.description
        if self.category:
            props["category"] = self.category
        if self.version:
            props["version"] = self.version
        return props


# ── Detection ─────────────────────────────────────────────────────────


def detect_frontmatter(text: str) -> FrontmatterFormat:
    """Detect which frontmatter format (if any) is present in *text*."""
    if _JSON_HEADER_RE.match(text):
        return FrontmatterFormat.JSON
    if _YAML_HEADER_RE.match(text):
        return FrontmatterFormat.YAML
    if _TOML_HEADER_RE.match(text):
        return FrontmatterFormat.TOML
    return FrontmatterFormat.NONE


def extract_raw(text: str) -> tuple[str, str, FrontmatterFormat]:
    """Extract raw frontmatter string from *text*.

    Returns ``(frontmatter_raw, remaining_text, format)``.
    """
    m = _YAML_HEADER_RE.match(text)
    if m:
        return m.group(1), text[m.end() :], FrontmatterFormat.YAML

    m = _TOML_HEADER_RE.match(text)
    if m:
        return m.group(1), text[m.end() :], FrontmatterFormat.TOML

    m = _JSON_HEADER_RE.match(text)
    if m:
        return m.group(1), text[m.end() :], FrontmatterFormat.JSON

    return "", text, FrontmatterFormat.NONE


# ── Parsing ───────────────────────────────────────────────────────────


def parse_frontmatter(
    text: str,
    fmt: FrontmatterFormat | None = None,
) -> Metadata:
    """Parse frontmatter from *text* and return a ``Metadata`` object.

    If *fmt* is ``None``, auto-detect the format.
    """
    if fmt is None:
        fmt = detect_frontmatter(text)

    if fmt == FrontmatterFormat.NONE:
        return Metadata()

    raw, remaining, actual_fmt = extract_raw(text)
    if not raw:
        return Metadata()

    if fmt == FrontmatterFormat.TOML:
        return _parse_toml(raw)
    elif fmt == FrontmatterFormat.JSON:
        return _parse_json(raw)
    else:
        return _parse_yaml(raw)


def parse_frontmatter_from_file(path: str | Path) -> Metadata:
    """Read a file and parse its frontmatter."""
    p = Path(path)
    if not p.is_file():
        return Metadata()
    text = p.read_text(encoding="utf-8", errors="replace")
    return parse_frontmatter(text)


def strip_frontmatter(text: str) -> str:
    """Remove frontmatter from *text*, returning only the body."""
    _, remaining, _ = extract_raw(text)
    return remaining


# ── Internal parsers ──────────────────────────────────────────────────


def _parse_yaml(raw: str) -> Metadata:
    try:
        import yaml
    except ImportError:
        return Metadata(custom={"raw_yaml": raw, "_parse_error": "PyYAML not installed"})

    try:
        data: dict[str, Any] = yaml.safe_load(raw) or {}
    except Exception:
        return Metadata(custom={"raw_yaml": raw, "_parse_error": "YAML parse failed"})

    return _raw_to_metadata(data)


def _parse_toml(raw: str) -> Metadata:
    tomllib = None
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return Metadata(custom={"raw_toml": raw, "_parse_error": "tomllib/tomli not installed"})

    try:
        data = tomllib.loads(raw)
    except Exception:
        return Metadata(custom={"raw_toml": raw, "_parse_error": "TOML parse failed"})

    return _raw_to_metadata(data)


def _parse_json(raw: str) -> Metadata:
    try:
        data = json.loads(raw)
    except Exception:
        return Metadata(custom={"raw_json": raw, "_parse_error": "JSON parse failed"})

    return _raw_to_metadata(data)


def _raw_to_metadata(data: dict[str, Any]) -> Metadata:
    meta = Metadata()

    field_map: dict[str, str] = {
        "title": "title",
        "author": "author",
        "authors": "authors",
        "date": "date",
        "description": "description",
        "subject": "subject",
        "keywords": "keywords",
        "category": "category",
        "tags": "tags",
        "draft": "draft",
        "slug": "slug",
        "layout": "layout",
        "template": "template",
        "language": "language",
        "lang": "language",
        "version": "version",
        "status": "status",
    }

    for src_key, meta_key in field_map.items():
        val = data.get(src_key)
        if val is not None:
            if meta_key == "keywords" and isinstance(val, str):
                val = [k.strip() for k in val.split(",")]
            elif meta_key == "tags" and isinstance(val, str):
                val = [t.strip() for t in val.split(",")]
            elif meta_key == "authors" and isinstance(val, str):
                val = [a.strip() for a in val.split(",")]
            elif meta_key == "date" and isinstance(val, str):
                try:
                    val = datetime.fromisoformat(val)
                except (ValueError, TypeError):
                    pass
            setattr(meta, meta_key, val)

    for k, v in data.items():
        if k not in field_map and k not in ("_parse_error",):
            meta.custom[k] = v

    return meta


__all__ = [
    "FrontmatterFormat",
    "Metadata",
    "detect_frontmatter",
    "extract_raw",
    "parse_frontmatter",
    "parse_frontmatter_from_file",
    "strip_frontmatter",
]
