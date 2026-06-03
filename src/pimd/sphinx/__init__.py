"""Sphinx documentation ecosystem support."""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "RSTDirective",
    "RSTRole",
    "ToctreeEntry",
    "SphinxConfig",
    "SphinxProject",
    "SphinxProjectConverter",
    "RSTtoMarkdownConverter",
    "parse_rst_directive",
    "parse_rst_role",
    "convert_rst_to_markdown",
    "parse_conf_py",
    "parse_toctree",
    "convert_toctree_to_nav",
    "detect_sphinx_project",
    "convert_sphinx_to_pimd",
    "resolve_sphinx_ref",
    "normalize_directive",
    "strip_rst_roles",
]

_DIRECTIVE_PATTERN = re.compile(
    r"^\.\.\s+(?:(?P<domain>py|c|cpp|js|ruby|fortran|rest|mysql|tex):)?(?P<name>[a-zA-Z_][a-zA-Z0-9_:.-]*)\s*::\s*(?P<args>.*)$",
    re.MULTILINE,
)

_DIRECTIVE_OPTION_PATTERN = re.compile(r"^\s+:(?P<key>[a-zA-Z_][a-zA-Z0-9_-]*):\s*(?P<value>.*)$", re.MULTILINE)

_CONTENT_CONTINUATION = re.compile(r"^\s{3,}")

_ROLE_PATTERN = re.compile(
    r"(?P<full>(?P<domain>py|c|cpp|js|ruby|fortran|rest|mysql|tex):)?"
    r"(?P<name>[a-zA-Z_][a-zA-Z0-9_:.-]*):"
    r"`(?P<title>(?:[^`]|\\`)+?)(?:\s+<(?P<target>[^>]+)>)?`",
)

_REF_PATTERN = re.compile(r":(?:ref|doc|class|func|mod|term|numref|cite):`([^`]+)`")

_ROLE_STRIP_PATTERN = re.compile(r":(?:ref|doc|class|func|mod|term|numref|cite|py:class|py:func|py:mod|py:meth|py:attr):`([^`]+)`")

_TOCTREE_DECL_PATTERN = re.compile(r"^\s*\.\.\s+toctree\s*::\s*$", re.MULTILINE)

_TOCTREE_OPTION_PATTERN = re.compile(r"^\s+:(?P<key>[a-zA-Z_][a-zA-Z0-9_-]*):\s*(?P<value>.*)$")

_TOCTREE_ENTRY_PATTERN = re.compile(r"^\s+(?P<path>\S[\S ]*)$")

_ADMONITION_MAP: dict[str, str] = {
    "note": "note",
    "warning": "warning",
    "tip": "tip",
    "important": "important",
    "caution": "caution",
    "attention": "attention",
    "danger": "danger",
    "error": "error",
    "hint": "hint",
    "seealso": "seealso",
}

_VERSION_DIRECTIVES = {"deprecated", "versionadded", "versionchanged"}

_SPHINX_MARKERS = {"conf.py", "index.rst", "make.bat", "Makefile", "source/conf.py"}

_KNOWN_DIRECTIVES: set[str] = set(_ADMONITION_MAP.keys()) | _VERSION_DIRECTIVES | {
    "code-block",
    "code",
    "sourcecode",
    "toctree",
    "contents",
    "sectionauthor",
    "moduleauthor",
    "codeauthor",
    "highlight",
    "default-domain",
    "glossary",
    "centered",
    "raw",
    "include",
    "image",
    "figure",
    "table",
    "list-table",
    "csv-table",
    "math",
    "eq",
    "eval-rst",
    "js:function",
    "js:class",
    "js:data",
    "js:attribute",
    "js:module",
    "py:function",
    "py:class",
    "py:module",
    "py:method",
    "py:attribute",
    "py:data",
    "py:decorator",
    "py:exception",
    "c:function",
    "c:macro",
    "c:type",
    "c:member",
    "c:var",
    "cpp:function",
    "cpp:class",
    "cpp:type",
    "cpp:enum",
    "cpp:member",
    "cpp:var",
    "ruby:method",
    "ruby:class",
    "ruby:module",
    "fortran:subroutine",
    "fortran:function",
    "rest:directive",
    "rest:role",
}

