"""Diagram plugin interface — lifecycle hooks for diagram rendering.

This module re-exports core types from the new SDK-based plugin system
while maintaining full backward compatibility with existing code.

Usage::

    from pimd.diagrams.plugin import DiagramPlugin, DiagramPluginManager, DiagramHook
"""

from __future__ import annotations

from pimd.sdk.base import DiagramHook, DiagramPluginEvent
from pimd.sdk.base import DiagramPlugin as _SdkDiagramPlugin


class DiagramPlugin(_SdkDiagramPlugin):
    """Abstract base class for diagram plugins.

    Subclass this to hook into the diagram rendering pipeline.
    Backward-compatible alias — the canonical version lives in
    :mod:`pimd.sdk.base`.

    Usage::

        class WatermarkPlugin(DiagramPlugin):
            def after_render(self, event):
                # Add watermark to every diagram
                pass
    """


class DiagramPluginManager:
    """Manages registered diagram plugins and dispatches lifecycle events.

    Usage::

        manager = DiagramPluginManager()
        manager.register(WatermarkPlugin())

        event = DiagramPluginEvent(hook=DiagramHook.AFTER_RENDER, ...)
        event = manager.dispatch(DiagramHook.AFTER_RENDER, event)
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
                "name": p.metadata.name,
                "version": p.metadata.version,
                "description": p.metadata.description,
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


__all__ = [
    "DiagramHook",
    "DiagramPlugin",
    "DiagramPluginEvent",
    "DiagramPluginManager",
]
