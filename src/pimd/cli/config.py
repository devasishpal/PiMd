"""Config system — load settings from ``~/.pimd/config.toml``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pimd.utils.logging import get_logger

logger = get_logger(__name__)

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

_CONFIG_DIR = Path.home() / ".pimd"
_CONFIG_PATH = _CONFIG_DIR / "config.toml"


def _ensure_config_dir() -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    """Load configuration from ``~/.pimd/config.toml``.

    Returns a dictionary with keys merged from the default config.
    Missing keys are filled from :const:`DEFAULT_CONFIG`.
    """
    config: dict[str, Any] = {}
    for section, values in DEFAULT_CONFIG.items():
        config.setdefault(section, {})
        for key, val in values.items():
            config[section].setdefault(key, val)

    if not _CONFIG_PATH.exists():
        return config

    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            logger.debug("tomli not available; skipping config")
            return config

    try:
        with _CONFIG_PATH.open("rb") as fh:
            user_config: dict[str, Any] = tomllib.load(fh)

        for section, values in user_config.items():
            if section not in config:
                config[section] = {}
            if isinstance(values, dict):
                for key, val in values.items():
                    config[section][key] = val
            else:
                config[section] = values
    except Exception as exc:
        logger.debug("Failed to load config: %s", exc)

    return config


def get_config_path() -> Path:
    """Return the path to the configuration file."""
    return _CONFIG_PATH


def write_default_config() -> None:
    """Write a default configuration file to disk.

    Does not overwrite an existing file.
    """
    if _CONFIG_PATH.exists():
        return

    _ensure_config_dir()
    lines = [
        "[defaults]",
        'theme = "professional"',
        'output_directory = ""',
        'author = ""',
        'company = ""',
        "",
        "[logging]",
        'level = "INFO"',
        "",
    ]
    _CONFIG_PATH.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Default config written to %s", _CONFIG_PATH)
