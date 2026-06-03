"""Lifecycle hook system definition for the PiMD Extension SDK.

Provides the formal hook abstraction that plugin types implement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HookScope(str, Enum):
    """Scope of a lifecycle hook."""

    CONVERSION = "conversion"
    DIAGRAM = "diagram"
    TEMPLATE = "template"
    DOCUMENT = "document"
    PLUGIN = "plugin"


@dataclass
class Hook:
    """Descriptor for a single lifecycle hook point.

    Attributes:
        name: Unique hook identifier (e.g. ``"before_parse"``).
        scope: The domain this hook belongs to.
        description: Human-readable explanation.
    """

    name: str
    scope: HookScope = HookScope.CONVERSION
    description: str = ""


@dataclass
class LifecycleHook:
    """A hook with before/after semantics and error handling.

    Wraps a :class:`Hook` and tracks whether it has been registered.
    """

    hook: Hook
    handlers: list[Any] = field(default_factory=list)


class HookRegistry:
    """Registry mapping hook names to their handlers.

    Usage::

        registry = HookRegistry()

        def my_handler(event, context):
            return event

        registry.register("before_parse", my_handler)
        result = registry.dispatch("before_parse", event, context={})
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[Any]] = {}

    def register(self, hook_name: str, handler: Any) -> None:
        """Register a handler for *hook_name*."""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(handler)

    def unregister(self, hook_name: str, handler: Any) -> None:
        """Remove a specific handler from *hook_name*."""
        handlers = self._hooks.get(hook_name, [])
        if handler in handlers:
            handlers.remove(handler)

    def dispatch(self, hook_name: str, *args: Any, **kwargs: Any) -> Any:
        """Call all handlers for *hook_name* in registration order.

        Each handler receives ``(value, context)`` and returns the
        (possibly transformed) value, which is passed to the next handler.

        Returns the final value after all handlers have run.
        """
        result = args[0] if args else None
        for handler in self._hooks.get(hook_name, []):
            try:
                if result is not None:
                    result = handler(result, kwargs.get("context", {}))
                else:
                    handler(*(args[1:]), **kwargs)
            except Exception as exc:
                raise RuntimeError(
                    f"Handler '{getattr(handler, '__name__', handler)}' "
                    f"failed at hook '{hook_name}': {exc}"
                ) from exc
        return result

    def list_hooks(self) -> list[str]:
        """Return all registered hook names."""
        return list(self._hooks.keys())

    def clear(self) -> None:
        """Remove all handlers."""
        self._hooks.clear()

    @property
    def hook_count(self) -> int:
        return len(self._hooks)


__all__ = [
    "Hook",
    "HookRegistry",
    "HookScope",
    "LifecycleHook",
]