_ADMONITION_TITLE_OVERRIDE: dict[str, str] = {
    "seealso": "See Also",
    "deprecated": "Deprecated",
    "versionadded": "New in version",
    "versionchanged": "Changed in version",
}


@dataclass
class RSTDirective:
    """A parsed RST directive with its components."""

    name: str
    arguments: str = ""
    options: dict[str, str] = field(default_factory=dict)
    content: list[str] = field(default_factory=list)
    domain: str = ""
    line: int = 0


@dataclass
class RSTRole:
    """A parsed RST interpreted text role."""

    name: str
    target: str = ""
    text: str = ""
    domain: str = ""
    raw: str = ""


@dataclass
class ToctreeEntry:
    """A single entry in a Sphinx toctree."""

    path: str
    title: str = ""
    glob: bool = False
    maxdepth: int = 0
    hidden: bool = False
    titlesonly: bool = False


@dataclass
class SphinxConfig:
    """Parsed Sphinx configuration from conf.py."""

    project: str = ""
    version: str = ""
    release: str = ""
    author: str = ""
    copyright: str = ""
    language: str = "en"
    extensions: list[str] = field(default_factory=list)
    html_theme: str = "alabaster"
    html_theme_options: dict[str, Any] = field(default_factory=dict)
    html_static_path: list[str] = field(default_factory=list)
    html_extra_path: list[str] = field(default_factory=list)
    html_css_files: list[str] = field(default_factory=list)
    html_js_files: list[str] = field(default_factory=list)
    html_logo: str = ""
    html_favicon: str = ""
    html_title: str = ""
    html_short_title: str = ""
    latex_elements: dict[str, Any] = field(default_factory=dict)
    latex_documents: list[tuple[str, ...]] = field(default_factory=list)
    man_pages: list[tuple[str, ...]] = field(default_factory=list)
    texinfo_documents: list[tuple[str, ...]] = field(default_factory=list)
    epub_title: str = ""
    epub_author: str = ""
    epub_language: str = "en"
    master_doc: str = "index"
    source_suffix: dict[str, str] = field(default_factory=lambda: {".rst": "restructuredtext"})
    exclude_patterns: list[str] = field(default_factory=list)
    nitpicky: bool = False
    suppress_warnings: list[str] = field(default_factory=list)
    rst_prolog: str = ""
    rst_epilog: str = ""
    numfig: bool = False
    smartquotes: bool = True
    needs_sphinx: str = ""
    _raw: dict[str, Any] = field(default_factory=dict)

    @property
    def theme(self) -> str:
        return self.html_theme

    @property
    def source_dir(self) -> str:
        return "source" if self.html_theme else "."


@dataclass
class SphinxProject:
    """Full representation of a Sphinx documentation project."""

    root: Path
    source_dir: Path
    build_dir: Path
    config: SphinxConfig = field(default_factory=SphinxConfig)
    pages: dict[str, Path] = field(default_factory=dict)
    inventories: dict[str, dict[str, str]] = field(default_factory=dict)
    toctrees: list[ToctreeEntry] = field(default_factory=list)
    static_dir: Path | None = None
    templates_dir: Path | None = None


@dataclass
class ConversionResult:
    """Result of converting a Sphinx project to PiMD."""

    total_pages: int = 0
    converted: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)
    output_dir: str = ""
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def parse_rst_directive(text: str, offset: int = 0) -> tuple[RSTDirective | None, int]:
    """Parse the first RST directive found in *text* starting from *offset*.

    Returns a tuple of (RSTDirective or None, end_position).
    """
    tail = text[offset:]
    m = _DIRECTIVE_PATTERN.search(tail)
    if not m:
        return None, offset

    directive = RSTDirective(
        name=m.group("name"),
        arguments=m.group("args").strip(),
        domain=m.group("domain") or "",
        line=offset + tail[: m.start()].count("\n") + 1,
    )

    body_start = m.end()
    body_lines = tail[body_start:].split("\n")
    option_mode = True
    content_mode = False
    options: dict[str, str] = {}
    content: list[str] = []

    for line in body_lines:
        if content_mode:
            if line.strip() == "":
                content.append("")
            elif line.startswith(" ") or line.startswith("\t"):
                content.append(line)
            else:
                break
            continue

        if option_mode:
            om = _DIRECTIVE_OPTION_PATTERN.match(line)
            if om:
                options[om.group("key")] = om.group("value").strip()
                continue
            if line.strip() == "":
                option_mode = False
                continue
            if line.startswith(" ") or line.startswith("\t"):
                option_mode = False
                content_mode = True
                content.append(line)
                continue
            if not line.strip():
                option_mode = False
                continue
            break

        if line.strip() == "":
            continue
        if line.startswith(" ") or line.startswith("\t"):
            content_mode = True
            content.append(line)
            continue
        break

    # Determine end position
    consumed = body_start
    seen_content = False
    for line in body_lines:
        if line.strip() == "" and not seen_content:
            consumed += 1  # blank lines between options and content
        elif line.startswith(" ") or line.startswith("\t"):
            seen_content = True
            consumed += len(line) + 1
        else:
            break

    directive.options = options
    directive.content = content

    return directive, consumed


