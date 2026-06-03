"""Docusaurus documentation ecosystem support."""

# ruff: noqa: N815 — camelCase class attributes map to Docusaurus JSON config fields

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SIDEBAR_JS_RE = re.compile(
    r"(?:module\.)?exports\s*=\s*(\[|\{)(.*)",
    re.DOTALL,
)
_SITE_IMPORT_RE = re.compile(r"@site/(static/)?")
_JSX_TAG_RE = re.compile(
    r"<[\w]+[^>]*>.*?</[\w]+>|<[\w]+[^>]*/>",
    re.DOTALL,
)
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_DOCUSAURUS_FM_FIELDS = {
    "id", "slug", "sidebar_position", "sidebar_label",
    "sidebar_class_name", "description", "title", "draft",
    "tags", "keywords",
}


@dataclass
class SidebarItem:
    type: str
    label: str = ""
    id: str = ""
    items: list[SidebarItem] = field(default_factory=list)
    link: str | None = None
    href: str | None = None
    doc_id: str | None = None
    collapsed: bool | None = None
    collapsible: bool | None = None
    className: str | None = None
    customProps: dict[str, Any] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)


@dataclass
class SidebarCategory:
    label: str
    items: list[SidebarItem] = field(default_factory=list)
    collapsed: bool = True
    collapsible: bool = True
    className: str | None = None
    link: str | None = None
    customProps: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocusaurusConfig:
    title: str = ""
    url: str = ""
    baseUrl: str = "/"
    projectName: str = ""
    tagline: str = ""
    organizationName: str = ""
    favicon: str = ""
    trailingSlash: bool = False
    presets: list[dict[str, Any]] = field(default_factory=list)
    themeConfig: dict[str, Any] = field(default_factory=dict)
    plugins: list[dict[str, Any]] = field(default_factory=list)
    customFields: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class VersionedDoc:
    version: str
    doc_id: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocusaurusProject:
    root: Path
    config: DocusaurusConfig = field(default_factory=DocusaurusConfig)
    sidebars: dict[str, list[SidebarItem]] = field(default_factory=dict)
    versioned_docs: dict[str, list[VersionedDoc]] = field(default_factory=dict)
    docs_dir: Path | None = None
    versions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _parse_sidebar_item(raw: dict[str, Any]) -> SidebarItem:
    itype = raw.get("type", "doc")
    if itype == "category":
        children: list[SidebarItem] = []
        for child in raw.get("items", []):
            if isinstance(child, dict):
                children.append(_parse_sidebar_item(child))
            elif isinstance(child, str):
                children.append(SidebarItem(type="doc", id=child))
        return SidebarItem(
            type="category",
            label=raw.get("label", ""),
            items=children,
            collapsed=raw.get("collapsed", True),
            collapsible=raw.get("collapsible", True),
            className=raw.get("className"),
            link=raw.get("link", {}).get("id") if isinstance(raw.get("link"), dict) else None,
            customProps=raw.get("customProps", {}),
            source=raw,
        )

    href = raw.get("href")
    if itype == "link" or href:
        return SidebarItem(
            type="link",
            label=raw.get("label", ""),
            href=href,
            doc_id=raw.get("docId"),
            customProps=raw.get("customProps", {}),
            source=raw,
        )

    return SidebarItem(
        type="doc",
        label=raw.get("label", ""),
        id=raw.get("id", ""),
        doc_id=raw.get("id"),
        className=raw.get("className"),
        customProps=raw.get("customProps", {}),
        source=raw,
    )


def parse_sidebar(path: str | Path) -> list[SidebarItem]:
    p = Path(path)
    if not p.is_file():
        return []

    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    if p.suffix in (".js", ".ts"):
        return parse_sidebars_js(path)

    try:
        data: list[dict[str, Any]] = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        items: list[SidebarItem] = []
        for v in data.values():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        items.append(_parse_sidebar_item(item))
                    elif isinstance(item, str):
                        items.append(SidebarItem(type="doc", id=item))
        return items

    if isinstance(data, list):
        result: list[SidebarItem] = []
        for item in data:
            if isinstance(item, dict):
                result.append(_parse_sidebar_item(item))
            elif isinstance(item, str):
                result.append(SidebarItem(type="doc", id=item))
        return result

    return []


def _js_obj_to_json(text: str) -> str:
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"require\([^)]+\)", '"__require__"', text)
    text = re.sub(r"`[^`]*`", '"__literal__"', text)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    text = re.sub(r"(?<=[{,])\s*([a-zA-Z_$][\w$]*)\s*:", r'"\1":', text)

    _json_literals = frozenset({"true", "false", "null", "undefined", "None", "~"})
    def _quote_val(m: re.Match) -> str:
        word = m.group(1)
        if word in _json_literals:
            return m.group(0)
        return f': "{word}"'

    text = re.sub(r":\s*([a-zA-Z_$][\w$.]*)(?=\s*[,}\]])", _quote_val, text)
    text = re.sub(r"'([^']*)'", r'"\1"', text)
    return text


