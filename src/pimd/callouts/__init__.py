"""Callout / Admonition rendering engine for PiMD."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class CalloutType(Enum):
    NOTE = "note"
    TIP = "tip"
    WARNING = "warning"
    DANGER = "danger"
    INFO = "info"
    SUCCESS = "success"
    QUESTION = "question"
    IMPORTANT = "important"
    ABSTRACT = "abstract"
    TODO = "todo"
    FAILURE = "failure"
    BUG = "bug"
    EXAMPLE = "example"
    QUOTE = "quote"


@dataclass
class CalloutConfig:
    type_colors: dict[CalloutType, str] = field(default_factory=dict)
    type_icons: dict[CalloutType, str] = field(default_factory=dict)
    default_title: bool = True
    render_border: bool = True


@dataclass
class CalloutBlock:
    type: CalloutType
    title: str
    content_lines: list[str] = field(default_factory=list)
    foldable: bool = False
    collapsed: bool = False
    nesting_level: int = 0
    color: str = ""
    icon: str = ""


_DEFAULT_COLORS: dict[CalloutType, str] = {
    CalloutType.NOTE: "#1F6FEB",
    CalloutType.TIP: "#238636",
    CalloutType.WARNING: "#D29922",
    CalloutType.DANGER: "#DA3633",
    CalloutType.INFO: "#1F6FEB",
    CalloutType.SUCCESS: "#238636",
    CalloutType.QUESTION: "#8B5CF6",
    CalloutType.IMPORTANT: "#D29922",
    CalloutType.ABSTRACT: "#58A6FF",
    CalloutType.TODO: "#58A6FF",
    CalloutType.FAILURE: "#DA3633",
    CalloutType.BUG: "#DA3633",
    CalloutType.EXAMPLE: "#8B5CF6",
    CalloutType.QUOTE: "#8B949E",
}

_DEFAULT_ICONS: dict[CalloutType, str] = {
    CalloutType.NOTE: "\u2139\ufe0f",
    CalloutType.TIP: "\ud83d\udca1",
    CalloutType.WARNING: "\u26a0\ufe0f",
    CalloutType.DANGER: "\u2622\ufe0f",
    CalloutType.INFO: "\u2139\ufe0f",
    CalloutType.SUCCESS: "\u2705",
    CalloutType.QUESTION: "\u2753",
    CalloutType.IMPORTANT: "\u2757",
    CalloutType.ABSTRACT: "\ud83d\udcdd",
    CalloutType.TODO: "\u2705",
    CalloutType.FAILURE: "\u274c",
    CalloutType.BUG: "\ud83d\udc1b",
    CalloutType.EXAMPLE: "\ud83d\udccb",
    CalloutType.QUOTE: "\ud83d\udcac",
}

_DEFAULT_TITLES: dict[CalloutType, str] = {
    CalloutType.NOTE: "Note",
    CalloutType.TIP: "Tip",
    CalloutType.WARNING: "Warning",
    CalloutType.DANGER: "Danger",
    CalloutType.INFO: "Info",
    CalloutType.SUCCESS: "Success",
    CalloutType.QUESTION: "Question",
    CalloutType.IMPORTANT: "Important",
    CalloutType.ABSTRACT: "Abstract",
    CalloutType.TODO: "Todo",
    CalloutType.FAILURE: "Failure",
    CalloutType.BUG: "Bug",
    CalloutType.EXAMPLE: "Example",
    CalloutType.QUOTE: "Quote",
}

_LABEL_MAP: dict[str, CalloutType] = {
    "note": CalloutType.NOTE,
    "tip": CalloutType.TIP,
    "warning": CalloutType.WARNING,
    "danger": CalloutType.DANGER,
    "info": CalloutType.INFO,
    "success": CalloutType.SUCCESS,
    "question": CalloutType.QUESTION,
    "important": CalloutType.IMPORTANT,
    "abstract": CalloutType.ABSTRACT,
    "summary": CalloutType.ABSTRACT,
    "tldr": CalloutType.ABSTRACT,
    "todo": CalloutType.TODO,
    "failure": CalloutType.FAILURE,
    "fail": CalloutType.FAILURE,
    "bug": CalloutType.BUG,
    "example": CalloutType.EXAMPLE,
    "quote": CalloutType.QUOTE,
    "cite": CalloutType.QUOTE,
}

_CALLOUT_HEADER = re.compile(
    r"^((?:\s*>)+) ?\[!([A-Z_]+)\]\s*([+\-])?\s*(.*)$",
    re.IGNORECASE,
)

_QUOTE_LINE = re.compile(r"^((?:\s*>)+) ?(.*)$")


def callout_type_from_label(label: str) -> CalloutType:
    normalized = label.strip().lower()
    if normalized in _LABEL_MAP:
        return _LABEL_MAP[normalized]
    raise ValueError(f"Unknown callout type label: {label}")


def callout_default_title(callout_type: CalloutType) -> str:
    return _DEFAULT_TITLES.get(callout_type, callout_type.value.capitalize())


def callout_color(
    callout_type: CalloutType,
    config: CalloutConfig | None = None,
) -> str:
    if config and callout_type in config.type_colors:
        return config.type_colors[callout_type]
    return _DEFAULT_COLORS.get(callout_type, "#1F6FEB")


def callout_icon(callout_type: CalloutType) -> str:
    return _DEFAULT_ICONS.get(callout_type, "\u2139\ufe0f")


def _nesting_from_prefix(prefix: str) -> int:
    return prefix.strip().count(">")


def _count_prefix_chars(prefix: str) -> int:
    return len(prefix)


def parse_callout(text: str, start: int = 0) -> tuple[CalloutBlock | None, int]:
    lines = text.splitlines()
    if start < 0 or start >= len(lines):
        return None, start

    m = _CALLOUT_HEADER.match(lines[start])
    if not m:
        return None, start

    prefix = m.group(1)
    nesting_level = _nesting_from_prefix(prefix)
    type_label = m.group(2)
    foldable_marker = m.group(3)
    raw_title = m.group(4).strip() if m.group(4) else ""

    callout_type = callout_type_from_label(type_label)
    foldable = foldable_marker is not None
    collapsed = foldable_marker == "-"
    title = raw_title if raw_title else callout_default_title(callout_type)

    content_lines: list[str] = []
    pos = start + 1

    while pos < len(lines):
        line = lines[pos]
        qm = _QUOTE_LINE.match(line)

        if not qm:
            if not line.strip():
                pos += 1
                continue
            break

        line_prefix = qm.group(1)
        line_nesting = _nesting_from_prefix(line_prefix)
        line_content = qm.group(2)

        if line_nesting < nesting_level:
            break

        if line_nesting == nesting_level:
            inner_header = _CALLOUT_HEADER.match(line)
            if inner_header:
                break
            content_lines.append(line_content)
            pos += 1
            continue

        if line_nesting > nesting_level:
            nested_block, new_pos = parse_callout(text, pos)
            if nested_block is not None:
                content_lines.append(callout_to_markdown(nested_block))
                pos = new_pos
                continue
            extra = line_nesting - nesting_level
            stripped = line_content
            for _ in range(extra):
                if stripped.startswith("> "):
                    stripped = stripped[2:]
                elif stripped.startswith(">"):
                    stripped = stripped[1:]
            content_lines.append(stripped)
            pos += 1
            continue

    while content_lines and not content_lines[-1]:
        content_lines.pop()

    block = CalloutBlock(
        type=callout_type,
        title=title,
        content_lines=content_lines,
        foldable=foldable,
        collapsed=collapsed,
        nesting_level=nesting_level,
        color=callout_color(callout_type),
        icon=callout_icon(callout_type),
    )

    return block, pos


def extract_callouts(text: str) -> list[CalloutBlock]:
    blocks: list[CalloutBlock] = []
    pos = 0
    lines = text.splitlines()
    while pos < len(lines):
        block, new_pos = parse_callout(text, pos)
        if block is not None:
            blocks.append(block)
            pos = new_pos
        else:
            pos += 1
    return blocks


def callout_to_html(block: CalloutBlock) -> str:
    color = block.color or callout_color(block.type)
    icon = block.icon or callout_icon(block.type)
    lines: list[str] = []
    lines.append(
        f'<div class="callout callout-{block.type.value}" '
        f'style="border-left: 4px solid {color}; '
        f'padding: 0.5em 1em; margin: 0.5em 0; '
        f'background: {color}10; border-radius: 4px;">'
    )
    lines.append(
        f"<p style=\"font-weight: bold; margin: 0 0 0.25em 0;\">"
        f"{icon} {_escape_html(block.title)}</p>"
    )
    for content_line in block.content_lines:
        if content_line.startswith("> [!") or content_line.strip().startswith("> [!") and content_line.startswith(">"):
            nested = parse_callout(content_line, 0)
            if nested[0] is not None:
                lines.append(callout_to_html(nested[0]))
                continue
        if not content_line.strip():
            lines.append("<br>")
        else:
            lines.append(f"<p style=\"margin: 0.25em 0;\">{_escape_html(content_line)}</p>")
    lines.append("</div>")
    return "\n".join(lines)


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def callout_to_markdown(block: CalloutBlock) -> str:
    prefix = "> " * block.nesting_level
    foldable_suffix = ""
    if block.foldable:
        coll = "+"
        if block.collapsed:
            coll = "-"
        foldable_suffix = coll

    label = block.type.value.upper()
    header = f"{prefix}[!{label}]{foldable_suffix}"
    title_text = block.title or callout_default_title(block.type)
    header = f"{header} {title_text}"

    lines: list[str] = [header]
    for content in block.content_lines:
        if content.strip().startswith("> ["):
            for cl in content.split("\n"):
                if cl.strip():
                    lines.append(f"{prefix}{cl}")
                else:
                    lines.append(prefix.rstrip())
        elif not content.strip():
            lines.append(prefix.rstrip())
        else:
            lines.append(f"{prefix}{content}")

    return "\n".join(lines)


def callout_to_docx_element(block: CalloutBlock) -> str:
    color = block.color or callout_color(block.type)
    icon = block.icon or callout_icon(block.type)
    hex_color = color.lstrip("#")

    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    bg_r = max(0, r + int((255 - r) * 0.85))
    bg_g = max(0, g + int((255 - g) * 0.85))
    bg_b = max(0, b + int((255 - b) * 0.85))
    bg_hex = f"{bg_r:02X}{bg_g:02X}{bg_b:02X}"

    lines: list[str] = []
    lines.append('<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">')
    lines.append("  <w:tblPr>")
    lines.append('    <w:tblStyle w:val="TableGrid"/>')
    lines.append('    <w:tblW w:w="5000" w:type="pct"/>')
    lines.append("    <w:tblBorders>")
    lines.append('      <w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>')
    lines.append('      <w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>')
    lines.append('      <w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>')
    lines.append(f'      <w:left w:val="single" w:sz="24" w:space="0" w:color="{hex_color}"/>')
    lines.append("    </w:tblBorders>")
    lines.append("    <w:tblCellMar>")
    lines.append('      <w:top w:w="60" w:type="dxa"/>')
    lines.append('      <w:bottom w:w="60" w:type="dxa"/>')
    lines.append('      <w:left w:w="120" w:type="dxa"/>')
    lines.append('      <w:right w:w="60" w:type="dxa"/>')
    lines.append("    </w:tblCellMar>")
    lines.append("  </w:tblPr>")
    lines.append("  <w:tr>")
    lines.append("    <w:tc>")
    lines.append("      <w:tcPr>")
    lines.append(f'        <w:shd w:val="clear" w:color="auto" w:fill="{bg_hex}"/>')
    lines.append("      </w:tcPr>")

    title_text = f"{icon} {block.title}"
    lines.append("      <w:p>")
    lines.append("        <w:pPr>")
    lines.append('          <w:pStyle w:val="Heading6"/>')
    lines.append("        </w:pPr>")
    lines.append("        <w:r>")
    lines.append("          <w:rPr>")
    lines.append(f'            <w:color w:val="{hex_color}"/>')
    lines.append('            <w:sz w:val="22"/>')
    lines.append("            <w:b/>")
    lines.append("          </w:rPr>")
    lines.append(f"          <w:t xml:space=\"preserve\">{_escape_xml(title_text)}</w:t>")
    lines.append("        </w:r>")
    lines.append("      </w:p>")

    for content_line in block.content_lines:
        if content_line.strip().startswith("> [") and not content_line.startswith(">  ") and content_line.strip().startswith("> [!"):
            nested = parse_callout(content_line, 0)
            if nested[0] is not None:
                nested_xml = callout_to_docx_element(nested[0])
                lines.append(nested_xml)
                continue
        lines.append("      <w:p>")
        lines.append("        <w:pPr>")
        lines.append('          <w:spacing w:before="40" w:after="40"/>')
        lines.append("        </w:pPr>")
        lines.append("        <w:r>")
        lines.append("          <w:rPr>")
        lines.append(f'            <w:color w:val="{hex_color}"/>')
        lines.append('            <w:sz w:val="20"/>')
        lines.append("          </w:rPr>")
        lines.append(f"          <w:t xml:space=\"preserve\">{_escape_xml(content_line)}</w:t>")
        lines.append("        </w:r>")
        lines.append("      </w:p>")

    lines.append("    </w:tc>")
    lines.append("  </w:tr>")
    lines.append("</w:tbl>")
    return "\n".join(lines)


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def process_callouts(text: str, config: CalloutConfig | None = None) -> str:
    lines = text.splitlines()
    result: list[str] = []
    pos = 0
    while pos < len(lines):
        block, new_pos = parse_callout(text, pos)
        if block is not None:
            if config is not None:
                if block.type in config.type_colors:
                    block.color = config.type_colors[block.type]
                if block.type in config.type_icons:
                    block.icon = config.type_icons[block.type]
            result.append(callout_to_markdown(block))
            pos = new_pos
        else:
            result.append(lines[pos])
            pos += 1
    return "\n".join(result)


__all__ = [
    "CalloutType",
    "CalloutConfig",
    "CalloutBlock",
    "callout_type_from_label",
    "callout_default_title",
    "callout_color",
    "callout_icon",
    "parse_callout",
    "extract_callouts",
    "callout_to_html",
    "callout_to_markdown",
    "callout_to_docx_element",
    "process_callouts",
]
