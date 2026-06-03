"""Extension SDK for PiMD — base classes, hooks, and events for plugin authors."""

from pimd.sdk.base import (
    AssetPlugin,
    BasePlugin,
    CitationPlugin,
    DiagramPlugin,
    ExporterPlugin,
    ParserPlugin,
    PublishingPlugin,
    RendererPlugin,
    TemplatePlugin,
    ValidationPlugin,
)
from pimd.sdk.events import Event, EventBus, EventHandler, EventPriority
from pimd.sdk.hooks import Hook, HookRegistry, HookScope, LifecycleHook

__all__ = [
    "BasePlugin",
    "DiagramPlugin",
    "TemplatePlugin",
    "CitationPlugin",
    "RendererPlugin",
    "ExporterPlugin",
    "AssetPlugin",
    "ValidationPlugin",
    "ParserPlugin",
    "PublishingPlugin",
    "Hook",
    "HookRegistry",
    "HookScope",
    "LifecycleHook",
    "Event",
    "EventBus",
    "EventHandler",
    "EventPriority",
]
