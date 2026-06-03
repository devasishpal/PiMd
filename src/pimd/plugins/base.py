"""Abstract plugin base class and hook types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

PLUGIN_TYPES = [
    "diagram",
    "template",
    "citation",
    "renderer",
    "exporter",
    "asset",
    "validation",
    "parser",
    "publishing",
]


@dataclass
class PluginMetadata:
    """Metadata describing a PiMD plugin."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    plugin_type: str = ""
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    homepage: str = ""
    license: str = ""


class ConversionHook(Enum):
    """Lifecycle hooks that plugins can attach to."""

    BEFORE_PARSE = "before_parse"
    AFTER_PARSE = "after_parse"
    BEFORE_RENDER = "before_render"
    AFTER_RENDER = "after_render"
    BEFORE_CONVERT = "before_convert"
    AFTER_CONVERT = "after_convert"


class Plugin(ABC):
    """Base class for all PiMD plugins.

    Subclasses override hook methods to inject behaviour into the
    conversion pipeline.

    Usage::

        class MyPlugin(Plugin):
            name = "my_plugin"
            version = "1.0.0"

            def after_parse(self, document, context):
                # Transform the document
                return document
    """

    name: str = ""
    version: str = "0.1.0"
    enabled: bool = True
    description: str = ""

    def __init__(self) -> None:
        if not self.name:
            self.name = type(self).__module__.split(".")[-1]
        self._metadata = PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
        )

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    @metadata.setter
    def metadata(self, value: PluginMetadata) -> None:
        self._metadata = value

    @abstractmethod
    def attach(self, manager: Any) -> None:
        """Register hooks with the plugin manager.

        Subclasses should call ``manager.register(self, hook, method)``
        for each hook they want to attach to.
        """

    def before_parse(self, source: str, context: dict[str, Any]) -> str:
        """Transform the raw input *before* parsing."""
        return source

    def after_parse(self, document: Any, context: dict[str, Any]) -> Any:
        """Transform the parsed document *after* parsing."""
        return document

    def before_render(self, document: Any, context: dict[str, Any]) -> Any:
        """Transform the document *before* rendering."""
        return document

    def after_render(self, output: Any, context: dict[str, Any]) -> Any:
        """Transform the rendered output *after* rendering."""
        return output

    def before_convert(self, context: dict[str, Any]) -> dict[str, Any]:
        """Hook called *before* conversion begins."""
        return context

    def after_convert(self, context: dict[str, Any]) -> dict[str, Any]:
        """Hook called *after* conversion completes."""
        return context

    # Lifecycle hooks
    def on_install(self) -> None:
        """Called when the plugin is installed."""

    def on_uninstall(self) -> None:
        """Called when the plugin is uninstalled."""

    def on_enable(self) -> None:
        """Called when the plugin is enabled."""

    def on_disable(self) -> None:
        """Called when the plugin is disabled."""

    def check_dependencies(self) -> list[str]:
        """Check plugin dependencies. Returns list of missing dependencies."""
        missing: list[str] = []
        for dep in self.metadata.dependencies:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)
        return missing


__all__ = [
    "ConversionHook",
    "PLUGIN_TYPES",
    "Plugin",
    "PluginMetadata",
]
