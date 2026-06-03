"""Configuration system — global, project, and runtime config with priority resolution.

Priority (highest to lowest):
  1. Runtime / in-code options
  2. Project config (.pimd/config.toml in CWD)
  3. Global user config (~/.pimd/config.toml)
  4. Built-in defaults
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pimd.layout import DocumentLayoutConfig

_USER_CONFIG_DIR = Path.home() / ".pimd"
_USER_CONFIG_PATH = _USER_CONFIG_DIR / "config.toml"
_PROJECT_CONFIG_NAME = ".pimdconfig"
_OLD_PROJECT_CONFIG_NAMES = ["pimd.toml", ".pimd/config.toml"]

BUILTIN_DEFAULTS: dict[str, Any] = {
    "defaults": {
        "theme": "professional",
        "output_directory": "",
        "author": "",
        "company": "",
        "subject": "",
        "language": "en-US",
        "page_size": "A4",
        "margins": "narrow",
        "default_font": "Calibri",
        "default_font_size": 11,
    },
    "conversion": {
        "generate_toc": False,
        "page_numbers": False,
        "cover_page": False,
        "continue_on_error": True,
        "parallel_diagrams": True,
        "parallel_equations": False,
        "max_diagram_workers": 4,
    },
    "export": {
        "default_format": "docx",
        "pdf_engine": "auto",
        "compress": True,
    },
    "security": {
        "max_input_size_mb": 100,
        "max_nesting_depth": 100,
        "max_document_blocks": 100000,
        "max_image_size_mb": 10,
        "allowed_paths": [],
        "blocked_paths": [],
    },
    "cache": {
        "enabled": True,
        "backend": "memory",
        "redis_url": "redis://localhost:6379/0",
        "diagram_ttl": 86400,
        "equation_ttl": 86400,
    },
    "logging": {
        "level": "INFO",
        "file": "",
    },
    "layout": {
        "page_size": "A4",
        "orientation": "portrait",
        "margin_top": 0.5,
        "margin_bottom": 0.5,
        "margin_left": 0.5,
        "margin_right": 0.5,
    },
    "diagram": {
        "cache": True,
        "svg_preferred": True,
        "max_width": 6.5,
        "figure_captions": True,
        "auto_number": True,
        "detect_diagrams": True,
        "default_dpi": 150,
    },
}


@dataclass
class ConfigSource:
    """A configuration source with its priority level."""

    name: str
    data: dict[str, Any]
    priority: int  # higher = more important


class Config:
    """Hierarchical configuration with priority resolution.

    Usage::

        cfg = Config()
        cfg.load_global()
        cfg.load_project()
        cfg.apply_runtime({"defaults": {"author": "me"}})
        val = cfg.get("defaults.theme")
    """

    def __init__(self) -> None:
        self._sources: list[ConfigSource] = []

    def load_global(self) -> Config:
        """Load global user config (~/.pimd/config.toml)."""
        if _USER_CONFIG_PATH.exists():
            data = _load_toml(_USER_CONFIG_PATH)
            self._sources.append(ConfigSource("global", data, 10))
        return self

    def load_project(self, project_dir: str | Path | None = None) -> Config:
        """Load project-level config from CWD or specified directory."""
        search_dir = Path(project_dir) if project_dir else Path.cwd()
        for name in [_PROJECT_CONFIG_NAME]:
            candidate = search_dir / name
            if candidate.exists():
                data = _load_toml(candidate)
                self._sources.append(ConfigSource(f"project:{candidate}", data, 20))
                return self
        for name in _OLD_PROJECT_CONFIG_NAMES:
            candidate = search_dir / name
            if candidate.exists():
                data = _load_toml(candidate)
                self._sources.append(ConfigSource(f"project:{candidate}", data, 20))
                return self
        return self

    def apply_runtime(self, overrides: dict[str, Any]) -> Config:
        """Apply runtime overrides (highest priority)."""
        if overrides:
            self._sources.append(ConfigSource("runtime", overrides, 30))
        return self

    def resolve(self) -> dict[str, Any]:
        """Resolve all sources into a single merged config dict.

        Priority: runtime > project > global > builtin defaults.
        """
        merged: dict[str, Any] = {}
        self._deep_merge(merged, BUILTIN_DEFAULTS)

        # Load sources in priority order
        sorted_sources = sorted(self._sources, key=lambda s: s.priority)
        for source in sorted_sources:
            self._deep_merge(merged, source.data)

        return merged

    def get(self, key: str, default: Any = None) -> Any:
        """Get a dotted config value (e.g. 'defaults.theme')."""
        resolved = self.resolve()
        parts = key.split(".")
        current = resolved
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default
        return current

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> None:
        """Recursively merge override into base."""
        for key, val in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(val, dict):
                self._deep_merge(base[key], val)
            else:
                base[key] = val

    def to_layout_config(self) -> DocumentLayoutConfig:
        """Build a DocumentLayoutConfig from resolved config."""
        resolved = self.resolve()
        layout = resolved.get("layout", {})
        return DocumentLayoutConfig(
            page_size=layout.get("page_size", "A4"),
            margins=type(
                "Margins",
                (),
                {
                    "top": layout.get("margin_top", 0.5),
                    "bottom": layout.get("margin_bottom", 0.5),
                    "left": layout.get("margin_left", 0.5),
                    "right": layout.get("margin_right", 0.5),
                },
            )(),
            default_font=layout.get("default_font", "Calibri"),
            default_font_size=layout.get("default_font_size", 11),
        )

    def find_config_files(self) -> list[Path]:
        """Find all existing config files in priority order."""
        files: list[Path] = [p for p in [_USER_CONFIG_PATH] if p.exists()]
        cwd_project = Path.cwd() / _PROJECT_CONFIG_NAME
        if cwd_project.exists():
            files.append(cwd_project)
        for name in _OLD_PROJECT_CONFIG_NAMES:
            p = Path.cwd() / name
            if p.exists():
                files.append(p)
                break
        return files


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file and return as dict."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return {}
    try:
        with path.open("rb") as f:
            return dict(tomllib.load(f))
    except Exception:
        return {}


def find_project_root(marker: str = ".pimdconfig") -> Path | None:
    """Walk up from CWD to find a project root marker file."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / marker).exists():
            return parent
    return None
