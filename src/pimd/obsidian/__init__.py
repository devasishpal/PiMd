"""Obsidian knowledge base vault support."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Data classes ───────────────────────────────────────────────────────


@dataclass
class WikiLink:
    target: str
    display_text: str | None = None
    section: str | None = None
    block_ref: str | None = None
    is_embed: bool = False

    def resolved_path(self, vault_path: Path) -> Path | None:
        return resolve_wikilink(self, vault_path)

    def as_markdown_link(self, vault_path: Path | None = None) -> str:
        resolved = resolve_wikilink(self, vault_path) if vault_path else None
        url = resolved.as_uri() if resolved else f"#{self.target}"
        text = self.display_text or self.target
        if self.section:
            url += f"#{self.section.lower().replace(' ', '-')}"
        return f"[{text}]({url})"


@dataclass
class ObsidianCallout:
    type: str
    is_foldable: bool = False
    is_collapsed: bool = False
    title: str = ""
    content: str = ""

    def to_blockquote(self, indent: str = "") -> str:
        lines = self.content.split("\n")
        out: list[str] = []
        for i, line in enumerate(lines):
            out.append(f"{indent}> {line}")
        return "\n".join(out)

    def to_markdown(self) -> str:
        return self.to_blockquote()


@dataclass
class GraphReference:
    source: str
    target: str
    type: str  # "forward" or "backlink"
    source_path: Path | None = None
    target_path: Path | None = None


@dataclass
class VaultConfig:
    vault_path: Path
    attachment_folder: str = "attachments"
    use_wikilinks: bool = True
    show_frontmatter: bool = True
    strict_line_break: bool = False
    new_link_format: str = "shortest"
    use_yaml: bool = True

    @classmethod
    def from_vault(cls, vault_path: str | Path) -> VaultConfig:
        p = Path(vault_path)
        obsidian_dir = p / ".obsidian"
        config: dict[str, Any] = {}
        if obsidian_dir.is_dir():
            app_json = obsidian_dir / "app.json"
            if app_json.is_file():
                import json
                try:
                    config = json.loads(app_json.read_text(encoding="utf-8", errors="replace"))
                except Exception:
                    pass
        return cls(
            vault_path=p,
            attachment_folder=config.get("attachmentFolderPath", "attachments"),
            use_wikilinks=config.get("useMarkdownLinks", False),
            show_frontmatter=config.get("showFrontmatter", True),
            strict_line_break=config.get("strictLineBreak", False),
            new_link_format=config.get("newLinkFormat", "shortest"),
            use_yaml=config.get("useYAML", True),
        )


@dataclass
class ObsidianNote:
    path: Path
    content: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    wikilinks: list[WikiLink] = field(default_factory=list)
    embeds: list[WikiLink] = field(default_factory=list)
    callouts: list[ObsidianCallout] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    cssclass: str = ""
    created: datetime | None = None
    updated: datetime | None = None

    @classmethod
    def parse(cls, path: str | Path) -> ObsidianNote:
        p = Path(path)
        raw = p.read_text(encoding="utf-8", errors="replace")
        fm, body = _extract_obsidian_frontmatter(raw)
        note = cls(
            path=p,
            content=body,
            frontmatter=fm,
            wikilinks=extract_wikilinks(body),
            embeds=extract_embeds(body),
            callouts=extract_callouts(body),
        )
        tags_raw = fm.get("tags", [])
        if isinstance(tags_raw, str):
            note.tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        elif isinstance(tags_raw, list):
            note.tags = [str(t) for t in tags_raw if t]
        tags_inline = _find_inline_tags(body)
        for t in tags_inline:
            if t not in note.tags:
                note.tags.append(t)
        aliases_raw = fm.get("aliases", [])
        if isinstance(aliases_raw, str):
            note.aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()]
        elif isinstance(aliases_raw, list):
            note.aliases = [str(a) for a in aliases_raw if a]
        note.cssclass = fm.get("cssclass", "")
        created_raw = fm.get("created")
        if created_raw:
            note.created = _parse_obsidian_date(created_raw)
        updated_raw = fm.get("updated")
        if updated_raw:
            note.updated = _parse_obsidian_date(updated_raw)
        return note


# ── Regex patterns ─────────────────────────────────────────────────────

_WIKILINK_RE = re.compile(
    r"(?<!!)\[\[([^\[\]]+?)\]\]"
)
_EMBED_RE = re.compile(
    r"!\[\[([^\[\]]+?)\]\]"
)
_WIKILINK_DETAIL_RE = re.compile(
    r"""
    ^
    (?P<target>[^#|^]+?)
    (?:\#(?P<section>[^|^#]+?))?
    (?:\^(?P<block>[^\|]+?))?
    (?:\|(?P<display>.+?))?
    $
    """,
    re.VERBOSE,
)
_CALLOUT_RE = re.compile(
    r"^>\s*\[!(?P<type>\w+)\](?P<foldable>[+-])?\s*(?P<title>.*?)$",
    re.MULTILINE,
)
_INLINE_TAG_RE = re.compile(r"#([\w/-]+)")
_OBSIDIAN_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_ATTACHMENT_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp",
    ".pdf", ".mp3", ".mp4", ".mov", ".avi", ".mkv",
    ".xcf", ".psd", ".ai", ".epub", ".mobi",
}

CALLOUT_TYPES: set[str] = {
    "note", "tip", "warning", "danger", "info", "success",
    "question", "abstract", "todo", "failure", "bug",
    "example", "quote", "summary", "tldr", "hint",
    "important", "check", "done", "help", "caution",
    "attention", "missing", "cite", "error", "faq",
}


# ── WikiLink parsing ───────────────────────────────────────────────────


def parse_wikilink(text: str) -> WikiLink | None:
    inner = text.strip()
    if inner.startswith("[["):
        inner = inner[2:]
    if inner.endswith("]]"):
        inner = inner[:-2]
    m = _WIKILINK_DETAIL_RE.match(inner)
    if not m:
        return None
    parts = m.groupdict()
    target = parts["target"].strip()
    display_text = parts["display"].strip() if parts["display"] else target
    return WikiLink(
        target=target,
        display_text=display_text,
        section=parts["section"].strip() if parts["section"] else None,
        block_ref=parts["block"].strip() if parts["block"] else None,
        is_embed=False,
    )


def resolve_wikilink(link: WikiLink, vault_path: Path) -> Path | None:
    vault = Path(vault_path)
    if not vault.is_dir():
        return None
    target = link.target
    slug = _slugify(target)
    name_stem = target.replace(" ", " ").strip()
    md_name = f"{name_stem}.md"
    md_slug = f"{slug}.md"
    candidates: list[Path] = []
    for root in vault.rglob("*"):
        if root.is_dir():
            continue
        if root.suffix not in (".md",):
            continue
        if root.name == md_name or root.stem == name_stem or root.name == md_slug:
            candidates.append(root)
    if not candidates:
        for root in vault.rglob("*"):
            if root.is_dir():
                continue
            if root.suffix not in (".md",):
                continue
            stem_lower = root.stem.lower().replace(" ", "-").replace("_", "-")
            target_lower = slug.replace("_", "-")
            if stem_lower == target_lower:
                candidates.append(root)
    if not candidates:
        return None
    return min(candidates, key=lambda p: len(p.parts))


def extract_wikilinks(text: str) -> list[WikiLink]:
    results: list[WikiLink] = []
    for m in _WIKILINK_RE.finditer(text):
        inner = m.group(1)
        parsed = parse_wikilink(inner)
        if parsed:
            results.append(parsed)
    return results


def extract_embeds(text: str) -> list[WikiLink]:
    results: list[WikiLink] = []
    for m in _EMBED_RE.finditer(text):
        inner = m.group(1)
        parsed = parse_wikilink(inner)
        if parsed:
            parsed.is_embed = True
            results.append(parsed)
    return results


# ── Callout parsing ────────────────────────────────────────────────────


def parse_callout(text: str) -> ObsidianCallout | None:
    lines = text.split("\n")
    if not lines:
        return None
    first = lines[0]
    m = _CALLOUT_RE.match(first)
    if not m:
        return None
    ctype = m.group("type").lower()
    if ctype not in CALLOUT_TYPES:
        return None
    foldable_str = m.group("foldable")
    is_foldable = foldable_str is not None
    is_collapsed = foldable_str == "-"
    title = m.group("title").strip()
    content_lines: list[str] = []
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped.startswith(">"):
            inner = stripped[1:].lstrip()
            content_lines.append(inner)
        elif not stripped:
            content_lines.append("")
        else:
            content_lines.append(line)
    content = "\n".join(content_lines).strip()
    return ObsidianCallout(
        type=ctype,
        is_foldable=is_foldable,
        is_collapsed=is_collapsed,
        title=title,
        content=content,
    )


def extract_callouts(text: str) -> list[ObsidianCallout]:
    results: list[ObsidianCallout] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = _CALLOUT_RE.match(lines[i])
        if m:
            block_lines: list[str] = [lines[i]]
            i += 1
            while i < len(lines):
                stripped = lines[i].lstrip()
                if stripped.startswith(">") or not stripped:
                    block_lines.append(lines[i])
                    i += 1
                else:
                    break
            callout = parse_callout("\n".join(block_lines))
            if callout:
                results.append(callout)
        else:
            i += 1
    return results


def convert_callout_to_markdown(text: str) -> str:
    parts = _split_callouts_and_text(text)
    out: list[str] = []
    for part in parts:
        if isinstance(part, ObsidianCallout):
            out.append(part.to_blockquote())
        else:
            out.append(part)
    return "".join(out)


def _split_callouts_and_text(text: str) -> list[ObsidianCallout | str]:
    parts: list[ObsidianCallout | str] = []
    lines = text.split("\n")
    i = 0
    last_end = 0
    while i < len(lines):
        m = _CALLOUT_RE.match(lines[i])
        if m:
            block_start = i
            block_lines: list[str] = [lines[i]]
            i += 1
            while i < len(lines):
                stripped = lines[i].lstrip()
                if stripped.startswith(">") or not stripped:
                    block_lines.append(lines[i])
                    i += 1
                else:
                    break
            callout = parse_callout("\n".join(block_lines))
            if callout:
                text_before = "\n".join(lines[last_end:block_start])
                if text_before:
                    parts.append(text_before)
                parts.append(callout)
                last_end = i
        else:
            i += 1
    remaining = "\n".join(lines[last_end:])
    if remaining:
        parts.append(remaining)
    return parts


# ── Full pipeline ──────────────────────────────────────────────────────


def process_obsidian_content(
    text: str,
    vault_path: Path | None = None,
) -> str:
    result = text
    result = convert_callout_to_markdown(result)
    for embed in reversed(_sorted_embed_positions(result)):
        link = embed["link"]
        embed_text = embed["raw"]
        if vault_path:
            resolved = resolve_embed_path(link.target, vault_path)
            if resolved and resolved.exists():
                ext = resolved.suffix.lower()
                if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"}:
                    replacement = f"![{link.display_text or link.target}]({resolved.as_uri()})"
                else:
                    replacement = f"[{link.display_text or link.target}]({resolved.as_uri()})"
                result = _replace_at_index(result, embed["start"], embed["end"], replacement)
            else:
                result = _replace_at_index(result, embed["start"], embed["end"], embed_text.replace("!", ""))
    for wl in reversed(_sorted_wikilink_positions(result)):
        link = wl["link"]
        if vault_path:
            resolved = resolve_wikilink(link, vault_path)
            if resolved:
                url = resolved.as_uri()
                text_display = link.display_text or link.target
                replacement = f"[{text_display}]({url})"
                result = _replace_at_index(result, wl["start"], wl["end"], replacement)
    return result


def _sorted_embed_positions(text: str) -> list[dict[str, Any]]:
    positions: list[dict[str, Any]] = []
    for m in _EMBED_RE.finditer(text):
        inner = m.group(1)
        parsed = parse_wikilink(inner)
        if parsed:
            parsed.is_embed = True
            positions.append({
                "start": m.start(),
                "end": m.end(),
                "raw": m.group(0),
                "link": parsed,
            })
    return positions


def _sorted_wikilink_positions(text: str) -> list[dict[str, Any]]:
    positions: list[dict[str, Any]] = []
    for m in _WIKILINK_RE.finditer(text):
        inner = m.group(1)
        parsed = parse_wikilink(inner)
        if parsed:
            positions.append({
                "start": m.start(),
                "end": m.end(),
                "raw": m.group(0),
                "link": parsed,
            })
    return positions


def _replace_at_index(text: str, start: int, end: int, replacement: str) -> str:
    return text[:start] + replacement + text[end:]


# ── Graph building ─────────────────────────────────────────────────────


def build_graph(vault_path: Path) -> dict[str, list[GraphReference]]:
    vault = Path(vault_path)
    if not vault.is_dir():
        return {"nodes": [], "edges": []}
    md_files: list[Path] = []
    for p in vault.rglob("*.md"):
        if ".obsidian" in p.parts:
            continue
        md_files.append(p)
    graph: dict[str, list[GraphReference]] = {}
    for mf in md_files:
        rel = mf.relative_to(vault).as_posix()
        graph[rel] = []
        text = mf.read_text(encoding="utf-8", errors="replace")
        links = extract_wikilinks(text)
        for link in links:
            resolved = resolve_wikilink(link, vault)
            if resolved:
                target_rel = resolved.relative_to(vault).as_posix()
                ref = GraphReference(
                    source=rel,
                    target=target_rel,
                    type="forward",
                    source_path=mf,
                    target_path=resolved,
                )
                graph[rel].append(ref)
    backlinks: dict[str, list[GraphReference]] = {}
    for source, refs in graph.items():
        for ref in refs:
            target = ref.target
            if target not in backlinks:
                backlinks[target] = []
            bl = GraphReference(
                source=source,
                target=target,
                type="backlink",
                source_path=ref.source_path,
                target_path=ref.target_path,
            )
            backlinks[target].append(bl)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    for source, refs in graph.items():
        if source not in seen_nodes:
            nodes.append({"id": source, "path": str(vault / source), "links": len(refs)})
            seen_nodes.add(source)
        for ref in refs:
            if ref.target not in seen_nodes:
                nodes.append({"id": ref.target, "path": str(vault / ref.target), "links": 0})
                seen_nodes.add(ref.target)
            edges.append({"source": ref.source, "target": ref.target, "type": "forward"})
    for target, brefs in backlinks.items():
        for bref in brefs:
            if bref.source not in seen_nodes:
                nodes.append({"id": bref.source, "path": str(vault / bref.source), "links": 0})
                seen_nodes.add(bref.source)
            edges.append({"source": bref.source, "target": bref.target, "type": "backlink"})
    return {"nodes": nodes, "edges": edges}


# ── Vault detection & export ───────────────────────────────────────────


def detect_obsidian_vault(path: str | Path) -> bool:
    p = Path(path)
    if not p.is_dir():
        return False
    return (p / ".obsidian").is_dir()


def export_vault(
    vault_path: str | Path,
    output_path: str | Path,
    config: VaultConfig | None = None,
) -> dict[str, Any]:
    vault = Path(vault_path)
    out = Path(output_path)
    if not detect_obsidian_vault(vault):
        return {"success": False, "error": "Not an Obsidian vault", "files": [], "count": 0}
    cfg = config or VaultConfig.from_vault(vault)
    exporter = VaultExporter(vault, out, cfg)
    return exporter.export()


# ── Embed path resolution ──────────────────────────────────────────────


def resolve_embed_path(embed: str, vault_path: Path) -> Path | None:
    vault = Path(vault_path)
    if not vault.is_dir():
        return None
    embed_path = Path(embed)
    if embed_path.is_absolute():
        return embed_path if embed_path.exists() else None
    for candidate in _embed_candidates(embed, vault):
        if candidate.exists():
            return candidate
    for root in vault.rglob("*"):
        if root.is_dir():
            continue
        if root.suffix.lower() in _ATTACHMENT_EXTS and root.stem == embed_path.stem:
            return root
    return None


def _embed_candidates(name: str, vault: Path) -> list[Path]:
    cfg = VaultConfig.from_vault(vault)
    name_p = Path(name)
    candidates: list[Path] = []
    attachment_dir = vault / cfg.attachment_folder
    candidates.append(vault / name)
    candidates.append(attachment_dir / name)
    if not name_p.suffix:
        for ext in _ATTACHMENT_EXTS:
            candidates.append(vault / f"{name}{ext}")
            candidates.append(attachment_dir / f"{name}{ext}")
    return candidates


# ── VaultExporter ──────────────────────────────────────────────────────


class VaultExporter:
    def __init__(
        self,
        vault_path: Path,
        output_path: Path,
        config: VaultConfig,
    ) -> None:
        self.vault = vault_path
        self.output = output_path
        self.config = config
        self._stats: dict[str, Any] = {
            "total": 0,
            "converted": 0,
            "skipped": 0,
            "errors": 0,
            "files": [],
        }

    def export(self) -> dict[str, Any]:
        self.output.mkdir(parents=True, exist_ok=True)
        md_files: list[Path] = []
        for p in self.vault.rglob("*.md"):
            if ".obsidian" in p.parts:
                continue
            md_files.append(p)
        self._stats["total"] = len(md_files)
        for mf in md_files:
            try:
                self._convert_file(mf)
                self._stats["converted"] += 1
                self._stats["files"].append(str(mf.relative_to(self.vault)))
            except Exception:
                self._stats["errors"] += 1
        self._export_attachments()
        self._export_vault_metadata()
        return self._stats

    def _convert_file(self, path: Path) -> None:
        rel = path.relative_to(self.vault)
        out_path = self.output / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        note = ObsidianNote.parse(path)
        processed = process_obsidian_content(note.content, vault_path=self.vault)
        processed = self._convert_frontmatter(note, processed)
        out_path.write_text(processed, encoding="utf-8")

    def _convert_frontmatter(self, note: ObsidianNote, body: str) -> str:
        if not self.config.show_frontmatter:
            return body
        fm_lines: list[str] = ["---"]
        written: set[str] = set()
        for key in ("title", "tags", "aliases", "cssclass", "created", "updated"):
            val = getattr(note, key, None) or note.frontmatter.get(key)
            if val is not None and key not in written:
                if isinstance(val, list):
                    fm_lines.append(f"{key}:")
                    for item in val:
                        fm_lines.append(f"  - {item}")
                elif isinstance(val, datetime):
                    fm_lines.append(f"{key}: {val.isoformat()}")
                else:
                    fm_lines.append(f"{key}: {val}")
                written.add(key)
        for k, v in note.frontmatter.items():
            if k not in written:
                if isinstance(v, list):
                    fm_lines.append(f"{k}:")
                    for item in v:
                        fm_lines.append(f"  - {item}")
                elif isinstance(v, dict):
                    fm_lines.append(f"{k}:")
                    for sk, sv in v.items():
                        fm_lines.append(f"  {sk}: {sv}")
                else:
                    fm_lines.append(f"{k}: {v}")
                written.add(k)
        fm_lines.append("---")
        return "\n".join(fm_lines) + "\n" + body

    def _export_attachments(self) -> None:
        cfg = self.config
        attachment_dir = self.vault / cfg.attachment_folder
        if attachment_dir.is_dir():
            out_attach = self.output / cfg.attachment_folder
            out_attach.mkdir(parents=True, exist_ok=True)
            for f in attachment_dir.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(attachment_dir)
                    dest = out_attach / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)

    def _export_vault_metadata(self) -> None:
        import json
        meta = {
            "vault": str(self.vault),
            "exported_at": datetime.now().isoformat(),
            "config": {
                "attachment_folder": self.config.attachment_folder,
                "use_wikilinks": self.config.use_wikilinks,
            },
            "stats": {
                k: v for k, v in self._stats.items() if k != "files"
            },
            "files": self._stats["files"],
        }
        meta_path = self.output / ".pimd_vault_export.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


# ── Internal helpers ───────────────────────────────────────────────────


def _extract_obsidian_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = _OBSIDIAN_FM_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    body = text[m.end() :]
    try:
        import yaml
        data: dict[str, Any] = yaml.safe_load(raw) or {}
    except Exception:
        data = {}
    return data, body


def _find_inline_tags(text: str) -> list[str]:
    return _INLINE_TAG_RE.findall(text)


def _parse_obsidian_date(val: Any) -> datetime | None:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
    return None


def _slugify(text: str) -> str:
    result = text.lower()
    for ch in (" ", "_", "/", "\\", ":", ".", ","):
        result = result.replace(ch, "-")
    result = re.sub(r"-+", "-", result)
    return result.strip("-")


__all__ = [
    "WikiLink",
    "ObsidianCallout",
    "GraphReference",
    "VaultConfig",
    "VaultExporter",
    "ObsidianNote",
    "parse_wikilink",
    "resolve_wikilink",
    "extract_wikilinks",
    "extract_embeds",
    "parse_callout",
    "extract_callouts",
    "convert_callout_to_markdown",
    "process_obsidian_content",
    "build_graph",
    "detect_obsidian_vault",
    "export_vault",
    "resolve_embed_path",
    "CALLOUT_TYPES",
]
