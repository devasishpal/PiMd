"""CLI config loader — thin wrapper around :mod:`pimd.config`.

All public functions delegate to the :class:`pimd.config.Config` class.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pimd.utils.logging import get_logger

__all__ = ["DEFAULT_CONFIG", "get_config_path", "load_config", "write_default_config"]

logger = get_logger(__name__)

_CONFIG_DIR = Path.home() / ".pimd"
_CONFIG_PATH = _CONFIG_DIR / "config.toml"

# Keep a minimal inline DEFAULT_CONFIG so module-level import works
# without triggering circular imports through pimd.config.
DEFAULT_CONFIG: dict[str, Any] = {
    "defaults": {
        "theme": "professional",
        "output_directory": "",
        "author": "",
        "company": "",
    },
    "logging": {
        "level": "INFO",
    },
}


def _ensure_config_dir() -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _lazy_toml_load(path: Path) -> dict[str, Any]:
    """Load a TOML file — helper to keep imports lazy."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return {}
    try:
        with path.open("rb") as fh:
            return dict(tomllib.load(fh))
    except Exception:
        return {}


def load_config() -> dict[str, Any]:
    """Load configuration from ``~/.pimd/config.toml``.

    Returns a dictionary merged from built-in defaults
    with user settings applied on top.
    """
    from pimd.config import Config, ConfigSource

    cfg = Config()
    if _CONFIG_PATH.exists():
        data = _lazy_toml_load(_CONFIG_PATH)
        if data:
            cfg._sources.append(ConfigSource("user", data, 10))
    return cfg.resolve()


def get_config_path() -> Path:
    """Return the path to the configuration file."""
    return _CONFIG_PATH


def write_default_config(path: str | Path | None = None) -> None:
    """Write a default configuration file to disk.

    Uses :meth:`Config.generate_default` for content.
    Does not overwrite an existing file.
    """
    from pimd.config import Config, config_to_toml

    dest = Path(path) if path else _CONFIG_PATH
    if dest.exists():
        return
    if path is None:
        _ensure_config_dir()
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
    defaults = Config.generate_default()
    dest.write_text(config_to_toml(defaults), encoding="utf-8")
    logger.info("Default config written to %s", dest)
