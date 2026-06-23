"""Template service — load, manage, and apply document templates."""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path
from typing import Any

from pimd.templates.models import Template, TemplateConfig, TemplateType

logger = logging.getLogger("pimd")


class TemplateService:
    """Manage and apply document templates.

    Supports:
    - Loading ``.dotx`` and ``.docx`` template files
    - Variable substitution (``{{ var }}`` placeholders)
    - Section templates with per-section overrides
    - Brand asset injection (logos, colours, fonts)
    - Built-in template presets (Professional, Technical, Academic, Business, Book)
    """

    def __init__(self, template_dir: str | Path | None = None) -> None:
        self._template_dir = Path(template_dir) if template_dir else None
        self._templates: dict[str, Template] = {}
        self._load_builtins()

    def _load_builtins(self) -> None:
        """Register built-in template presets."""
        from pimd.templates.models import TemplateMetadata

        builtins: dict[str, tuple[str, TemplateType]] = {
            "professional": ("Professional document template", TemplateType.PROFESSIONAL),
            "technical": ("Technical document template", TemplateType.TECHNICAL),
            "academic": ("Academic paper template", TemplateType.ACADEMIC),
            "business": ("Business report template", TemplateType.BUSINESS),
            "book": ("Book manuscript template", TemplateType.BOOK),
            "invoice": ("Professional invoice template", TemplateType.INVOICE),
            "api": ("API documentation template", TemplateType.API),
            "manual": ("Technical user manual template", TemplateType.MANUAL),
            "proposal": ("Business proposal template", TemplateType.PROPOSAL),
            "resume": ("Professional resume template", TemplateType.RESUME),
        }
        for name, (desc, ttype) in builtins.items():
            self._templates[name] = Template(
                metadata=TemplateMetadata(name=name, type=ttype, description=desc),
                config=TemplateConfig(),
            )

    def list_templates(self) -> list[str]:
        """List available template names."""
        return list(self._templates.keys())

    def load_template(self, name: str, path: str | Path) -> None:
        """Load and register a template from a file.

        Args:
            name: Template identifier.
            path: Path to the ``.docx`` or ``.dotx`` template file.

        Raises:
            FileNotFoundError: If the template file does not exist.
        """
        from pimd.templates.models import TemplateMetadata

        template_path = Path(path)
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        self._templates[name] = Template(
            metadata=TemplateMetadata(name=name, type=TemplateType.CUSTOM, description=f"User template from {template_path.name}"),
            config=TemplateConfig(),
            docx_template_path=template_path,
        )
        logger.debug("Loaded template '%s' from %s", name, template_path)

    def get_template(self, name: str) -> Template | None:
        """Return the template object for a named template."""
        return self._templates.get(name)

    def get_template_path(self, name: str) -> Path | None:
        """Return the file path for a named template, if one exists."""
        tmpl = self._templates.get(name)
        return tmpl.docx_template_path if tmpl else None

    def get_reference_doc_path(self, name: str) -> Path | None:
        """Return the reference doc path for a built-in template preset, if one exists.

        Checks for ``reference.docx`` in the preset directory.
        """
        preset_dir = Path(__file__).resolve().parent.parent / "templates" / "presets" / name
        if preset_dir.is_dir():
            ref_path = preset_dir / "reference.docx"
            if ref_path.exists():
                return ref_path
        return None

    def apply_template(
        self,
        template_name: str,
        variables: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Resolve template configuration with variable substitution.

        Args:
            template_name: Name of the template to apply.
            variables: Key-value pairs for ``{{ var }}`` substitution.

        Returns:
            A dictionary of resolved template configuration values.

        Raises:
            ValueError: If the template name is unknown.
        """
        tmpl = self._templates.get(template_name)
        if tmpl is None:
            raise ValueError(f"Unknown template: {template_name}. Available: {list(self._templates)}")

        resolved = dataclasses.asdict(tmpl.config)

        if variables:
            resolved = self._substitute_variables(resolved, variables)

        return resolved

    def _substitute_variables(
        self,
        config: dict[str, Any],
        variables: dict[str, str],
    ) -> dict[str, Any]:
        """Replace ``{{ var }}`` placeholders in string values.

        Works recursively through nested dictionaries and lists.
        """
        result: dict[str, Any] = {}
        for key, value in config.items():
            if isinstance(value, str):
                result[key] = _replace_vars(value, variables)
            elif isinstance(value, dict):
                result[key] = self._substitute_variables(value, variables)
            elif isinstance(value, list):
                result[key] = [
                    self._substitute_variables(item, variables) if isinstance(item, dict)
                    else _replace_vars(item, variables) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def template_exists(self, name: str) -> bool:
        """Check if a template name is registered."""
        return name in self._templates


def _replace_vars(text: str, variables: dict[str, str]) -> str:
    """Replace ``{{ key }}`` placeholders with variable values."""
    for key, value in variables.items():
        text = text.replace("{{ " + key + " }}", value).replace("{{" + key + "}}", value)
    return text