def parse_rst_role(text: str) -> RSTRole | None:
    """Parse the first RST role found in *text*.

    Returns an RSTRole or None.
    """
    m = _ROLE_PATTERN.search(text)
    if not m:
        return None

    target = m.group("target") or m.group("title")
    return RSTRole(
        name=m.group("name"),
        target=target.strip() if target else "",
        text=m.group("title"),
        domain=m.group("domain").rstrip(":") if m.group("domain") else "",
        raw=m.group("full"),
    )


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def _admonition_to_markdown(directive: RSTDirective) -> str:
    admon_type = _ADMONITION_MAP.get(directive.name, "note")
    title_override = _ADMONITION_TITLE_OVERRIDE.get(directive.name)

    title = directive.arguments or title_override or admon_type.capitalize()
    body = "\n".join(directive.content)
    if title_override and directive.arguments:
        title = f"{title_override}: {directive.arguments}"
    return f"> [!{admon_type}]\n> **{title}**\n" + "".join(
        f"> {line}\n" for line in body.split("\n") if line.strip()
    )


def _version_to_markdown(directive: RSTDirective) -> str:
    label = _ADMONITION_TITLE_OVERRIDE.get(directive.name, directive.name.capitalize())
    version = directive.arguments
    body = "\n".join(directive.content)
    parts = [f"> [!note]\n> **{label}: {version}**"]
    if body.strip():
        parts.append("".join(f"> {line}\n" for line in body.split("\n") if line.strip()))
    return "\n".join(parts)


def _code_block_to_markdown(directive: RSTDirective) -> str:
    lang = directive.arguments or ""
    lines = directive.content
    if not lines:
        return ""
    code = "\n".join(lines)
    return f"```{lang}\n{code}\n```\n"


def _image_to_markdown(directive: RSTDirective) -> str:
    uri = directive.arguments
    alt = directive.options.get("alt", "")
    width = directive.options.get("width", "")
    if width:
        return f'![{alt}]({uri} "{width}")\n'
    return f"![{alt}]({uri})\n"


def _figure_to_markdown(directive: RSTDirective) -> str:
    caption_parts = [line for line in directive.content if line.strip() and not line.strip().startswith("..")]
    uri = directive.arguments
    alt = directive.options.get("alt", "")
    caption = caption_parts[0] if caption_parts else alt
    return f"![{caption}]({uri})\n\n*{caption}*\n"


def _table_to_markdown(directive: RSTDirective) -> str:
    lines = directive.content
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("+") or stripped.startswith("|"):
            continue
        if stripped.startswith("===") or stripped.startswith("---"):
            continue
        cells = [c.strip() for c in stripped.split("  ") if c.strip()]
        if cells:
            rows.append(cells)
    if not rows:
        return "\n".join(lines) + "\n"
    col_count = max(len(r) for r in rows)
    separator = "| " + " | ".join("---" for _ in range(col_count)) + " |"
    md_rows: list[str] = []
    for i, row in enumerate(rows):
        padded = row + [""] * (col_count - len(row))
        md_rows.append("| " + " | ".join(padded) + " |")
        if i == 0:
            md_rows.append(separator)
    return "\n".join(md_rows) + "\n"


def _list_table_to_markdown(directive: RSTDirective) -> str:
    return _table_to_markdown(directive)


def _math_to_markdown(directive: RSTDirective) -> str:
    body = "\n".join(directive.content)
    if not body.strip():
        body = directive.arguments
    return f"$$\n{body}\n$$\n"


