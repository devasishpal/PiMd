"""Template inheritance — base/child/override mechanism for document templates.

Supports:
- Base templates with common settings
- Child templates that inherit and override
- Partial customization of specific fields
- Multi-level inheritance chains
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pimd.templates.models import Template, TemplateConfig, TemplateMetadata, TemplateType


@dataclass
class InheritanceChain:
    """A chain of template inheritance from base to final child."""

    names: list[str] = field(default_factory=list)
    resolved: list[Template] = field(default_factory=list)

    @property
    def depth(self) -> int:
        return len(self.names)

    @property
    def leaf(self) -> Template | None:
        return self.resolved[-1] if self.resolved else None

    @property
    def root(self) -> Template | None:
        return self.resolved[0] if self.resolved else None


class TemplateInheritance:
    """Resolve template inheritance chains and merge configurations.

    Usage::

        inheritance = TemplateInheritance()
        chain = inheritance.resolve_chain("academic")
        merged = inheritance.merge_chain(chain)
    """

    def __init__(self, template_dir: str | Path | None = None) -> None:
        self._template_dir = Path(template_dir) if template_dir else None
        self._cache: dict[str, Template] = {}

    def _load(self, name: str) -> Template | None:
        if name in self._cache:
            return self._cache[name]

        from pimd.templates.loader import load_template

        tpl = load_template(name)
        if tpl is not None:
            self._cache[name] = tpl
        return tpl

    def resolve_chain(self, name: str) -> InheritanceChain:
        """Resolve the full inheritance chain for a template name.

        Traverses ``parent`` metadata fields to build the chain.
        """
        names: list[str] = []
        resolved: list[Template] = []
        seen: set[str] = set()
        current = name

        while current and current not in seen:
            seen.add(current)
            tpl = self._load(current)
            if tpl is None:
                break
            names.append(current)
            resolved.append(tpl)

            parent_name = tpl.metadata.tags[0] if tpl.metadata.tags and not current.startswith("base_") else None
            if parent_name and parent_name.startswith("base_"):
                current = parent_name
            else:
                break

        return InheritanceChain(names=list(reversed(names)), resolved=list(reversed(resolved)))

    def merge_chain(self, chain: InheritanceChain) -> Template:
        """Merge an inheritance chain into a single effective template.

        Later templates override earlier ones. If the chain is empty,
        returns a default template.
        """
        if not chain.resolved:
            return Template(
                metadata=TemplateMetadata(name="default", type=TemplateType.CUSTOM),
                config=TemplateConfig(),
            )

        base = deepcopy(chain.resolved[0])

        for child in chain.resolved[1:]:
            base.metadata = deepcopy(child.metadata)
            for key, value in child.config.__dict__.items():
                if value is not None and value != "" and not (
                    isinstance(value, (int, float)) and value == 0
                ):
                    setattr(base.config, key, value)
            if child.docx_template_path is not None:
                base.docx_template_path = child.docx_template_path
            if child.content_before:
                base.content_before = child.content_before
            if child.content_after:
                base.content_after = child.content_after

        return base

    def merge_configs(self, *configs: TemplateConfig) -> TemplateConfig:
        """Merge multiple configs into one. Later values win."""
        merged = TemplateConfig()
        defaults = TemplateConfig()
        for cfg in configs:
            for key, value in cfg.__dict__.items():
                default_value = getattr(defaults, key)
                if value != default_value:
                    setattr(merged, key, value)
        return merged

    def create_child(
        self,
        base_name: str,
        child_name: str,
        overrides: dict[str, Any] | None = None,
    ) -> Template:
        """Create a child template that inherits from a base template."""
        tpl = self._load(base_name)
        if tpl is None:
            raise ValueError(f"Base template '{base_name}' not found")

        child_meta = TemplateMetadata(
            name=child_name,
            type=tpl.metadata.type,
            description=f"Child of {base_name}",
            version=tpl.metadata.version,
            author=tpl.metadata.author,
            tags=[base_name],
        )
        child_cfg = deepcopy(tpl.config)
        if overrides:
            for key, value in overrides.items():
                if hasattr(child_cfg, key):
                    setattr(child_cfg, key, value)

        return Template(
            metadata=child_meta,
            config=child_cfg,
            docx_template_path=tpl.docx_template_path,
            content_before=tpl.content_before,
            content_after=tpl.content_after,
        )

    def clear_cache(self) -> None:
        self._cache.clear()
