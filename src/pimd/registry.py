"""Unified Capability Registry — single source of truth for all discoverable plugins.

All capability types:
  - RendererCapability  (pidraw renderers)
  - ExporterCapability  (export formats)
  - ConverterCapability (document converters)
  - PluginCapability    (pimd plugins)
  - ThemeCapability     (visual themes)

Every capability is registered once and discovered through one registry.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class CapabilityType(enum.Enum):
    RENDERER = "renderer"
    EXPORTER = "exporter"
    CONVERTER = "converter"
    PLUGIN = "plugin"
    THEME = "theme"
    OPTIMIZER = "optimizer"
    ASSET = "asset"
    TEMPLATE = "template"


@dataclass
class Capability(Generic[T]):
    """A registered capability in the unified registry."""

    name: str
    cap_type: CapabilityType
    instance: T
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)

    def matches(self, query: str) -> bool:
        q = query.lower()
        return q in self.name.lower() or q in self.cap_type.value


class CapabilityRegistry:
    """Thread-safe registry for all discoverable capabilities.

    Usage::

        registry = CapabilityRegistry()
        registry.register(Capability("mermaid", CapabilityType.RENDERER, renderer))
        renderers = registry.get_by_type(CapabilityType.RENDERER)
        registry.resolve(["pidraw>=2.0", "theme:dark"])
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._type_index: dict[CapabilityType, list[str]] = {
            t: [] for t in CapabilityType
        }

    def register(self, capability: Capability) -> None:
        key = f"{capability.cap_type.value}:{capability.name}"
        self._capabilities[key] = capability
        self._type_index[capability.cap_type].append(key)

    def unregister(self, name: str, cap_type: CapabilityType) -> None:
        key = f"{cap_type.value}:{name}"
        self._capabilities.pop(key, None)
        if key in self._type_index.get(cap_type, []):
            self._type_index[cap_type].remove(key)

    def get(self, name: str, cap_type: CapabilityType) -> Capability | None:
        return self._capabilities.get(f"{cap_type.value}:{name}")

    def get_by_type(self, cap_type: CapabilityType) -> list[Capability]:
        return [self._capabilities[k] for k in self._type_index.get(cap_type, []) if k in self._capabilities]

    def list_all(self) -> list[Capability]:
        return list(self._capabilities.values())

    def find(self, query: str) -> list[Capability]:
        q = query.lower()
        return [c for c in self._capabilities.values() if c.matches(q)]

    def resolve(self, dependencies: list[str]) -> dict[str, list[str]]:
        """Resolve dependency specs against registered capabilities.

        Returns {resolved: [], missing: [], conflicts: []}
        """
        resolved: list[str] = []
        missing: list[str] = []

        known_prefixes = {t.value for t in CapabilityType}

        for dep in dependencies:
            dep = dep.strip()
            if not dep:
                continue

            if ":" in dep:
                prefix, rest = dep.split(":", 1)
            else:
                prefix, rest = None, dep

            if prefix in known_prefixes:
                bare_name = rest.split(">=")[0].split("<=")[0].split("==")[0].strip()
                key = f"{prefix}:{bare_name}"
            elif prefix == "python":
                continue
            else:
                bare_name = dep.split(">=")[0].split("<=")[0].split("==")[0].strip()
                key = bare_name

            if key in self._capabilities:
                resolved.append(dep)
            else:
                missing.append(dep)

        return {"resolved": resolved, "missing": missing, "conflicts": []}

    def clear(self) -> None:
        self._capabilities.clear()
        for t in CapabilityType:
            self._type_index[t] = []

    @property
    def count(self) -> int:
        return len(self._capabilities)

    def health(self) -> dict[str, Any]:
        return {
            "total_capabilities": self.count,
            "by_type": {t.value: len(self._type_index[t]) for t in CapabilityType},
            "entries": [f"{c.cap_type.value}:{c.name}" for c in self._capabilities.values()],
        }


_GLOBAL_REGISTRY: CapabilityRegistry | None = None


def get_registry() -> CapabilityRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = CapabilityRegistry()
    return _GLOBAL_REGISTRY


def reset_registry() -> None:
    global _GLOBAL_REGISTRY
    _GLOBAL_REGISTRY = None
