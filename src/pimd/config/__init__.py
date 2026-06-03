"""Configuration system — global, project, and runtime config with priority resolution.

Priority (highest to lowest):
  1. Runtime / in-code options
  2. Environment variables (PIMD_SECTION_KEY)
  3. Project config (.pimd/config.toml in CWD)
  4. Global user config (~/.pimd/config.toml)
  5. Built-in defaults
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pimd.layout import DocumentLayoutConfig

__all__ = [
    "BUILTIN_DEFAULTS",
    "CONFIG_SCHEMA",
    "Config",
    "ConfigSchemaEntry",
    "ConfigSource",
    "config_to_toml",
    "find_project_root",
    "load_toml",
]

_USER_CONFIG_DIR = Path.home() / ".pimd"
_USER_CONFIG_PATH = _USER_CONFIG_DIR / "config.toml"
_PROJECT_CONFIG_NAME = ".pimdconfig"
_OLD_PROJECT_CONFIG_NAMES = ["pimd.toml", ".pimd/config.toml"]


@dataclass
class ConfigSchemaEntry:
    """Schema definition for a single config key."""

    type: type
    default: Any
    description: str
    required: bool = False
    env_var: str | None = None


CONFIG_SCHEMA: dict[str, ConfigSchemaEntry] = {
    # ── defaults ──────────────────────────────────────────────────
    "defaults.theme": ConfigSchemaEntry(
        type=str,
        default="professional",
        description="Default theme name",
        env_var="PIMD_DEFAULTS_THEME",
    ),
    "defaults.output_directory": ConfigSchemaEntry(
        type=str,
        default="",
        description="Default output directory for generated files",
        env_var="PIMD_DEFAULTS_OUTPUT_DIRECTORY",
    ),
    "defaults.author": ConfigSchemaEntry(
        type=str,
        default="",
        description="Default author name for documents",
        env_var="PIMD_DEFAULTS_AUTHOR",
    ),
    "defaults.company": ConfigSchemaEntry(
        type=str,
        default="",
        description="Default company name",
        env_var="PIMD_DEFAULTS_COMPANY",
    ),
    "defaults.subject": ConfigSchemaEntry(
        type=str,
        default="",
        description="Default document subject",
        env_var="PIMD_DEFAULTS_SUBJECT",
    ),
    "defaults.language": ConfigSchemaEntry(
        type=str,
        default="en-US",
        description="Default document language code",
        env_var="PIMD_DEFAULTS_LANGUAGE",
    ),
    "defaults.page_size": ConfigSchemaEntry(
        type=str,
        default="A4",
        description="Default page size (e.g. A4, Letter)",
        env_var="PIMD_DEFAULTS_PAGE_SIZE",
    ),
    "defaults.margins": ConfigSchemaEntry(
        type=str,
        default="narrow",
        description="Default margin preset (narrow, normal, wide)",
        env_var="PIMD_DEFAULTS_MARGINS",
    ),
    "defaults.default_font": ConfigSchemaEntry(
        type=str,
        default="Calibri",
        description="Default document font family",
        env_var="PIMD_DEFAULTS_DEFAULT_FONT",
    ),
    "defaults.default_font_size": ConfigSchemaEntry(
        type=int,
        default=11,
        description="Default document font size in points",
        env_var="PIMD_DEFAULTS_DEFAULT_FONT_SIZE",
    ),
    # ── conversion ────────────────────────────────────────────────
    "conversion.generate_toc": ConfigSchemaEntry(
        type=bool,
        default=False,
        description="Generate table of contents during conversion",
        env_var="PIMD_CONVERSION_GENERATE_TOC",
    ),
    "conversion.page_numbers": ConfigSchemaEntry(
        type=bool,
        default=False,
        description="Include page numbers in output",
        env_var="PIMD_CONVERSION_PAGE_NUMBERS",
    ),
    "conversion.cover_page": ConfigSchemaEntry(
        type=bool,
        default=False,
        description="Generate a cover page",
        env_var="PIMD_CONVERSION_COVER_PAGE",
    ),
    "conversion.continue_on_error": ConfigSchemaEntry(
        type=bool,
        default=True,
        description="Continue conversion when non-fatal errors occur",
        env_var="PIMD_CONVERSION_CONTINUE_ON_ERROR",
    ),
    "conversion.parallel_diagrams": ConfigSchemaEntry(
        type=bool,
        default=True,
        description="Render diagrams in parallel",
        env_var="PIMD_CONVERSION_PARALLEL_DIAGRAMS",
    ),
    "conversion.parallel_equations": ConfigSchemaEntry(
        type=bool,
        default=False,
        description="Render equations in parallel",
        env_var="PIMD_CONVERSION_PARALLEL_EQUATIONS",
    ),
    "conversion.max_diagram_workers": ConfigSchemaEntry(
        type=int,
        default=4,
        description="Maximum parallel workers for diagram rendering",
        env_var="PIMD_CONVERSION_MAX_DIAGRAM_WORKERS",
    ),
    # ── export ────────────────────────────────────────────────────
    "export.default_format": ConfigSchemaEntry(
        type=str,
        default="docx",
        description="Default export format (docx, pdf, html, md)",
        env_var="PIMD_EXPORT_DEFAULT_FORMAT",
    ),
    "export.pdf_engine": ConfigSchemaEntry(
        type=str,
        default="auto",
        description="PDF export engine (auto, weasyprint, docx2pdf)",
        env_var="PIMD_EXPORT_PDF_ENGINE",
    ),
    "export.compress": ConfigSchemaEntry(
        type=bool,
        default=True,
        description="Compress output files when possible",
        env_var="PIMD_EXPORT_COMPRESS",
    ),
    # ── security ──────────────────────────────────────────────────
    "security.max_input_size_mb": ConfigSchemaEntry(
        type=int,
        default=100,
        description="Maximum input file size in MB",
        env_var="PIMD_SECURITY_MAX_INPUT_SIZE_MB",
    ),
    "security.max_nesting_depth": ConfigSchemaEntry(
        type=int,
        default=100,
        description="Maximum allowed nesting depth for includes",
        env_var="PIMD_SECURITY_MAX_NESTING_DEPTH",
    ),
    "security.max_document_blocks": ConfigSchemaEntry(
        type=int,
        default=100000,
        description="Maximum number of document blocks before abort",
        env_var="PIMD_SECURITY_MAX_DOCUMENT_BLOCKS",
    ),
    "security.max_image_size_mb": ConfigSchemaEntry(
        type=int,
        default=10,
        description="Maximum image file size in MB",
        env_var="PIMD_SECURITY_MAX_IMAGE_SIZE_MB",
    ),
    "security.allowed_paths": ConfigSchemaEntry(
        type=list,
        default=[],
        description="List of allowed file paths for include directives",
        env_var="PIMD_SECURITY_ALLOWED_PATHS",
    ),
    "security.blocked_paths": ConfigSchemaEntry(
        type=list,
        default=[],
        description="List of blocked file paths for include directives",
        env_var="PIMD_SECURITY_BLOCKED_PATHS",
    ),
    # ── cache ─────────────────────────────────────────────────────
    "cache.enabled": ConfigSchemaEntry(
        type=bool,
        default=True,
        description="Enable caching of rendered output",
        env_var="PIMD_CACHE_ENABLED",
    ),
    "cache.backend": ConfigSchemaEntry(
        type=str,
        default="memory",
        description="Cache backend (memory, redis)",
        env_var="PIMD_CACHE_BACKEND",
    ),
    "cache.redis_url": ConfigSchemaEntry(
        type=str,
        default="redis://localhost:6379/0",
        description="Redis connection URL",
        env_var="PIMD_CACHE_REDIS_URL",
    ),
    "cache.diagram_ttl": ConfigSchemaEntry(
        type=int,
        default=86400,
        description="TTL in seconds for cached diagrams",
        env_var="PIMD_CACHE_DIAGRAM_TTL",
    ),
    "cache.equation_ttl": ConfigSchemaEntry(
        type=int,
        default=86400,
        description="TTL in seconds for cached equations",
        env_var="PIMD_CACHE_EQUATION_TTL",
    ),
    # ── logging ───────────────────────────────────────────────────
    "logging.level": ConfigSchemaEntry(
        type=str,
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        env_var="PIMD_LOGGING_LEVEL",
    ),
    "logging.file": ConfigSchemaEntry(
        type=str,
        default="",
        description="Log file path (empty = stderr)",
        env_var="PIMD_LOGGING_FILE",
    ),
    # ── layout ────────────────────────────────────────────────────
    "layout.page_size": ConfigSchemaEntry(
        type=str,
        default="A4",
        description="Layout page size",
        env_var="PIMD_LAYOUT_PAGE_SIZE",
    ),
    "layout.orientation": ConfigSchemaEntry(
        type=str,
        default="portrait",
        description="Page orientation (portrait, landscape)",
        env_var="PIMD_LAYOUT_ORIENTATION",
    ),
    "layout.margin_top": ConfigSchemaEntry(
        type=float,
        default=0.5,
        description="Top margin in inches",
        env_var="PIMD_LAYOUT_MARGIN_TOP",
    ),
    "layout.margin_bottom": ConfigSchemaEntry(
        type=float,
        default=0.5,
        description="Bottom margin in inches",
        env_var="PIMD_LAYOUT_MARGIN_BOTTOM",
    ),
    "layout.margin_left": ConfigSchemaEntry(
        type=float,
        default=0.5,
        description="Left margin in inches",
        env_var="PIMD_LAYOUT_MARGIN_LEFT",
    ),
    "layout.margin_right": ConfigSchemaEntry(
        type=float,
        default=0.5,
        description="Right margin in inches",
        env_var="PIMD_LAYOUT_MARGIN_RIGHT",
    ),
    # ── diagram ───────────────────────────────────────────────────
    "diagram.cache": ConfigSchemaEntry(
        type=bool,
        default=True,
        description="Cache rendered diagrams",
        env_var="PIMD_DIAGRAM_CACHE",
    ),
    "diagram.svg_preferred": ConfigSchemaEntry(
        type=bool,
        default=True,
        description="Prefer SVG output for diagrams",
        env_var="PIMD_DIAGRAM_SVG_PREFERRED",
    ),
    "diagram.max_width": ConfigSchemaEntry(
        type=float,
        default=6.5,
        description="Maximum diagram width in inches",
        env_var="PIMD_DIAGRAM_MAX_WIDTH",
    ),
    "diagram.figure_captions": ConfigSchemaEntry(
        type=bool,
        default=True,
        description="Generate figure captions for diagrams",
        env_var="PIMD_DIAGRAM_FIGURE_CAPTIONS",
    ),
    "diagram.auto_number": ConfigSchemaEntry(
        type=bool,
        default=True,
        description="Auto-number diagrams",
        env_var="PIMD_DIAGRAM_AUTO_NUMBER",
    ),
    "diagram.detect_diagrams": ConfigSchemaEntry(
        type=bool,
        default=True,
        description="Auto-detect diagram blocks in markdown",
        env_var="PIMD_DIAGRAM_DETECT_DIAGRAMS",
    ),
    "diagram.default_dpi": ConfigSchemaEntry(
        type=int,
        default=150,
        description="Default DPI for raster diagram output",
        env_var="PIMD_DIAGRAM_DEFAULT_DPI",
    ),
}

BUILTIN_DEFAULTS: dict[str, Any] = {
    section: {
        key.split(".", 1)[1]: entry.default
        for key, entry in CONFIG_SCHEMA.items()
        if key.startswith(section + ".")
    }
    for section in {k.split(".")[0] for k in CONFIG_SCHEMA}
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

    def load_global(self, path: str | Path | None = None) -> Config:
        """Load global user config (~/.pimd/config.toml)."""
        config_path = Path(path) if path else _USER_CONFIG_PATH
        if config_path.exists():
            data = load_toml(config_path)
            self._sources.append(ConfigSource("global", data, 10))
        return self

    def load_project(self, project_dir: str | Path | None = None) -> Config:
        """Load project-level config from CWD or specified directory."""
        search_dir = Path(project_dir) if project_dir else Path.cwd()
        for name in [_PROJECT_CONFIG_NAME]:
            candidate = search_dir / name
            if candidate.exists():
                data = load_toml(candidate)
                self._sources.append(ConfigSource(f"project:{candidate}", data, 20))
                return self
        for name in _OLD_PROJECT_CONFIG_NAMES:
            candidate = search_dir / name
            if candidate.exists():
                data = load_toml(candidate)
                self._sources.append(ConfigSource(f"project:{candidate}", data, 20))
                return self
        return self

    def apply_runtime(self, overrides: dict[str, Any]) -> Config:
        """Apply runtime overrides (highest priority)."""
        if overrides:
            self._sources.append(ConfigSource("runtime", overrides, 30))
        return self

    def apply_env(self) -> Config:
        """Apply environment variable overrides (PIMD_SECTION_KEY pattern).

        Reads environment variables matching ``PIMD_{SECTION}_{KEY}`` and
        injects them as runtime overrides with type coercion.
        """
        overrides: dict[str, Any] = {}
        for key, entry in CONFIG_SCHEMA.items():
            if entry.env_var is None:
                continue
            env_val = os.environ.get(entry.env_var)
            if env_val is None:
                continue
            parsed = _parse_env_value(env_val, entry.type)
            parts = key.split(".")
            current = overrides
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = parsed
        if overrides:
            self.apply_runtime(overrides)
        return self

    def resolve(self) -> dict[str, Any]:
        """Resolve all sources into a single merged config dict.

        Priority: env / runtime > project > global > builtin defaults.
        """
        merged: dict[str, Any] = {}
        self._deep_merge(merged, copy.deepcopy(BUILTIN_DEFAULTS))

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

    def validate(self) -> list[str]:
        """Validate resolved config against CONFIG_SCHEMA.

        Returns a list of error messages (empty = valid).
        Collects all errors, does not fail on first one.
        """
        errors: list[str] = []
        resolved = self.resolve()
        for key, entry in CONFIG_SCHEMA.items():
            parts = key.split(".")
            current: Any = resolved
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    current = None
                    break
            if current is None:
                if entry.required:
                    errors.append(f"{key}: required but missing")
                continue
            if not isinstance(current, entry.type):
                errors.append(
                    f"{key}: expected {entry.type.__name__}, got {type(current).__name__} (value: {current!r})"
                )
        return errors

    @classmethod
    def generate_default(cls) -> dict[str, Any]:
        """Generate a default configuration dict from CONFIG_SCHEMA."""
        defaults: dict[str, Any] = {}
        for key, entry in CONFIG_SCHEMA.items():
            parts = key.split(".")
            current = defaults
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = entry.default
        return defaults

    @classmethod
    def write_default(cls, path: str | Path) -> Path:
        """Write a default configuration file to *path*.

        Does not overwrite an existing file.
        Returns the path that was written (or that already existed).
        """
        dest = Path(path)
        if dest.exists():
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        config = cls.generate_default()
        dest.write_text(config_to_toml(config), encoding="utf-8")
        return dest

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


# ── helpers ────────────────────────────────────────────────────────


def load_toml(path: Path) -> dict[str, Any]:
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


# Backward compat alias
_load_toml = load_toml


def config_to_toml(config: dict[str, Any], header: str = "") -> str:
    """Serialize a nested config dict to TOML format string."""
    lines: list[str] = []
    if header:
        lines.append(header)
        lines.append("")
    for section, values in config.items():
        if isinstance(values, dict):
            lines.append(f"[{section}]")
            for key, val in values.items():
                lines.append(f"{key} = {_toml_repr(val)}")
            lines.append("")
        else:
            lines.append(f"{section} = {_toml_repr(values)}")
            lines.append("")
    return "\n".join(lines)


def _toml_repr(val: Any) -> str:
    """Format a value as a TOML literal."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int | float):
        return str(val)
    if isinstance(val, str):
        escaped = val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    if isinstance(val, list):
        items = [_toml_repr(v) for v in val]
        return f"[{', '.join(items)}]"
    return str(val)


def _parse_env_value(val: str, target_type: type) -> Any:
    """Parse an environment variable string to the target type."""
    if target_type is bool:
        return val.lower() in ("true", "1", "yes", "y")
    if target_type is int:
        return int(val)
    if target_type is float:
        return float(val)
    if target_type is list:
        try:
            import json

            return json.loads(val)
        except Exception:
            return [x.strip() for x in val.split(",") if x.strip()]
    return val


def find_project_root(marker: str = ".pimdconfig") -> Path | None:
    """Walk up from CWD to find a project root marker file."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / marker).exists():
            return parent
    return None