def _include_to_markdown(directive: RSTDirective) -> str:
    path = directive.arguments
    return f"<!-- include: {path} -->\n"


def _raw_to_markdown(directive: RSTDirective) -> str:
    return ""


def _toctree_to_markdown(directive: RSTDirective) -> str:
    entries = []
    for line in directive.content:
        stripped = line.strip()
        if stripped:
            entries.append(stripped)
    if not entries:
        return ""
    md = "<!-- toctree -->\n"
    for entry in entries:
        md += f"- [{entry}]({entry}.md)\n"
    return md


_DIRECTIVE_HANDLERS: dict[str, Callable[[RSTDirective], str]] = {
    "note": _admonition_to_markdown,
    "warning": _admonition_to_markdown,
    "tip": _admonition_to_markdown,
    "important": _admonition_to_markdown,
    "caution": _admonition_to_markdown,
    "attention": _admonition_to_markdown,
    "danger": _admonition_to_markdown,
    "error": _admonition_to_markdown,
    "hint": _admonition_to_markdown,
    "seealso": _admonition_to_markdown,
    "deprecated": _version_to_markdown,
    "versionadded": _version_to_markdown,
    "versionchanged": _version_to_markdown,
    "code-block": _code_block_to_markdown,
    "code": _code_block_to_markdown,
    "sourcecode": _code_block_to_markdown,
    "image": _image_to_markdown,
    "figure": _figure_to_markdown,
    "table": _table_to_markdown,
    "list-table": _list_table_to_markdown,
    "csv-table": _list_table_to_markdown,
    "math": _math_to_markdown,
    "eq": _math_to_markdown,
    "include": _include_to_markdown,
    "raw": _raw_to_markdown,
    "toctree": _toctree_to_markdown,
}

_DOMAIN_TITLE_MAP: dict[str, str] = {
    "py:class": "Class",
    "py:function": "Function",
    "py:module": "Module",
    "py:method": "Method",
    "py:attribute": "Attribute",
    "py:data": "Data",
    "py:decorator": "Decorator",
    "py:exception": "Exception",
    "c:function": "C Function",
    "c:macro": "C Macro",
    "c:type": "C Type",
    "c:member": "C Member",
    "c:var": "C Variable",
    "cpp:function": "C++ Function",
    "cpp:class": "C++ Class",
    "cpp:type": "C++ Type",
    "cpp:enum": "C++ Enum",
    "cpp:member": "C++ Member",
    "cpp:var": "C++ Variable",
    "js:function": "JS Function",
    "js:class": "JS Class",
    "js:module": "JS Module",
    "js:data": "JS Data",
    "js:attribute": "JS Attribute",
    "ruby:method": "Ruby Method",
    "ruby:class": "Ruby Class",
    "ruby:module": "Ruby Module",
    "fortran:subroutine": "Fortran Subroutine",
    "fortran:function": "Fortran Function",
}


def normalize_directive(directive: RSTDirective) -> str:
    """Convert a single RSTDirective to Markdown."""
    full_name = f"{directive.domain}:{directive.name}" if directive.domain else directive.name
    handler = _DIRECTIVE_HANDLERS.get(full_name) or _DIRECTIVE_HANDLERS.get(directive.name)

    if handler:
        return handler(directive)

    domain_title = _DOMAIN_TITLE_MAP.get(full_name)
    if domain_title:
        sig = directive.arguments
        body = "\n".join(directive.content)
        parts = [f"### {domain_title}: {sig}"]
        if body.strip():
            parts.append(body)
        return "\n\n".join(parts) + "\n"

    if directive.content:
        body = "\n".join(directive.content)
        return f"<!-- {directive.name}: {directive.arguments} -->\n{body}\n"

    return f"<!-- {directive.name}: {directive.arguments} -->\n"


# ---------------------------------------------------------------------------
# Role / reference helpers
# ---------------------------------------------------------------------------


def strip_rst_roles(text: str) -> str:
    r"""Replace RST roles like :role:`target` with Markdown links.

    Handles both :domain:role:`target` and :role:`text <target>` forms.
    """
    def _replace_role(m: re.Match[str]) -> str:
        inner = m.group(1)
        if "<" in inner and inner.endswith(">"):
            parts = inner.rsplit("<", 1)
            text = parts[0].strip()
            target = parts[1].rstrip(">").strip()
        else:
            text = inner
            target = inner
        return f"[{text}]({_ref_url(target)})"

    return _REF_PATTERN.sub(_replace_role, text)