def _extract_sidebar_from_js_source(text: str) -> list[SidebarItem]:
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    m = _SIDEBAR_JS_RE.search(text)
    if m:
        brace = m.group(1)
        rest = m.group(2)
        json_str = brace + rest
        json_str = re.sub(r";\s*$", "", json_str)
        json_str = _js_obj_to_json(json_str)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return []
    else:
        json_str = _js_obj_to_json(text)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return []

    if isinstance(data, dict):
        items: list[SidebarItem] = []
        for v in data.values():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        items.append(_parse_sidebar_item(item))
        return items

    if isinstance(data, list):
        result: list[SidebarItem] = []
        for item in data:
            if isinstance(item, dict):
                result.append(_parse_sidebar_item(item))
        return result

    return []


def parse_sidebars_js(path: str | Path) -> list[SidebarItem]:
    p = Path(path)
    if not p.is_file():
        return []

    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    return _extract_sidebar_from_js_source(text)


def detect_docusaurus_project(path: str | Path) -> bool:
    root = Path(path)
    if not root.is_dir():
        return False

    markers = [
        root / "docusaurus.config.js",
        root / "docusaurus.config.ts",
        root / "sidebars.js",
        root / "sidebars.ts",
        root / "sidebars.json",
        root / "package.json",
    ]

    for marker in markers:
        if marker.is_file():
            if marker.name == "package.json":
                try:
                    pkg = json.loads(marker.read_text(encoding="utf-8", errors="replace"))
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    if any("docusaurus" in k for k in deps):
                        return True
                except (json.JSONDecodeError, OSError):
                    continue
            else:
                return True

    return (root / "docs").is_dir() or (root / "versioned_docs").is_dir()


def find_versioned_docs(path: str | Path) -> dict[str, list[Path]]:
    root = Path(path)
    result: dict[str, list[Path]] = {}

    versioned_dir = root / "versioned_docs"
    if versioned_dir.is_dir():
        version_pattern = re.compile(r"^version-(.+)$")
        for entry in sorted(versioned_dir.iterdir()):
            if not entry.is_dir():
                continue
            m = version_pattern.match(entry.name)
            version = m.group(1) if m else entry.name
            docs = sorted(entry.rglob("*.md")) + sorted(entry.rglob("*.mdx"))
            if docs:
                result[version] = docs

    current_docs = root / "docs"
    if current_docs.is_dir():
        current = sorted(current_docs.rglob("*.md")) + sorted(current_docs.rglob("*.mdx"))
        if current:
            result["current"] = current

    return result


def parse_docusaurus_frontmatter(text: str) -> dict[str, Any]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}

    raw = m.group(1)
    data: dict[str, Any] = {}

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()

        if not key:
            continue

        val = _parse_frontmatter_value(val)
        if key in _DOCUSAURUS_FM_FIELDS:
            data[key] = val

    return data


def _parse_frontmatter_value(val: str) -> Any:
    if not val:
        return ""
    if val.lower() in ("true", "yes"):
        return True
    if val.lower() in ("false", "no"):
        return False
    if val.lower() in ("null", "~", "none"):
        return None

    try:
        return int(val)
    except ValueError:
        pass

    try:
        return float(val)
    except ValueError:
        pass

    if val.startswith("[") and val.endswith("]"):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            pass

    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]

    return val


def strip_docusaurus_imports(text: str) -> str:
    result = _SITE_IMPORT_RE.sub("", text)

    prev = None
    while prev != result:
        prev = result
        result = _JSX_TAG_RE.sub("", result)
    _jsx_no_content = re.compile(r"<[\w]+[^>]*\s*/>", re.DOTALL)
    result = _jsx_no_content.sub("", result)

    result = re.sub(
        r'^import\s+.*?from\s+["\'][^"\']+["\'];?\s*$',
        "",
        result,
        flags=re.MULTILINE,
    )

    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def normalize_docusaurus_path(path: str, version: str = "") -> str:
    normalized = path.replace("\\", "/")

    normalized = re.sub(r"^@site/", "", normalized)
    normalized = re.sub(r"^/docs/", "docs/", normalized)
    normalized = re.sub(r"^docs/", "", normalized)

    if version and version not in ("current", ""):
        normalized = re.sub(rf"^version-{re.escape(version)}/", "", normalized)
        normalized = re.sub(rf"^versioned_docs/version-{re.escape(version)}/", "", normalized)

    normalized = re.sub(r"^versioned_docs/version-([^/]+)/", "", normalized)
    normalized = re.sub(r"^version-([^/]+)/", "", normalized)

    normalized = normalized.strip("/")

    normalized = re.sub(r"\.(md|mdx)$", "", normalized)

    if normalized.endswith("/index") or normalized == "index":
        normalized = re.sub(r"/?index$", "", normalized)
    if normalized.endswith("/README") or normalized == "README":
        normalized = re.sub(r"/?README$", "", normalized)

    return normalized


