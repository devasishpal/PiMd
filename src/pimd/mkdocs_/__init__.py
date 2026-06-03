"""MkDocs documentation ecosystem support."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MkDocsConfig:
    """Parsed ``mkdocs.yml`` configuration."""

    site_name: str = ""
    site_url: str = ""
    site_description: str = ""
    site_author: str = ""
    docs_dir: str = "docs"
    nav: list[Any] | dict[str, Any] | None = None
    theme_name: str = "mkdocs"
    theme_config: dict[str, Any] = field(default_factory=dict)
    plugins: list[dict[str, Any]] = field(default_factory=list)
    markdown_extensions: list[dict[str, Any] | str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    extra_css: list[str] = field(default_factory=list)
    extra_javascript: list[str] = field(default_factory=list)
    copyright: str = ""
    repo_url: str = ""
    repo_name: str = ""
    edit_uri: str = ""
    use_directory_urls: bool = True
    strict: bool = False
    dev_addr: str = "127.0.0.1:8000"
    watch: list[str] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    raw_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class NavItem:
    """A single navigation entry parsed from ``mkdocs.yml`` ``nav``."""

    title: str
    path: str | None = None
    children: list[NavItem] = field(default_factory=list)
    level: int = 0

    @property
    def is_section(self) -> bool:
        return self.path is None


@dataclass
class MkDocsProject:
    """Represents a discovered and parsed MkDocs project."""

    config: MkDocsConfig
    config_path: Path
    source_dir: Path
    docs_dir: Path
    nav_items: list[NavItem]


# ── Known MkDocs Markdown extensions ──────────────────────────────────

_BUILTIN_EXTENSIONS: set[str] = {
    "abbr",
    "admonition",
    "attr_list",
    "codehilite",
    "def_list",
    "extra",
    "fenced_code",
    "footnotes",
    "headerid",
    "legacy_attrs",
    "legacy_em",
    "md_in_html",
    "meta",
    "nl2br",
    "sane_lists",
    "smarty",
    "tables",
    "toc",
}

_PYMDOWNX_EXTENSIONS: set[str] = {
    "arithmatex",
    "betterem",
    "caret",
    "critic",
    "details",
    "emoji",
    "escapeall",
    "extra",
    "highlight",
    "inlinehilite",
    "keys",
    "magiclink",
    "mark",
    "pathconverter",
    "progressbar",
    "saneheaders",
    "smartsymbols",
    "snippets",
    "striphtml",
    "superfences",
    "tabbed",
    "tasklist",
    "tilde",
}

_KNOWN_THEMES: dict[str, str] = {
    "mkdocs": "MkDocs default",
    "readthedocs": "Read the Docs",
    "material": "Material for MkDocs",
    "bootstrap": "Bootstrap",
    "cinder": "Cinder",
    "cosmo": "Cosmo",
    "flatly": "Flatly",
    "journal": "Journal",
    "legacy": "Legacy",
    "lumen": "Lumen",
    "pulp": "Pulp",
    "readable": "Readable",
    "sandstone": "Sandstone",
    "simplex": "Simplex",
    "slate": "Slate",
    "spacelab": "Spacelab",
    "united": "United",
    "yeti": "Yeti",
}

_KNOWN_PLUGINS: set[str] = {
    "awesome-pages",
    "git-committers",
    "git-revision-date-localized",
    "glossary",
    "include-dir-to-nav",
    "macros",
    "markdown-exec",
    "minify",
    "mkdocs-plugin",
    "mkdocs-video",
    "open-in-new-tab",
    "pdf-export",
    "print-site",
    "redirect",
    "rss",
    "search",
    "social",
    "table-reader",
    "tags",
}

# ── Detection ─────────────────────────────────────────────────────────


def detect_mkdocs_project(path: str | Path) -> bool:
    """Check if *path* contains an MkDocs project (``mkdocs.yml`` / ``mkdocs.yaml``)."""
    root = Path(path)
    if not root.is_dir():
        return False
    return (root / "mkdocs.yml").is_file() or (root / "mkdocs.yaml").is_file()

# ── Configuration parsing ────────────────────────────────────────────


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required to parse mkdocs.yml. Install with: pip install pyyaml"
        )

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        data: dict[str, Any] = yaml.safe_load(text) or {}
    except FileNotFoundError:
        raise FileNotFoundError(f"MkDocs config not found: {path}")
    except Exception as exc:
        raise ValueError(f"Failed to parse {path}: {exc}")

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected a top-level mapping in {path}, got {type(data).__name__}"
        )

    return data


def parse_mkdocs_config(path: str | Path) -> MkDocsConfig:
    """Parse an ``mkdocs.yml`` file and return an ``MkDocsConfig``."""
    config_path = Path(path).resolve()
    data = _load_yaml(config_path)

    raw_nav: Any = data.get("nav")
    nav: list[Any] | dict[str, Any] | None = raw_nav

    theme_raw: Any = data.get("theme", "mkdocs")
    if isinstance(theme_raw, str):
        theme_name = theme_raw
        theme_config: dict[str, Any] = {}
    elif isinstance(theme_raw, dict):
        theme_name = str(theme_raw.get("name", "mkdocs"))
        theme_config = {k: v for k, v in theme_raw.items() if k != "name"}
    else:
        theme_name = "mkdocs"
        theme_config = {}

    raw_plugins: Any = data.get("plugins", [])
    if isinstance(raw_plugins, list):
        plugins = _parse_plugin_list(raw_plugins)
    else:
        plugins = []

    raw_extensions: Any = data.get("markdown_extensions", [])
    if isinstance(raw_extensions, list):
        markdown_extensions = _parse_extension_list(raw_extensions)
    else:
        markdown_extensions = []

    return MkDocsConfig(
        site_name=str(data.get("site_name", "")),
        site_url=str(data.get("site_url", "")),
        site_description=str(data.get("site_description", "")),
        site_author=str(data.get("site_author", "")),
        docs_dir=str(data.get("docs_dir", "docs")),
        nav=nav,
        theme_name=theme_name,
        theme_config=theme_config,
        plugins=plugins,
        markdown_extensions=markdown_extensions,
        extra=dict(data.get("extra", {})),
        extra_css=list(data.get("extra_css", [])),
        extra_javascript=list(data.get("extra_javascript", [])),
        copyright=str(data.get("copyright", "")),
        repo_url=str(data.get("repo_url", "")),
        repo_name=str(data.get("repo_name", "")),
        edit_uri=str(data.get("edit_uri", "")),
        use_directory_urls=bool(data.get("use_directory_urls", True)),
        strict=bool(data.get("strict", False)),
        dev_addr=str(data.get("dev_addr", "127.0.0.1:8000")),
        watch=list(data.get("watch", [])),
        validation=dict(data.get("validation", {})),
        raw_config=data,
    )


def _parse_plugin_list(raw_plugins: list[Any]) -> list[dict[str, Any]]:
    plugins: list[dict[str, Any]] = []
    for item in raw_plugins:
        if isinstance(item, str):
            plugins.append({"name": item, "config": {}})
        elif isinstance(item, dict):
            for name, cfg in item.items():
                plugins.append(
                    {"name": str(name), "config": dict(cfg) if isinstance(cfg, dict) else {}}
                )
    return plugins


def _parse_extension_list(
    raw_extensions: list[Any],
) -> list[dict[str, Any] | str]:
    extensions: list[dict[str, Any] | str] = []
    for item in raw_extensions:
        if isinstance(item, str):
            extensions.append(item)
        elif isinstance(item, dict):
            for ext_name, ext_cfg in item.items():
                if isinstance(ext_cfg, dict):
                    extensions.append({ext_name: ext_cfg})
                else:
                    extensions.append(ext_name)
    return extensions

# ── Nav parsing ──────────────────────────────────────────────────────


def parse_nav(nav_data: list[Any] | dict[str, Any] | None) -> list[NavItem]:
    """Parse the ``nav`` section of an MkDocs config into ``NavItem``s."""
    if nav_data is None:
        return []

    if isinstance(nav_data, dict):
        items: list[NavItem] = []
        for key, value in nav_data.items():
            items.append(_parse_nav_entry(str(key), value, level=0))
        return items

    if isinstance(nav_data, list):
        items: list[NavItem] = []
        for entry in nav_data:
            items.append(_parse_nav_entry_list(entry, level=0))
        return items

    return []


def _parse_nav_entry_list(entry: Any, level: int) -> NavItem:
    if isinstance(entry, str):
        title = _title_from_path(entry)
        return NavItem(title=title, path=entry, level=level)

    if isinstance(entry, dict):
        for key, value in entry.items():
            return _parse_nav_entry(str(key), value, level)
        return NavItem(title="", level=level)

    return NavItem(title=str(entry), level=level)


def _parse_nav_entry(title: str, value: Any, level: int) -> NavItem:
    if isinstance(value, str):
        return NavItem(title=title, path=value, level=level)

    if isinstance(value, list):
        children: list[NavItem] = []
        for child in value:
            children.append(_parse_nav_entry_list(child, level + 1))
        return NavItem(title=title, children=children, level=level)

    return NavItem(title=title, children=[], level=level)


def _title_from_path(path: str) -> str:
    stem = Path(path).stem
    if stem == "index":
        parts = Path(path).parent.name
        if parts == ".":
            return "Home"
        return parts.replace("-", " ").replace("_", " ").title()
    return stem.replace("-", " ").replace("_", " ").title()

# ── Nav utilities ────────────────────────────────────────────────────


def flatten_nav(nav: list[NavItem]) -> list[NavItem]:
    """Flatten nested ``NavItem`` tree into an ordered list (depth-first)."""
    result: list[NavItem] = []
    for item in nav:
        if item.children:
            if item.path is not None:
                result.append(NavItem(title=item.title, path=item.path, level=0))
            result.extend(flatten_nav(item.children))
        else:
            result.append(NavItem(title=item.title, path=item.path, level=0))
    return result


def resolve_mkdocs_path(path: str, docs_dir: Path) -> Path:
    """Resolve a nav path (possibly with anchor) relative to ``docs_dir``."""
    clean = path.split("#")[0]
    if not clean:
        return docs_dir

    resolved = (docs_dir / clean).resolve()
    if not resolved.suffix:
        resolved = resolved.with_suffix(".md")

    return resolved

# ── Extension detection ──────────────────────────────────────────────


def detect_mkdocs_extensions(config: MkDocsConfig) -> dict[str, list[str]]:
    """Categorise MkDocs markdown extensions into builtin, pymdownx, and custom."""
    builtin: list[str] = []
    pymdownx: list[str] = []
    custom: list[str] = []

    for ext in config.markdown_extensions:
        name = ext if isinstance(ext, str) else next(iter(ext.keys()), "")
        if name.startswith("pymdownx."):
            pymdownx.append(name[len("pymdownx."):])
        elif name in _BUILTIN_EXTENSIONS or name.startswith("markdown.extensions."):
            builtin.append(name.replace("markdown.extensions.", ""))
        else:
            custom.append(name)

    return {
        "builtin": sorted(builtin),
        "pymdownx": sorted(pymdownx),
        "custom": sorted(custom),
    }

# ── Path mapping ─────────────────────────────────────────────────────


def build_path_title_map(config: MkDocsConfig, docs_dir: Path) -> dict[str, str]:
    """Build a mapping of file paths to document titles from the nav definition."""
    title_map: dict[str, str] = {}
    if config.nav is None:
        return title_map

    nav_items = parse_nav(config.nav)
    for item in flatten_nav(nav_items):
        if item.path:
            try:
                resolved = resolve_mkdocs_path(item.path, docs_dir)
                rel = resolved.relative_to(docs_dir)
                title_map[str(rel.as_posix())] = item.title
            except ValueError:
                pass

    return title_map

# ── MkDocsProject discovery ──────────────────────────────────────────


def discover_mkdocs_project(path: str | Path) -> MkDocsProject | None:
    """Discover and parse an MkDocs project at *path*.

    Returns ``None`` if the directory does not contain
    ``mkdocs.yml`` / ``mkdocs.yaml``.
    """
    root = Path(path).resolve()
    if not root.is_dir():
        return None

    yml_path = root / "mkdocs.yml"
    if not yml_path.is_file():
        yml_path = root / "mkdocs.yaml"
        if not yml_path.is_file():
            return None

    config = parse_mkdocs_config(yml_path)
    docs_dir = (root / config.docs_dir).resolve()
    nav_items = parse_nav(config.nav) if config.nav else []

    return MkDocsProject(
        config=config,
        config_path=yml_path,
        source_dir=root,
        docs_dir=docs_dir,
        nav_items=nav_items,
    )

# ── Project converter ────────────────────────────────────────────────


class MkDocsProjectConverter:
    """Convert an entire MkDocs project to PiMD-ready format.

    Usage::

        converter = MkDocsProjectConverter()
        result = converter.convert("my-mkdocs-project/", "output-pimd/")
    """

    def __init__(self) -> None:
        self._converted_count: int = 0
        self._skipped_count: int = 0
        self._error_count: int = 0
        self._errors: list[tuple[str, str]] = []

    def convert(
        self,
        source_dir: str | Path,
        output_dir: str | Path,
        *,
        include_assets: bool = True,
        merge: bool = False,
    ) -> dict[str, Any]:
        """Convert an MkDocs project to PiMD format.

        Parameters
        ----------
        source_dir:
            Directory containing ``mkdocs.yml``.
        output_dir:
            Output directory for the converted structure.
        include_assets:
            Copy static directories (``img``, ``images``, ``assets``).
        merge:
            Merge all pages into a single output document.

        Returns
        -------
        dict
            Result summary with keys: ``total``, ``converted``, ``skipped``,
            ``errors``, ``error_details``, ``output_dir``, ``extensions``,
            ``nav_items``.
        """
        source = Path(source_dir).resolve()
        output = Path(output_dir).resolve()

        project = discover_mkdocs_project(source)
        if project is None:
            raise FileNotFoundError(f"No MkDocs project found at {source}")

        output.mkdir(parents=True, exist_ok=True)

        extensions = detect_mkdocs_extensions(project.config)
        nav_flat = flatten_nav(project.nav_items)

        if merge:
            self._convert_merged(output, project, nav_flat)
        else:
            self._convert_individual(output, project, nav_flat)

        if include_assets:
            _copy_assets(project, output)

        return {
            "total": self._converted_count + self._skipped_count + self._error_count,
            "converted": self._converted_count,
            "skipped": self._skipped_count,
            "errors": self._error_count,
            "error_details": list(self._errors),
            "output_dir": str(output),
            "extensions": extensions,
            "nav_items": len(nav_flat),
        }

    def _convert_individual(
        self,
        output_dir: Path,
        project: MkDocsProject,
        nav_flat: list[NavItem],
    ) -> None:
        from pimd.export import ExportConverter

        converter = ExportConverter()

        for item in nav_flat:
            if not item.path:
                self._skipped_count += 1
                continue

            try:
                src_path = resolve_mkdocs_path(item.path, project.docs_dir)
                if not src_path.is_file():
                    self._skipped_count += 1
                    continue

                out_name = src_path.relative_to(project.docs_dir)
                out_path = output_dir / out_name
                out_path.parent.mkdir(parents=True, exist_ok=True)

                converter.convert(
                    str(src_path),
                    "docx",
                    str(out_path.with_suffix(".docx")),
                )
                self._converted_count += 1
            except Exception as exc:
                self._error_count += 1
                self._errors.append((item.title, str(exc)))

    def _convert_merged(
        self,
        output_dir: Path,
        project: MkDocsProject,
        nav_flat: list[NavItem],
    ) -> None:
        from pimd.merge import DocumentMerger

        input_paths: list[Path] = []
        for item in nav_flat:
            if not item.path:
                continue
            try:
                src_path = resolve_mkdocs_path(item.path, project.docs_dir)
                if src_path.is_file():
                    input_paths.append(src_path)
            except Exception:
                pass

        if not input_paths:
            return

        try:
            merger = DocumentMerger()
            out_path = output_dir / "merged.docx"
            merger.merge(input_paths, str(out_path))
            self._converted_count = len(input_paths)
        except Exception as exc:
            self._error_count = len(input_paths)
            self._errors.append(("_merged_", str(exc)))


def _copy_assets(project: MkDocsProject, output_dir: Path) -> None:
    import shutil

    for asset_dir in ("img", "images", "assets", "media"):
        src = project.docs_dir / asset_dir
        if src.is_dir():
            dst = output_dir / asset_dir
            try:
                shutil.copytree(src, dst, dirs_exist_ok=True)
            except Exception:
                pass

# ── Top-level conversion convenience ─────────────────────────────────


def convert_mkdocs_to_pimd(
    source_dir: str | Path,
    output_dir: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    """Convert an MkDocs project to PiMD-ready format.

    Convenience wrapper around ``MkDocsProjectConverter``.
    """
    return MkDocsProjectConverter().convert(source_dir, output_dir, **kwargs)


__all__ = [
    "MkDocsConfig",
    "MkDocsProject",
    "MkDocsProjectConverter",
    "NavItem",
    "build_path_title_map",
    "convert_mkdocs_to_pimd",
    "detect_mkdocs_extensions",
    "detect_mkdocs_project",
    "discover_mkdocs_project",
    "flatten_nav",
    "parse_mkdocs_config",
    "parse_nav",
    "resolve_mkdocs_path",
]
