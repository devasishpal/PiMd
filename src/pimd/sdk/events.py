"""Event types and event bus for the PiMD Extension SDK.

Plugins can emit and listen for events to coordinate behaviour
without tight coupling.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

EventHandler = Callable[..., None]


class EventPriority(int, Enum):
    """Priority levels for event handlers."""

    HIGHEST = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    LOWEST = 0


@dataclass
class Event:
    """Base event payload.

    Attributes:
        name: Event identifier (e.g. ``"conversion.started"``).
        data: Arbitrary payload attached to the event.
        source: Name of the plugin or component that emitted the event.
        cancelled: If ``True``, the event has been cancelled by a handler.
    """

    name: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    cancelled: bool = False

    def cancel(self) -> None:
        """Prevent further processing of this event."""
        self.cancelled = True


class EventBus:
    """Simple in-process event bus for plugin communication.

    Usage::

        bus = EventBus()

        def on_convert(event: Event) -> None:
            print(f"Conversion: {event.data}")

        bus.on("conversion.started", on_convert)
        bus.emit(Event("conversion.started", {"file": "doc.md"}))
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[tuple[EventHandler, EventPriority]]] = {}

    def on(
        self,
        event_name: str,
        handler: EventHandler,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> None:
        """Register *handler* for *event_name* with an optional *priority*."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append((handler, priority))
        self._listeners[event_name].sort(key=lambda x: x[1].value, reverse=True)

    def off(self, event_name: str, handler: EventHandler) -> None:
        """Remove *handler* from *event_name*."""
        listeners = self._listeners.get(event_name, [])
        self._listeners[event_name] = [
            (h, p) for h, p in listeners if h != handler
        ]

    def emit(self, event: Event) -> None:
        """Emit *event* to all registered handlers in priority order.

        If any handler cancels the event, remaining handlers are skipped.
        """
        for handler, _priority in self._listeners.get(event.name, []):
            if event.cancelled:
                break
            try:
                handler(event)
            except Exception as exc:
                raise RuntimeError(
                    f"Event handler '{getattr(handler, '__name__', handler)}' "
                    f"failed for event '{event.name}': {exc}"
                ) from exc

    def clear(self) -> None:
        """Remove all listeners."""
        self._listeners.clear()

    @property
    def listener_count(self) -> int:
        return sum(len(v) for v in self._listeners.values())


__all__ = [
    "Event",
    "EventBus",
    "EventHandler",
    "EventPriority",
]
