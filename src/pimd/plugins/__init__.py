"""Plugin system foundation — registration, hooks, lifecycle."""

from pimd.plugins.base import PLUGIN_TYPES, ConversionHook, Plugin, PluginMetadata
from pimd.plugins.manager import PluginManager

__all__ = [
    "ConversionHook",
    "PLUGIN_TYPES",
    "Plugin",
    "PluginManager",
    "PluginMetadata",
]