def resolve_sphinx_ref(ref: str, inv_data: dict | None = None) -> str | None:
    """Resolve a Sphinx cross-reference to a URL.

    Returns a URL string or None if resolution fails.
    """
    if inv_data:
        url = inv_data.get(ref)
        if url:
            return url

    if ref.startswith("http://") or ref.startswith("https://"):
        return ref

    parts = ref.rsplit("/", 1)
    anchor = ""
    if len(parts) > 1:
        ref = parts[0]
        anchor = f"#{parts[1]}"

    if ref.endswith(".html") or ref.endswith(".htm"):
        return f"{ref}{anchor}"
    if "." in ref and not ref.startswith("_"):
        module_parts = ref.rsplit(".", 1)
        if len(module_parts) == 2:
            return f"{module_parts[0]}.html#{module_parts[1]}{anchor}"
    return f"{ref}.html{anchor}"


def _ref_url(target: str) -> str:
    if target.startswith("http://") or target.startswith("https://"):
        return target
    if "#" in target:
        return target
    if target.endswith(".html"):
        return target
    return f"{target}.html"


def _convert_inline_roles(text: str) -> str:
    """Convert all RST roles found in inline text to Markdown equivalents."""
    def _repl(m: re.Match[str]) -> str:
        domain = m.group("domain") or ""
        name = m.group("name")
        title = m.group("title")
        target = m.group("target") or title
        full_name = f"{domain}{name}" if domain else name

        ref_types = {"ref", "doc", "numref", "cite"}
        literal_types = {"class", "func", "mod", "meth", "attr", "obj", "exc", "data", "const", "keyword", "option", "envvar", "token", "guilabel", "menuselection", "file", "kbd", "mailheader", "mimetype", "newsgroup", "program", "regexp", "samp", "dfn", "abbr"}

        if full_name in ref_types:
            return f"[{title}]({_ref_url(target)})"
        if full_name in literal_types:
            return f"[`{title}`]({_ref_url(target)})"
        if full_name.startswith("py:") or full_name.startswith("c:") or full_name.startswith("cpp:") or full_name.startswith("js:"):
            return f"[`{title}`]({_ref_url(target)})"
        if name == "emphasis":
            return f"*{title}*"
        if name == "strong":
            return f"**{title}**"
        if name == "literal":
            return f"`{title}`"
        if name == "title-reference":
            return f"*{title}*"

        return f"[{title}]({_ref_url(target)})"

    return _ROLE_PATTERN.sub(_repl, text)


def _rst_headings_to_markdown(text: str) -> str:
    """Convert RST section headings to Markdown ATX headings."""
    lines = text.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            heading_chars = {"=", "-", "~", "^", '"'}
            if next_line and all(c in heading_chars for c in next_line) and len(next_line) >= len(line) * 0.5:
                char = next_line[0]
                level = {"=": 1, "-": 2, "~": 3, "^": 4, '"': 5}.get(char, 6)
                result.append(f"{'#' * level} {line}")
                i += 2
                continue
        result.append(line)
        i += 1
    return "\n".join(result)


def _rst_literal_blocks(text: str) -> str:
    """Convert RST literal blocks (::) to fenced code blocks."""
    lines = text.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.rstrip().endswith("::") and not re.match(r"^\s+", line):
            prefix = line.rstrip()[:-2]
            if prefix.strip():
                result.append(prefix)
            result.append("```")
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].strip() == ""):
                content_line = lines[i][4:] if lines[i].startswith("    ") else lines[i][1:] if lines[i].startswith(" ") else lines[i]
                result.append(content_line)
                i += 1
            result.append("```")
            continue
        result.append(line)
        i += 1
    return "\n".join(result)


def _rst_inline_literals(text: str) -> str:
    """Convert ``inline literals`` to backtick code spans."""
    return re.sub(r"``(.+?)``", r"`\1`", text)


