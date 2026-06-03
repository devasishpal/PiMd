"""Template manager — central registry for loading, listing, and applying templates."""

from __future__ import annotations

from pathlib import Path

from pimd.templates.loader import discover_templates, load_template
from pimd.templates.models import Template, TemplateConfig, TemplateType
from pimd.templates.validator import ValidationResult, validate_template


class TemplateManager:
    """Central registry and application logic for document templates."""

    def __init__(self) -> None:
        self._cache: dict[str, Template] = {}

    def list_templates(self, type_filter: TemplateType | None = None) -> list[Template]:
        """List all discovered templates, optionally filtered by type."""
        templates = discover_templates()
        if type_filter is not None:
            templates = [t for t in templates if t.type == type_filter]
        for t in templates:
            self._cache[t.name] = t
        return templates

    def get(self, name: str) -> Template | None:
        """Retrieve a template by name (cached after first load)."""
        if name in self._cache:
            return self._cache[name]
        tpl = load_template(name)
        if tpl is not None:
            self._cache[name] = tpl
        return tpl

    def validate(self, name: str) -> ValidationResult:
        """Validate a template by name."""
        tpl = self.get(name)
        if tpl is None:
            return ValidationResult(valid=False, errors=[f"Template '{name}' not found"])
        return validate_template(tpl)

    def resolve_config(
        self, name: str, overrides: dict[str, object] | None = None
    ) -> TemplateConfig:
        """Resolve the effective config for a template, merging overrides."""
        tpl = self.get(name)
        if tpl is None:
            return TemplateConfig(**(overrides or {}))
        return tpl.merge_config(overrides or {})

    def refresh(self) -> None:
        """Clear the cache and re-discover templates."""
        self._cache.clear()

    def builtin_names(self) -> list[str]:
        """Return names of built-in (preset) templates only."""
        pkg_dir = Path(__file__).resolve().parent / "presets"
        if not pkg_dir.is_dir():
            return []
        return [d.name for d in pkg_dir.iterdir() if d.is_dir()]
