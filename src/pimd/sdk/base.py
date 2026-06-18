"""Plugin base classes for the PiMD Extension SDK.

Each plugin type provides typed hook methods that subclasses override
to inject behaviour into PiMD's pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pimd.diagrams.models import DiagramContext, DiagramResult
from pimd.plugins.base import Plugin, PluginMetadata

# ---------------------------------------------------------------------------
# Diagram-specific types (absorbed from pimd.diagrams.plugin)
# ---------------------------------------------------------------------------


class DiagramHook(str, Enum):
    """Diagram pipeline lifecycle hook points."""

    BEFORE_RENDER = "before_render"
    AFTER_RENDER = "after_render"
    BEFORE_CACHE = "before_cache"
    AFTER_CACHE = "after_cache"
    BEFORE_EMBED = "before_embed"
    AFTER_EMBED = "after_embed"
    ON_ERROR = "on_error"
    ON_FALLBACK = "on_fallback"


@dataclass
class DiagramPluginEvent:
    """Event data passed to diagram plugin hooks."""

    hook: DiagramHook
    context: DiagramContext
    result: DiagramResult | None = None
    renderer_name: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# SDK base — extends pimd.plugins.base.Plugin for backward compatibility
# ---------------------------------------------------------------------------


class BasePlugin(Plugin):
    """Base class all PiMD plugins must inherit when using the SDK.

    Extends :class:`pimd.plugins.base.Plugin` with a typed
    :attr:`metadata` attribute and provides a consistent interface
    for the plugin system.

    Usage::

        class MyPlugin(BasePlugin):
            metadata = PluginMetadata(
                name="my_plugin",
                version="1.0.0",
                description="Does something useful",
            )
    """

    metadata: PluginMetadata

    def attach(self, manager: Any) -> None:
        """Default no-op implementation so SDK users need not override."""
        pass

    def __init__(self) -> None:
        super().__init__()
        if not self.metadata.name:
            self.metadata = PluginMetadata(
                name=self.name,
                version=self.version,
                description=self.description,
            )


# ---------------------------------------------------------------------------
# Type-specific plugin bases
# ---------------------------------------------------------------------------


class DiagramPlugin(BasePlugin):
    """Plugin that hooks into the diagram rendering pipeline.

    Implement any combination of the hook methods. All are optional
    — the base class provides no-op defaults.
    """

    def __init__(self) -> None:
        super().__init__()
        if not self.metadata.plugin_type:
            self.metadata.plugin_type = "diagram"

    def before_render(self, event: DiagramPluginEvent) -> DiagramPluginEvent:
        """Called before a diagram is rendered. May modify the context."""
        return event

    def after_render(self, event: DiagramPluginEvent) -> DiagramPluginEvent:
        """Called after a diagram is rendered. May inspect or modify results."""
        return event

    def before_cache(self, event: DiagramPluginEvent) -> DiagramPluginEvent:
        """Called before checking the cache. May modify the cache key."""
        return event

    def after_cache(self, event: DiagramPluginEvent) -> DiagramPluginEvent:
        """Called after a cache hit/miss. May log or modify."""
        return event

    def before_embed(self, event: DiagramPluginEvent) -> DiagramPluginEvent:
        """Called before embedding a diagram into the output document."""
        return event

    def after_embed(self, event: DiagramPluginEvent) -> DiagramPluginEvent:
        """Called after embedding into the output document."""
        return event

    def on_error(self, event: DiagramPluginEvent) -> DiagramPluginEvent:
        """Called when a diagram renderer raises an error."""
        return event

    def on_fallback(self, event: DiagramPluginEvent) -> DiagramPluginEvent:
        """Called when a diagram falls back to a simpler rendering."""
        return event


class TemplatePlugin(BasePlugin):
    """Plugin that hooks into the template system."""

    def __init__(self) -> None:
        super().__init__()
        if not self.metadata.plugin_type:
            self.metadata.plugin_type = "template"

    def on_template_load(self, template_name: str, context: dict[str, Any]) -> dict[str, Any]:
        """Called when a template is loaded. May modify the context."""
        return context

    def on_template_render(self, output: str, template_name: str) -> str:
        """Called after a template is rendered. May modify the output."""
        return output


class CitationPlugin(BasePlugin):
    """Plugin that hooks into the citation engine."""

    def __init__(self) -> None:
        super().__init__()
        if not self.metadata.plugin_type:
            self.metadata.plugin_type = "citation"

    def on_citation_load(self, citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Called when citations are loaded. May add or modify entries."""
        return citations

    def on_citation_render(self, bibliography: str, style: str) -> str:
        """Called after the bibliography is rendered."""
        return bibliography


