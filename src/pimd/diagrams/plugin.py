"""Diagram plugin interface — lifecycle hooks for diagram rendering.

Third-party plugins can subclass :class:`DiagramPlugin` and register
with the :class:`DiagramPluginManager` to hook into the diagram
rendering pipeline at every stage.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pimd.diagrams.models import DiagramContext, DiagramResult


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
    """Event data passed to plugin hooks."""

    hook: DiagramHook
    context: DiagramContext
    result: DiagramResult | None = None
    renderer_name: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class DiagramPlugin(ABC):
    """Abstract base class for diagram plugins.

    Implement any combination of the hook methods. All are optional
    — the base class provides no-op defaults.

    Usage::

        class WatermarkPlugin(DiagramPlugin):
            def after_render(self, event: DiagramPluginEvent) -> None:
                # Add watermark to every diagram
                pass
    """

    name: str = "unnamed"
    version: str = "0.1.0"
    description: str = ""

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


class DiagramPluginManager:
    """Manages registered diagram plugins and dispatches lifecycle events.

    Usage::

        manager = DiagramPluginManager()
        manager.register(WatermarkPlugin())

        event = DiagramPluginEvent(hook=DiagramHook.AFTER_RENDER, ...)
        for event in manager.dispatch(DiagramHook.AFTER_RENDER, event):
            ...
    """

    def __init__(self) -> None:
        self._plugins: list[DiagramPlugin] = []

    def register(self, plugin: DiagramPlugin) -> None:
        """Register a diagram plugin."""
        self._plugins.append(plugin)

    def unregister(self, plugin: DiagramPlugin) -> None:
        """Remove a previously registered plugin."""
        self._plugins.remove(plugin)

    def list_plugins(self) -> list[dict[str, str]]:
        """Return metadata for all registered plugins."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
            }
            for p in self._plugins
        ]

    def dispatch(
        self,
        hook: DiagramHook,
        event: DiagramPluginEvent,
    ) -> DiagramPluginEvent:
        """Dispatch an event to all registered plugins for the given hook.

        Each plugin receives the (possibly-modified) event from the
        previous plugin, forming a pipeline.

        Args:
            hook: The lifecycle hook to dispatch to.
            event: The initial event data.

        Returns:
            The final event after all plugins have processed it.
        """
        method_map = {
            DiagramHook.BEFORE_RENDER: "before_render",
            DiagramHook.AFTER_RENDER: "after_render",
            DiagramHook.BEFORE_CACHE: "before_cache",
            DiagramHook.AFTER_CACHE: "after_cache",
            DiagramHook.BEFORE_EMBED: "before_embed",
            DiagramHook.AFTER_EMBED: "after_embed",
            DiagramHook.ON_ERROR: "on_error",
            DiagramHook.ON_FALLBACK: "on_fallback",
        }
        method_name = method_map.get(hook)
        if method_name is None:
            return event

        for plugin in self._plugins:
            method = getattr(plugin, method_name)
            event = method(event)

        return event