def _build_version_list(root: Path) -> list[str]:
    versions: list[str] = []
    versioned_dir = root / "versioned_docs"
    if versioned_dir.is_dir():
        pattern = re.compile(r"^version-(.+)$")
        for entry in sorted(versioned_dir.iterdir()):
            if entry.is_dir():
                m = pattern.match(entry.name)
                if m:
                    versions.append(m.group(1))
    if (root / "docs").is_dir():
        versions.insert(0, "current")
    return versions


def _parse_config(config_path: Path) -> DocusaurusConfig:
    cfg = DocusaurusConfig()
    if not config_path.is_file():
        return cfg

    try:
        text = config_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return cfg

    cfg.raw["_source"] = text[:500]

    title_m = re.search(r"title:\s*['\"]([^'\"]+)['\"]", text)
    if title_m:
        cfg.title = title_m.group(1)

    url_m = re.search(r"url:\s*['\"]([^'\"]+)['\"]", text)
    if url_m:
        cfg.url = url_m.group(1)

    base_m = re.search(r"baseUrl:\s*['\"]([^'\"]+)['\"]", text)
    if base_m:
        cfg.baseUrl = base_m.group(1)

    project_m = re.search(r"projectName:\s*['\"]([^'\"]+)['\"]", text)
    if project_m:
        cfg.projectName = project_m.group(1)

    org_m = re.search(r"organizationName:\s*['\"]([^'\"]+)['\"]", text)
    if org_m:
        cfg.organizationName = org_m.group(1)

    tagline_m = re.search(r"tagline:\s*['\"]([^'\"]+)['\"]", text)
    if tagline_m:
        cfg.tagline = tagline_m.group(1)

    favicon_m = re.search(r"favicon:\s*['\"]([^'\"]+)['\"]", text)
    if favicon_m:
        cfg.favicon = favicon_m.group(1)

    trailing_m = re.search(r"trailingSlash:\s*(true|false)", text)
    if trailing_m:
        cfg.trailingSlash = trailing_m.group(1) == "true"

    try:
        pkg_json = config_path.parent / "package.json"
        if pkg_json.is_file():
            pkg = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
            cfg.projectName = cfg.projectName or pkg.get("name", "")
            if not cfg.title:
                cfg.title = pkg.get("name", "")
    except (json.JSONDecodeError, OSError):
        pass

    return cfg


def _load_all_sidebars(root: Path) -> dict[str, list[SidebarItem]]:
    sidebars: dict[str, list[SidebarItem]] = {}

    sidebar_candidates = [
        root / "sidebars.json",
        root / "sidebars.js",
        root / "sidebars.ts",
    ]

    for candidate in sidebar_candidates:
        if candidate.is_file():
            parsed = parse_sidebar(candidate)
            if parsed:
                sidebars["default"] = parsed
                break

    versioned_sidebars_dir = root / "versioned_sidebars"
    if versioned_sidebars_dir.is_dir():
        version_pattern = re.compile(r"^version-(.+)[.](json|js|ts)$")
        for entry in sorted(versioned_sidebars_dir.iterdir()):
            if entry.is_file():
                m = version_pattern.match(entry.name)
                if m:
                    version = m.group(1)
                    parsed = parse_sidebar(entry)
                    if parsed:
                        sidebars[f"version-{version}"] = parsed

    return sidebars


