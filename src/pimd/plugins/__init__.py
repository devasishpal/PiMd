"""Plugin system foundation — registration, hooks, lifecycle."""

from pimd.plugins.base import ConversionHook, Plugin
from pimd.plugins.manager import PluginManager

__all__ = [
    "Plugin",
    "ConversionHook",
    "PluginManager",
]
