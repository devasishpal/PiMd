"""Plugin manager — registration, dispatch, lifecycle."""

from __future__ import annotations

from typing import Any

from pimd.plugins.base import ConversionHook, Plugin


class PluginManager:
    """Registry and dispatcher for PiMD plugins.

    Usage::

        manager = PluginManager()
        manager.register(my_plugin, ConversionHook.AFTER_PARSE, my_plugin.after_parse)

        # Dispatch a hook
        document = manager.dispatch(ConversionHook.AFTER_PARSE, document, context=ctx)
    """

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._hooks: dict[ConversionHook, list[tuple[str, Any]]] = {
            hook: [] for hook in ConversionHook
        }

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        plugin: Plugin,
        hook: ConversionHook,
        handler: Any = None,
    ) -> None:
        """Register *plugin* to run *handler* at *hook*.

        Args:
            plugin: The plugin instance.
            hook: The lifecycle hook to attach to.
            handler: The callable (defaults to the hook-named method on the plugin).
        """
        if not plugin.enabled:
            return

        self._plugins[plugin.name] = plugin
        if handler is None:
            handler = getattr(plugin, hook.value.replace("_", ""), None)
            if handler is None:
                handler = getattr(plugin, hook.value, None)

        if handler is not None:
            self._hooks[hook].append((plugin.name, handler))

    def unregister(self, plugin_name: str) -> None:
        """Remove all hooks for *plugin_name*."""
        self._plugins.pop(plugin_name, None)
        for hook in self._hooks:
            self._hooks[hook] = [
                (name, handler) for name, handler in self._hooks[hook] if name != plugin_name
            ]

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, hook: ConversionHook, *args: Any, **kwargs: Any) -> Any:
        """Call all handlers registered for *hook* in registration order.

        Each handler receives ``(value, context)`` and returns the (possibly
        transformed) value, which is passed to the next handler.

        Returns the final value after all handlers have run.
        """
        result = args[0] if args else None
        for _name, handler in self._hooks[hook]:
            try:
                if result is not None:
                    result = handler(result, kwargs.get("context", {}))
                else:
                    handler(*(args[1:]), **kwargs)
            except Exception as exc:
                raise RuntimeError(
                    f"Plugin '{_name}' failed at hook '{hook.value}': {exc}"
                ) from exc
        return result

    # ------------------------------------------------------------------
    # Plugin lifecycle
    # ------------------------------------------------------------------

    def enable(self, plugin_name: str) -> None:
        """Enable a registered plugin."""
        plugin = self._plugins.get(plugin_name)
        if plugin:
            plugin.enabled = True

    def disable(self, plugin_name: str) -> None:
        """Disable a registered plugin."""
        plugin = self._plugins.get(plugin_name)
        if plugin:
            plugin.enabled = False

    def list_plugins(self) -> list[dict[str, str]]:
        """List all registered plugins and their status."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "enabled": str(p.enabled),
            }
            for p in self._plugins.values()
        ]

    @property
    def plugin_count(self) -> int:
        return len(self._plugins)