class DocusaurusProjectConverter:
    def __init__(
        self,
        preserve_versions: bool = True,
        flatten_single_version: bool = False,
        include_assets: bool = True,
        sidebar_aware: bool = True,
    ) -> None:
        self.preserve_versions = preserve_versions
        self.flatten_single_version = flatten_single_version
        self.include_assets = include_assets
        self.sidebar_aware = sidebar_aware

    def load(self, source_dir: str | Path) -> DocusaurusProject:
        root = Path(source_dir).resolve()
        project = DocusaurusProject(root=root)
        project.errors = []

        if not root.is_dir():
            project.errors.append(f"Directory not found: {root}")
            return project

        config_paths = [
            root / "docusaurus.config.js",
            root / "docusaurus.config.ts",
        ]
        for cp in config_paths:
            if cp.is_file():
                project.config = _parse_config(cp)
                break

        docs_dir = root / "docs"
        if docs_dir.is_dir():
            project.docs_dir = docs_dir

        project.versions = _build_version_list(root)

        project.sidebars = _load_all_sidebars(root)

        versioned = find_versioned_docs(root)
        for version, paths in versioned.items():
            docs_list: list[VersionedDoc] = []
            for p in paths:
                doc_id = normalize_docusaurus_path(
                    str(p.relative_to(root)), version=version
                )
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                    fm = parse_docusaurus_frontmatter(content)
                except OSError:
                    fm = {}
                docs_list.append(
                    VersionedDoc(version=version, doc_id=doc_id, path=p, metadata=fm)
                )
            project.versioned_docs[version] = docs_list

        return project

    def convert(
        self, source_dir: str | Path, output_dir: str | Path
    ) -> dict[str, Any]:
        project = self.load(source_dir)
        out = Path(output_dir)

        if project.errors:
            return {
                "success": False,
                "errors": project.errors,
                "converted_files": 0,
                "output_dir": str(out),
            }

        out.mkdir(parents=True, exist_ok=True)

        converted = 0
        errors: list[str] = []

        if self.sidebar_aware and project.sidebars:
            self._write_sidebar_metadata(project, out)

        for version, docs in project.versioned_docs.items():
            if not self.preserve_versions:
                version = ""

            for vdoc in docs:
                target_dir = out
                if version and not self.flatten_single_version:
                    target_dir = out / version

                try:
                    content = vdoc.path.read_text(encoding="utf-8", errors="replace")
                    cleaned = strip_docusaurus_imports(content)

                    fm = parse_docusaurus_frontmatter(content)
                    if fm:
                        fm_lines = ["---"]
                        for k, v in fm.items():
                            fm_lines.append(f"{k}: {v}")
                        fm_lines.append("---")
                        fm_block = "\n".join(fm_lines)
                        body = re.sub(r"^---.*?\n---\s*\n", "", content, count=0, flags=re.DOTALL)
                        cleaned = fm_block + "\n\n" + strip_docusaurus_imports(body)

                    target_path = target_dir / f"{vdoc.doc_id}.md"
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(cleaned, encoding="utf-8")
                    converted += 1

                except OSError as exc:
                    errors.append(f"{vdoc.doc_id}: {exc}")

        if self.include_assets:
            self._copy_assets(project, out)

        return {
            "success": not errors,
            "errors": errors,
            "converted_files": converted,
            "output_dir": str(out),
            "versions": project.versions,
            "total_versions": len(project.versions),
        }

    def _write_sidebar_metadata(
        self, project: DocusaurusProject, output_dir: Path
    ) -> None:
        for version_key, items in project.sidebars.items():
            target = output_dir
            if version_key != "default":
                target = output_dir / version_key
            target.mkdir(parents=True, exist_ok=True)
            meta = self._sidebar_to_flat(items)
            sidebar_path = target / ".sidebar-metadata.json"
            try:
                sidebar_path.write_text(
                    json.dumps(meta, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except OSError:
                pass

    def _sidebar_to_flat(
        self, items: list[SidebarItem], prefix: str = ""
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for i, item in enumerate(items):
            order = prefix + str(i).zfill(3)
            if item.type == "category":
                if item.id:
                    result[item.id] = {
                        "sidebar_label": item.label,
                        "sidebar_position": order,
                        "type": "category",
                        "collapsed": item.collapsed,
                        "collapsible": item.collapsible,
                    }
                child_meta = self._sidebar_to_flat(item.items, f"{order}.")
                result.update(child_meta)
            elif item.type == "doc" and item.id:
                result[item.id] = {
                    "sidebar_label": item.label if item.label else item.id,
                    "sidebar_position": order,
                    "type": "doc",
                }
            elif item.type == "link" and item.label:
                pass

        return result

    def _copy_assets(self, project: DocusaurusProject, output_dir: Path) -> None:
        static_dir = project.root / "static"
        if static_dir.is_dir():
            assets_target = output_dir / "assets"
            try:
                for item in static_dir.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(static_dir)
                        dest = assets_target / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(item.read_bytes())
            except OSError:
                pass


def convert_docusaurus_to_pimd(
    source_dir: str | Path,
    output_dir: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    converter = DocusaurusProjectConverter(**kwargs)
    return converter.convert(source_dir, output_dir)


__all__ = [
    "SidebarItem",
    "SidebarCategory",
    "DocusaurusConfig",
    "VersionedDoc",
    "DocusaurusProject",
    "DocusaurusProjectConverter",
    "parse_sidebar",
    "parse_sidebars_js",
    "detect_docusaurus_project",
    "find_versioned_docs",
    "parse_docusaurus_frontmatter",
    "convert_docusaurus_to_pimd",
    "strip_docusaurus_imports",
    "normalize_docusaurus_path",
]
