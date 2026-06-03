"""Template discovery and loading from disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pimd.templates.models import Template, TemplateConfig, TemplateMetadata, TemplateType


def _find_template_dirs() -> list[Path]:
    """Return ordered list of directories to search for templates."""
    dirs: list[Path] = []
    # User-local templates
    user_dir = Path.home() / ".pimd" / "templates"
    if user_dir.is_dir():
        dirs.append(user_dir)
    # Package-bundled presets
    pkg_dir = Path(__file__).resolve().parent / "presets"
    if pkg_dir.is_dir():
        dirs.append(pkg_dir)
    # CWD templates
    cwd_dir = Path.cwd() / ".pimd" / "templates"
    if cwd_dir.is_dir():
        dirs.append(cwd_dir)
    return dirs


def _load_meta(path: Path) -> dict[str, Any] | None:
    """Load template metadata from a JSON or TOML sidecar file."""
    for ext in (".json", ".toml"):
        meta_file = path.with_suffix(ext)
        if meta_file.is_file():
            raw = meta_file.read_text(encoding="utf-8")
            if ext == ".toml":
                import tomllib  # Python 3.11+

                return dict(tomllib.loads(raw))
            return dict(json.loads(raw))
    return None


def discover_templates() -> list[Template]:
    """Scan all template directories and return discovered templates."""
    found: list[Template] = []
    seen: set[str] = set()
    for directory in _find_template_dirs():
        for entry in sorted(directory.iterdir()):
            if entry.is_dir() and entry.name not in seen:
                seen.add(entry.name)
                tpl = _load_template_dir(entry)
                if tpl is not None:
                    found.append(tpl)
    return found


def _load_template_dir(path: Path) -> Template | None:
    """Load a single template from a directory."""
    meta = _load_meta(path / "template")
    if meta is None:
        meta = _load_meta(path)
    if meta is None:
        return None
    try:
        tm = TemplateMetadata(
            name=meta.get("name", path.name),
            type=TemplateType(meta.get("type", "custom")),
            description=meta.get("description", ""),
            version=meta.get("version", "1.0.0"),
            author=meta.get("author", ""),
            tags=meta.get("tags", []),
        )
    except (ValueError, KeyError):
        return None
    cfg_data = meta.get("config", {})
    cfg = TemplateConfig(**{k: v for k, v in cfg_data.items() if hasattr(TemplateConfig, k)})
    docx_path = path / "template.docx"
    tpl = Template(metadata=tm, config=cfg)
    if docx_path.is_file():
        tpl.docx_template_path = docx_path.resolve()
    before_file = path / "content_before.md"
    if before_file.is_file():
        tpl.content_before = before_file.read_text(encoding="utf-8")
    after_file = path / "content_after.md"
    if after_file.is_file():
        tpl.content_after = after_file.read_text(encoding="utf-8")
    return tpl


def load_template(name: str) -> Template | None:
    """Load a single template by name."""
    for tpl in discover_templates():
        if tpl.name == name:
            return tpl
    return None


def get_template_path(name: str) -> Path | None:
    """Return the path to a template's DOCX file, if any."""
    tpl = load_template(name)
    if tpl is not None:
        return tpl.docx_template_path
    return None
