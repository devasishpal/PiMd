"""Tests for pimd.registry — unified CapabilityRegistry."""

from __future__ import annotations

from pimd.registry import Capability, CapabilityRegistry, CapabilityType, get_registry, reset_registry


class TestCapabilityRegistry:
    def setup_method(self) -> None:
        reset_registry()

    def test_register_and_get(self) -> None:
        registry = CapabilityRegistry()
        cap = Capability("mermaid", CapabilityType.RENDERER, object(), version="1.0")
        registry.register(cap)
        retrieved = registry.get("mermaid", CapabilityType.RENDERER)
        assert retrieved is not None
        assert retrieved.name == "mermaid"
        assert retrieved.cap_type == CapabilityType.RENDERER

    def test_unregister(self) -> None:
        registry = CapabilityRegistry()
        cap = Capability("test", CapabilityType.PLUGIN, object())
        registry.register(cap)
        registry.unregister("test", CapabilityType.PLUGIN)
        assert registry.get("test", CapabilityType.PLUGIN) is None

    def test_get_by_type(self) -> None:
        registry = CapabilityRegistry()
        registry.register(Capability("a", CapabilityType.RENDERER, "r1"))
        registry.register(Capability("b", CapabilityType.RENDERER, "r2"))
        registry.register(Capability("c", CapabilityType.EXPORTER, "e1"))
        renderers = registry.get_by_type(CapabilityType.RENDERER)
        assert len(renderers) == 2
        exporters = registry.get_by_type(CapabilityType.EXPORTER)
        assert len(exporters) == 1

    def test_list_all(self) -> None:
        registry = CapabilityRegistry()
        registry.register(Capability("x", CapabilityType.THEME, object()))
        registry.register(Capability("y", CapabilityType.TEMPLATE, object()))
        assert len(registry.list_all()) == 2

    def test_find(self) -> None:
        registry = CapabilityRegistry()
        registry.register(Capability("mermaid", CapabilityType.RENDERER, object()))
        registry.register(Capability("plantuml", CapabilityType.RENDERER, object()))
        matches = registry.find("mermaid")
        assert len(matches) == 1
        assert matches[0].name == "mermaid"

    def test_resolve_all_present(self) -> None:
        registry = CapabilityRegistry()
        registry.register(Capability("pidraw", CapabilityType.RENDERER, object()))
        result = registry.resolve(["renderer:pidraw>=2.0"])
        assert len(result["resolved"]) == 1
        assert result["missing"] == []

    def test_resolve_missing(self) -> None:
        registry = CapabilityRegistry()
        result = registry.resolve(["nonexistent"])
        assert result["missing"] == ["nonexistent"]

    def test_health(self) -> None:
        registry = CapabilityRegistry()
        registry.register(Capability("a", CapabilityType.RENDERER, object()))
        registry.register(Capability("b", CapabilityType.EXPORTER, object()))
        h = registry.health()
        assert h["total_capabilities"] == 2

    def test_clear(self) -> None:
        registry = CapabilityRegistry()
        registry.register(Capability("x", CapabilityType.RENDERER, object()))
        registry.clear()
        assert registry.count == 0

    def test_global_registry(self) -> None:
        reset_registry()
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_reset_registry(self) -> None:
        reset_registry()
        r1 = get_registry()
        reset_registry()
        r2 = get_registry()
        assert r1 is not r2

    def test_capability_matches(self) -> None:
        cap = Capability("TestRenderer", CapabilityType.RENDERER, object())
        assert cap.matches("test")
        assert cap.matches("renderer")
        assert not cap.matches("exporter")