class RendererPlugin(BasePlugin):
    """Plugin that hooks into the document rendering pipeline."""

    def __init__(self) -> None:
        super().__init__()
        if not self.metadata.plugin_type:
            self.metadata.plugin_type = "renderer"

    def before_document_render(self, document: Any, context: dict[str, Any]) -> Any:
        """Called before the document is rendered to the output format."""
        return document

    def after_document_render(self, output: Any, context: dict[str, Any]) -> Any:
        """Called after the document is rendered to the output format."""
        return output


class ExporterPlugin(BasePlugin):
    """Plugin that hooks into the export pipeline."""

    def __init__(self) -> None:
        super().__init__()
        if not self.metadata.plugin_type:
            self.metadata.plugin_type = "exporter"

    def before_export(self, document: Any, export_format: str) -> Any:
        """Called before export begins."""
        return document

    def after_export(self, result: Any, export_format: str) -> Any:
        """Called after export completes."""
        return result


class AssetPlugin(BasePlugin):
    """Plugin that manages or transforms assets (images, fonts, etc.)."""

    def __init__(self) -> None:
        super().__init__()
        if not self.metadata.plugin_type:
            self.metadata.plugin_type = "asset"

    def on_asset_resolve(self, asset_path: str) -> str:
        """Called when an asset path is being resolved."""
        return asset_path

    def on_asset_process(self, asset_data: bytes, asset_type: str) -> bytes:
        """Called to transform asset data before embedding."""
        return asset_data


class ValidationPlugin(BasePlugin):
    """Plugin that performs document validation."""

    def __init__(self) -> None:
        super().__init__()
        if not self.metadata.plugin_type:
            self.metadata.plugin_type = "validation"

    def on_validate(self, document: Any) -> list[dict[str, Any]]:
        """Called during validation. Return a list of issue dicts.

        Each issue dict should contain ``severity``, ``message``,
        and optionally ``location``.
        """
        return []


class ParserPlugin(BasePlugin):
    """Plugin that hooks into the parsing stage."""

    def __init__(self) -> None:
        super().__init__()
        if not self.metadata.plugin_type:
            self.metadata.plugin_type = "parser"

    def on_parse_start(self, source: str, fmt: str) -> str:
        """Called before parsing begins. May transform the source."""
        return source

    def on_parse_end(self, document: Any, fmt: str) -> Any:
        """Called after parsing completes. May transform the document."""
        return document


class PublishingPlugin(BasePlugin):
    """Plugin that hooks into the publishing pipeline."""

    def __init__(self) -> None:
        super().__init__()
        if not self.metadata.plugin_type:
            self.metadata.plugin_type = "publishing"

    def before_publish(self, document: Any, target: str) -> Any:
        """Called before publishing to a target."""
        return document

    def after_publish(self, result: Any, target: str) -> Any:
        """Called after publishing to a target."""
        return result


__all__ = [
    "AssetPlugin",
    "BasePlugin",
    "CitationPlugin",
    "DiagramHook",
    "DiagramPlugin",
    "DiagramPluginEvent",
    "ExporterPlugin",
    "ParserPlugin",
    "PublishingPlugin",
    "RendererPlugin",
    "TemplatePlugin",
    "ValidationPlugin",
]