def _rst_nested_inline(text: str) -> str:
    """Convert :math: roles and other inline RST."""
    text = re.sub(r":math:`(.+?)`", r"$\1$", text)
    text = re.sub(r":ref:`([^`]+)`", lambda m: f"[{m.group(1)}]({m.group(1).lower().replace(' ', '-')}.html)", text)
    text = re.sub(r":doc:`([^`]+)`", lambda m: f"[{m.group(1)}]({m.group(1)}.html)", text)
    return text


def _rst_inline_markup(text: str) -> str:
    """Convert *emphasis* and **strong** handling."""
    text = re.sub(r"\*(\S.*?\S)\*", r"*\1*", text)
    text = re.sub(r"\*\*(\S.*?\S)\*\*", r"**\1**", text)
    return text


def _line_offset(text: str, line_num: int) -> int:
    """Return the offset of the start of the given 1-indexed line."""
    lines = text.split("\n")
    offset = 0
    for _ in range(min(line_num - 1, len(lines))):
        offset += len(lines[_]) + 1
    return offset


def _directive_end_offset(text: str, offset: int) -> int:
    """Return the offset just past the directive body starting at *offset*."""
    tail = text[offset:]
    lines = tail.split("\n")
    if not lines:
        return offset
    pos = len(lines[0]) + 1
    for line in lines[1:]:
        if line.strip() == "":
            pos += len(line) + 1
        elif line.startswith(" ") or line.startswith("\t"):
            pos += len(line) + 1
        else:
            break
    if pos > len(tail):
        pos = len(tail)
    return offset + pos


def convert_rst_to_markdown(text: str) -> str:
    """Convert full reStructuredText content to Markdown.

    Handles directives, roles, headings, literal blocks, inline markup,
    and Sphinx-specific constructs.
    """
    offset = 0
    parts: list[str] = []
    while offset < len(text):
        directive, end = parse_rst_directive(text, offset=offset)
        if directive is None:
            parts.append(text[offset:])
            break
        lines_before = text[offset : offset + max(0, _line_offset(text, directive.line) - offset)]
        parts.append(lines_before)
        parts.append(normalize_directive(directive))
        offset = _directive_end_offset(text, _line_offset(text, directive.line))
        while offset < len(text) and text[offset] == "\n":
            offset += 1
    text = "".join(parts)
    text = _rst_headings_to_markdown(text)
    text = _rst_literal_blocks(text)
    text = _rst_inline_literals(text)
    text = _rst_nested_inline(text)
    text = _convert_inline_roles(text)
    text = _rst_inline_markup(text)
    text = _cleanup_blank_lines(text)
    return text.strip()


def _cleanup_blank_lines(text: str) -> str:
    """Collapse excessive blank lines."""
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


# ---------------------------------------------------------------------------
# toctree helpers
# ---------------------------------------------------------------------------


def parse_toctree(text: str) -> list[ToctreeEntry]:
    """Parse a Sphinx toctree directive text into structured entries."""
    lines = text.split("\n")
    entries: list[ToctreeEntry] = []
    in_toctree = False
    options: dict[str, str] = {}

    for line in lines:
        if not in_toctree:
            m = _TOCTREE_DECL_PATTERN.match(line)
            if m:
                in_toctree = True
            continue

        om = _TOCTREE_OPTION_PATTERN.match(line)
        if om:
            options[om.group("key")] = om.group("value").strip()
            continue

        em = _TOCTREE_ENTRY_PATTERN.match(line)
        if em:
            entry_text = em.group("path").strip()
            title = ""
            path = entry_text
            if "<" in entry_text and entry_text.endswith(">"):
                parts = entry_text.rsplit("<", 1)
                title = parts[0].strip()
                path = parts[1].rstrip(">").strip()

            is_glob = "*" in path or "?" in path
            entries.append(
                ToctreeEntry(
                    path=path,
                    title=title,
                    glob=is_glob,
                    maxdepth=int(options.get("maxdepth", "0")),
                    hidden="hidden" in options,
                    titlesonly="titlesonly" in options,
                )
            )
            continue

        if in_toctree and line.strip() and not line.startswith(" "):
            break

    return entries


