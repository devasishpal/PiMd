"""Template service — future template management."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class TemplateService:
    """Manage and apply document templates.

    Currently a placeholder for future template features such as:
    - Loading ``.dotx`` template files
    - Variable substitution
    - Section templates
    - Brand asset injection (logos, colours)
    """

    def __init__(self, template_dir: str | Path | None = None) -> None:
        self._template_dir = Path(template_dir) if template_dir else None
        self._templates: dict[str, Any] = {}

    def list_templates(self) -> list[str]:
        """List available template names."""
        return list(self._templates.keys())

    def load_template(self, name: str, path: str | Path) -> None:
        """Register a template file."""
        self._templates[name] = Path(path)

    def get_template_path(self, name: str) -> Path | None:
        """Return the path for a named template."""
        return self._templates.get(name)