def convert_toctree_to_nav(toctree: list[ToctreeEntry]) -> list[dict]:
    """Convert a parsed toctree to a navigation structure."""
    nav: list[dict] = []
    for entry in toctree:
        item: dict[str, Any] = {
            "path": entry.path,
            "title": entry.title or Path(entry.path).stem.replace("_", " ").title(),
        }
        if entry.glob:
            item["glob"] = True
        if entry.maxdepth > 0:
            item["maxdepth"] = entry.maxdepth
        if entry.hidden:
            item["hidden"] = True
        if entry.titlesonly:
            item["titlesonly"] = True
        nav.append(item)
    return nav


# ---------------------------------------------------------------------------
# conf.py parsing
# ---------------------------------------------------------------------------


def parse_conf_py(path: str | Path) -> SphinxConfig:
    """Parse a Sphinx ``conf.py`` file and return a ``SphinxConfig``.

    Uses safe AST parsing to evaluate string expressions.
    """
    config = SphinxConfig()
    filepath = Path(path)

    if not filepath.exists():
        return config

    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return config

    _simple_types = {ast.Constant, ast.Name, ast.List, ast.Dict, ast.Tuple, ast.Call, ast.UnaryOp, ast.BinOp, ast.Attribute, ast.Subscript}

    def _safe_eval(node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            _safe_names = {
                "True": True, "False": False, "None": None,
                "rst": "rst", "md": "md", "markdown": "markdown",
            }
            return _safe_names.get(node.id, node.id)
        if isinstance(node, ast.List):
            return [_safe_eval(el) for el in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(_safe_eval(el) for el in node.elts)
        if isinstance(node, ast.Dict):
            return {_safe_eval(k): _safe_eval(v) for k, v in zip(node.keys, node.values) if k is not None}
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -_safe_eval(node.operand)
            if isinstance(node.op, ast.Not):
                return not _safe_eval(node.operand)
        if isinstance(node, ast.BinOp):
            left = _safe_eval(node.left)
            right = _safe_eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
        if isinstance(node, ast.Call):
            args = [_safe_eval(a) for a in node.args]
            kwargs = {kw.arg: _safe_eval(kw.value) for kw in node.keywords if kw.arg}
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "Path" and node.func.attr == "resolve":
                    return str(Path.cwd())
            if isinstance(node.func, ast.Name):
                if node.func.id == "dict":
                    return dict(zip(args[::2], args[1::2])) if len(args) % 2 == 0 else dict(kwargs)
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "os" and node.func.attr == "path" and len(args) > 0 and isinstance(node.func, ast.Attribute):
                    pass
            return ""
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}"
            if hasattr(node.value, "id"):
                return f"{node.value.id}.{node.attr}"
            return node.attr
        if isinstance(node, ast.Subscript):
            try:
                return _safe_eval(node.value)
            except (IndexError, KeyError, TypeError):
                return ""
        return ""

    _assignment_map: dict[str, str] = {
        "project": "project",
        "version": "version",
        "release": "release",
        "author": "author",
        "copyright": "copyright",
        "language": "language",
        "extensions": "extensions",
        "html_theme": "html_theme",
        "html_theme_options": "html_theme_options",
        "html_static_path": "html_static_path",
        "html_extra_path": "html_extra_path",
        "html_css_files": "html_css_files",
        "html_js_files": "html_js_files",
        "html_logo": "html_logo",
        "html_favicon": "html_favicon",
        "html_title": "html_title",
        "html_short_title": "html_short_title",
        "latex_elements": "latex_elements",
        "latex_documents": "latex_documents",
        "man_pages": "man_pages",
        "texinfo_documents": "texinfo_documents",
        "epub_title": "epub_title",
        "epub_author": "epub_author",
        "epub_language": "epub_language",
        "master_doc": "master_doc",
        "source_suffix": "source_suffix",
        "exclude_patterns": "exclude_patterns",
        "nitpicky": "nitpicky",
        "suppress_warnings": "suppress_warnings",
        "rst_prolog": "rst_prolog",
        "rst_epilog": "rst_epilog",
        "numfig": "numfig",
        "smartquotes": "smartquotes",
        "needs_sphinx": "needs_sphinx",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in _assignment_map:
                    attr_name = _assignment_map[target.id]
                    try:
                        value = _safe_eval(node.value)
                        setattr(config, attr_name, value)
                        config._raw[target.id] = value
                    except (ValueError, TypeError, SyntaxError, RecursionError):
                        pass

    return config


# ---------------------------------------------------------------------------
# Project-level operations
# ---------------------------------------------------------------------------


def detect_sphinx_project(path: str | Path) -> bool:
    """Check whether *path* contains a Sphinx documentation project."""
    root = Path(path)
    if not root.is_dir():
        return False
    for marker in _SPHINX_MARKERS:
        if (root / marker).exists():
            return True
    return any(
        (root / "source" / marker).exists()
        for marker in {"conf.py", "index.rst"}
    )


def _discover_rst_files(root: Path, exclude_dirs: set[str] | None = None) -> dict[str, Path]:
    exclude = exclude_dirs or {"_build", "_templates", "_static", ".git", "__pycache__", ".venv", "node_modules"}
    pages: dict[str, Path] = {}
    for p in root.rglob("*.rst"):
        if any(part.startswith(".") or part in exclude for part in p.parts):
            continue
        rel = p.relative_to(root)
        stem = str(rel.with_suffix(""))
        pages[stem] = p
    return pages


def _parse_inventory(lines: list[str]) -> dict[str, str]:
    """Parse a simplified objects.inv format."""
    inv: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 4:
            name = parts[0]
            location = parts[-2] if len(parts) >= 5 else parts[2]
            inv[name] = location
    return inv


class RSTtoMarkdownConverter:
    """Converts RST content to Markdown with directive and role handling.

    Usage::

        converter = RSTtoMarkdownConverter()
        md = converter.convert(rst_text)
    """

    def __init__(self, inv_data: dict[str, str] | None = None) -> None:
        self._inv_data = inv_data or {}

    def convert(self, text: str) -> str:
        """Convert RST text to Markdown."""
        md = convert_rst_to_markdown(text)
        return md.strip() + "\n" if md else ""


class SphinxProjectConverter:
    """Converts an entire Sphinx documentation project to PiMD format.

    Handles conf.py, RST source files, toctrees, static assets,
    and cross-reference resolution.

    Usage::

        converter = SphinxProjectConverter()
        result = converter.convert("docs/", "output/")
    """

    def __init__(self, *, preserve_static: bool = True, flatten: bool = False) -> None:
        self._preserve_static = preserve_static
        self._flatten = flatten
        self._inv_data: dict[str, str] = {}

    def convert(self, source_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
        """Convert a Sphinx project.

        Args:
            source_dir: Path to the Sphinx project root.
            output_dir: Path where PiMD output will be written.

        Returns:
            A dictionary with conversion results.
        """
        source = Path(source_dir)
        output = Path(output_dir)

        conf_path = source / "conf.py"
        if not conf_path.exists():
            conf_path = source / "source" / "conf.py"

        config = parse_conf_py(conf_path) if conf_path.exists() else SphinxConfig()
        rst_root = conf_path.parent if conf_path.exists() else source

        pages = _discover_rst_files(rst_root)
        output.mkdir(parents=True, exist_ok=True)

        result = {
            "total_pages": len(pages),
            "converted": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
            "output_dir": str(output),
            "config": {
                "project": config.project,
                "version": config.version,
                "html_theme": config.html_theme,
                "extensions": config.extensions,
            },
        }

        nav_tree: list[dict] = []

        for rel_path, rst_file in pages.items():
            out_path = output / f"{rel_path}.md"
            if self._flatten:
                out_path = output / f"{rst_file.stem}.md"

            out_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                rst_text = rst_file.read_text(encoding="utf-8")
                md = convert_rst_to_markdown(rst_text)
                out_path.write_text(md, encoding="utf-8")
                result["converted"] += 1

                toctree_entries = parse_toctree(rst_text)
                if toctree_entries:
                    nav_tree.extend(convert_toctree_to_nav(toctree_entries))

            except Exception as exc:
                result["failed"] += 1
                result["errors"].append((str(rst_file), str(exc)))

        result["nav"] = nav_tree
        return result


# ---------------------------------------------------------------------------
# Top-level public functions
# ---------------------------------------------------------------------------


def convert_sphinx_to_pimd(source_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Convert a Sphinx documentation project to PiMD format.

    Convenience wrapper around ``SphinxProjectConverter``.

    Args:
        source_dir: Path to Sphinx project root.
        output_dir: Path for output.

    Returns:
        Dictionary with conversion statistics.
    """
    converter = SphinxProjectConverter()
    return converter.convert(source_dir, output_dir)
