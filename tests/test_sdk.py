"""Tests for the PiMD Extension SDK."""

from __future__ import annotations

from typing import Any

import pytest

from pimd.sdk.base import (
    AssetPlugin,
    BasePlugin,
    CitationPlugin,
    DiagramPlugin,
    ExporterPlugin,
    ParserPlugin,
    PluginMetadata,
    PublishingPlugin,
    RendererPlugin,
    TemplatePlugin,
    ValidationPlugin,
)
from pimd.sdk.events import Event, EventBus, EventPriority
from pimd.sdk.hooks import Hook, HookRegistry, HookScope, LifecycleHook


class TestBasePlugin:
    def test_instantiation_with_concrete_subclass(self) -> None:
        class MyPlugin(BasePlugin):
            metadata = PluginMetadata(name="my-plugin", version="1.0.0")
            def attach(self, manager: Any) -> None:
                pass

        plugin = MyPlugin()
        assert isinstance(plugin, BasePlugin)
        assert plugin.metadata.name == "my-plugin"
        assert plugin.metadata.version == "1.0.0"

    def test_metadata_attribute(self) -> None:
        md = PluginMetadata(name="custom-name", version="2.0.0", description="A custom plugin")

        class CustomPlugin(BasePlugin):
            metadata = md
            def attach(self, manager: Any) -> None:
                pass

        plugin = CustomPlugin()
        assert plugin.metadata.name == "custom-name"
        assert plugin.metadata.version == "2.0.0"
        assert plugin.metadata.description == "A custom plugin"

    def test_metadata_auto_populated(self) -> None:
        class NamedPlugin(BasePlugin):
            def attach(self, manager: Any) -> None:
                pass

        plugin = NamedPlugin()
        assert plugin.metadata.name
        assert plugin.metadata.version == "0.1.0"


class TestDiagramPlugin:
    def make(self) -> DiagramPlugin:
        class TestDiagramPlugin(DiagramPlugin):
            def attach(self, manager: Any) -> None:
                pass
        return TestDiagramPlugin()

    def test_instantiation(self) -> None:
        plugin = self.make()
        assert plugin.metadata.plugin_type == "diagram"

    def test_before_render_default(self) -> None:
        from pimd.sdk.base import DiagramPluginEvent
        event = DiagramPluginEvent(hook=None, context=None)  # type: ignore[arg-type]
        result = self.make().before_render(event)
        assert result is event

    def test_after_render_default(self) -> None:
        from pimd.sdk.base import DiagramPluginEvent
        event = DiagramPluginEvent(hook=None, context=None)  # type: ignore[arg-type]
        result = self.make().after_render(event)
        assert result is event

    def test_before_cache_default(self) -> None:
        from pimd.sdk.base import DiagramPluginEvent
        event = DiagramPluginEvent(hook=None, context=None)  # type: ignore[arg-type]
        result = self.make().before_cache(event)
        assert result is event

    def test_after_cache_default(self) -> None:
        from pimd.sdk.base import DiagramPluginEvent
        event = DiagramPluginEvent(hook=None, context=None)  # type: ignore[arg-type]
        result = self.make().after_cache(event)
        assert result is event

    def test_before_embed_default(self) -> None:
        from pimd.sdk.base import DiagramPluginEvent
        event = DiagramPluginEvent(hook=None, context=None)  # type: ignore[arg-type]
        result = self.make().before_embed(event)
        assert result is event

    def test_after_embed_default(self) -> None:
        from pimd.sdk.base import DiagramPluginEvent
        event = DiagramPluginEvent(hook=None, context=None)  # type: ignore[arg-type]
        result = self.make().after_embed(event)
        assert result is event

    def test_on_error_default(self) -> None:
        from pimd.sdk.base import DiagramPluginEvent
        event = DiagramPluginEvent(hook=None, context=None)  # type: ignore[arg-type]
        result = self.make().on_error(event)
        assert result is event

    def test_on_fallback_default(self) -> None:
        from pimd.sdk.base import DiagramPluginEvent
        event = DiagramPluginEvent(hook=None, context=None)  # type: ignore[arg-type]
        result = self.make().on_fallback(event)
        assert result is event

    def test_subclass_overrides(self) -> None:
        class MyDiagram(DiagramPlugin):
            def attach(self, manager: Any) -> None:
                pass
            def before_render(self, event: Any) -> Any:
                return "overridden"

        plugin = MyDiagram()
        assert plugin.metadata.plugin_type == "diagram"
        result = plugin.before_render(None)
        assert result == "overridden"


class TestTemplatePlugin:
    def make(self) -> TemplatePlugin:
        class TestTemplatePlugin(TemplatePlugin):
            def attach(self, manager: Any) -> None:
                pass
        return TestTemplatePlugin()

    def test_instantiation(self) -> None:
        assert self.make().metadata.plugin_type == "template"

    def test_on_template_load(self) -> None:
        result = self.make().on_template_load("report", {"key": "val"})
        assert result == {"key": "val"}

    def test_on_template_render(self) -> None:
        result = self.make().on_template_render("<html>", "report")
        assert result == "<html>"


class TestCitationPlugin:
    def make(self) -> CitationPlugin:
        class TestCitationPlugin(CitationPlugin):
            def attach(self, manager: Any) -> None:
                pass
        return TestCitationPlugin()

    def test_instantiation(self) -> None:
        assert self.make().metadata.plugin_type == "citation"

    def test_on_citation_load(self) -> None:
        citations = [{"id": "ref1", "title": "Paper"}]
        result = self.make().on_citation_load(citations)
        assert result == citations

    def test_on_citation_render(self) -> None:
        result = self.make().on_citation_render("[1] Ref", "ieee")
        assert result == "[1] Ref"


class TestRendererPlugin:
    def make(self) -> RendererPlugin:
        class TestRendererPlugin(RendererPlugin):
            def attach(self, manager: Any) -> None:
                pass
        return TestRendererPlugin()

    def test_instantiation(self) -> None:
        assert self.make().metadata.plugin_type == "renderer"

    def test_before_document_render(self) -> None:
        result = self.make().before_document_render("doc", {})
        assert result == "doc"

    def test_after_document_render(self) -> None:
        result = self.make().after_document_render("output", {})
        assert result == "output"


class TestExporterPlugin:
    def make(self) -> ExporterPlugin:
        class TestExporterPlugin(ExporterPlugin):
            def attach(self, manager: Any) -> None:
                pass
        return TestExporterPlugin()

    def test_instantiation(self) -> None:
        assert self.make().metadata.plugin_type == "exporter"

    def test_before_export(self) -> None:
        result = self.make().before_export("doc", "pdf")
        assert result == "doc"

    def test_after_export(self) -> None:
        result = self.make().after_export("result", "pdf")
        assert result == "result"


class TestAssetPlugin:
    def make(self) -> AssetPlugin:
        class TestAssetPlugin(AssetPlugin):
            def attach(self, manager: Any) -> None:
                pass
        return TestAssetPlugin()

    def test_instantiation(self) -> None:
        assert self.make().metadata.plugin_type == "asset"

    def test_on_asset_resolve(self) -> None:
        result = self.make().on_asset_resolve("/path/to/image.png")
        assert result == "/path/to/image.png"

    def test_on_asset_process(self) -> None:
        result = self.make().on_asset_process(b"raw data", "image")
        assert result == b"raw data"


class TestValidationPlugin:
    def make(self) -> ValidationPlugin:
        class TestValidationPlugin(ValidationPlugin):
            def attach(self, manager: Any) -> None:
                pass
        return TestValidationPlugin()

    def test_instantiation(self) -> None:
        assert self.make().metadata.plugin_type == "validation"

    def test_on_validate_defaults(self) -> None:
        result = self.make().on_validate("doc")
        assert result == []

    def test_subclass_returns_issues(self) -> None:
        class StrictValidator(ValidationPlugin):
            def attach(self, manager: Any) -> None:
                pass
            def on_validate(self, document: Any) -> list[dict[str, Any]]:
                return [{"severity": "error", "message": "Too long"}]

        plugin = StrictValidator()
        issues = plugin.on_validate("doc")
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"


class TestParserPlugin:
    def make(self) -> ParserPlugin:
        class TestParserPlugin(ParserPlugin):
            def attach(self, manager: Any) -> None:
                pass
        return TestParserPlugin()

    def test_instantiation(self) -> None:
        assert self.make().metadata.plugin_type == "parser"

    def test_on_parse_start(self) -> None:
        result = self.make().on_parse_start("# Hello", "markdown")
        assert result == "# Hello"

    def test_on_parse_end(self) -> None:
        result = self.make().on_parse_end({"type": "doc"}, "markdown")
        assert result == {"type": "doc"}


class TestPublishingPlugin:
    def make(self) -> PublishingPlugin:
        class TestPublishingPlugin(PublishingPlugin):
            def attach(self, manager: Any) -> None:
                pass
        return TestPublishingPlugin()

    def test_instantiation(self) -> None:
        assert self.make().metadata.plugin_type == "publishing"

    def test_before_publish(self) -> None:
        result = self.make().before_publish("doc", "wordpress")
        assert result == "doc"

    def test_after_publish(self) -> None:
        result = self.make().after_publish("success", "wordpress")
        assert result == "success"


class TestPluginTypesCount:
    def test_nine_plugin_types_have_correct_types(self) -> None:
        types: list[tuple[type[BasePlugin], str]] = [
            (DiagramPlugin, "diagram"),
            (TemplatePlugin, "template"),
            (CitationPlugin, "citation"),
            (RendererPlugin, "renderer"),
            (ExporterPlugin, "exporter"),
            (AssetPlugin, "asset"),
            (ValidationPlugin, "validation"),
            (ParserPlugin, "parser"),
            (PublishingPlugin, "publishing"),
        ]
        assert len(types) == 9

    def test_each_plugin_type_sets_metadata_type(self) -> None:
        for cls, expected_type in [
            (DiagramPlugin, "diagram"),
            (TemplatePlugin, "template"),
            (CitationPlugin, "citation"),
            (RendererPlugin, "renderer"),
            (ExporterPlugin, "exporter"),
            (AssetPlugin, "asset"),
            (ValidationPlugin, "validation"),
            (ParserPlugin, "parser"),
            (PublishingPlugin, "publishing"),
        ]:
            subclass = type("Test" + cls.__name__, (cls,), {"attach": lambda self, m: None})
            instance = subclass()
            assert instance.metadata.plugin_type == expected_type, f"{cls.__name__}"


class TestHook:
    def test_create_hook(self) -> None:
        hook = Hook(name="before_parse", scope=HookScope.CONVERSION, description="Before parsing")
        assert hook.name == "before_parse"
        assert hook.scope == HookScope.CONVERSION
        assert hook.description == "Before parsing"

    def test_hook_default_scope(self) -> None:
        hook = Hook(name="custom")
        assert hook.scope == HookScope.CONVERSION
        assert hook.description == ""


class TestLifecycleHook:
    def test_create_lifecycle_hook(self) -> None:
        hook = Hook(name="before_render")
        lifecycle = LifecycleHook(hook=hook)
        assert lifecycle.hook is hook
        assert lifecycle.handlers == []

    def test_with_handlers(self) -> None:
        hook = Hook(name="after_render")
        handlers = [lambda x: x]
        lifecycle = LifecycleHook(hook=hook, handlers=handlers)
        assert len(lifecycle.handlers) == 1


class TestHookRegistry:
    def test_register_and_dispatch(self) -> None:
        registry = HookRegistry()

        def upper_hook(value: str, context: dict[str, Any]) -> str:
            return value.upper()

        registry.register("format", upper_hook)
        result = registry.dispatch("format", "hello", context={})
        assert result == "HELLO"

    def test_dispatch_multiple_handlers(self) -> None:
        registry = HookRegistry()

        def add_exclaim(value: str, context: dict[str, Any]) -> str:
            return value + "!"

        def add_question(value: str, context: dict[str, Any]) -> str:
            return value + "?"

        registry.register("chain", add_exclaim)
        registry.register("chain", add_question)
        result = registry.dispatch("chain", "hi", context={})
        assert result == "hi!?"

    def test_dispatch_unknown_hook_returns_none(self) -> None:
        registry = HookRegistry()
        result = registry.dispatch("nonexistent", "val", context={})
        assert result == "val"

    def test_unregister_removes_handler(self) -> None:
        registry = HookRegistry()

        def handler(value: str, context: dict[str, Any]) -> str:
            return value.upper()

        registry.register("h", handler)
        assert len(registry._hooks["h"]) == 1
        registry.unregister("h", handler)
        assert registry._hooks["h"] == []

    def test_list_hooks(self) -> None:
        registry = HookRegistry()
        registry.register("a", lambda v, ctx: v)
        registry.register("b", lambda v, ctx: v)
        hooks = registry.list_hooks()
        assert "a" in hooks
        assert "b" in hooks

    def test_clear(self) -> None:
        registry = HookRegistry()
        registry.register("x", lambda v, ctx: v)
        registry.clear()
        assert registry.hook_count == 0

    def test_hook_count(self) -> None:
        registry = HookRegistry()
        assert registry.hook_count == 0
        registry.register("a", lambda v, ctx: v)
        assert registry.hook_count == 1

    def test_handler_error_wraps(self) -> None:
        registry = HookRegistry()

        def broken(value: str, context: dict[str, Any]) -> str:
            msg = "broken"
            raise ValueError(msg)

        registry.register("b", broken)
        with pytest.raises(RuntimeError, match="broken"):
            registry.dispatch("b", "val", context={})


class TestEvent:
    def test_create_event(self) -> None:
        event = Event(name="conversion.started", data={"file": "test.md"}, source="test")
        assert event.name == "conversion.started"
        assert event.data == {"file": "test.md"}
        assert event.source == "test"
        assert event.cancelled is False

    def test_cancel(self) -> None:
        event = Event(name="test.event")
        event.cancel()
        assert event.cancelled is True


class TestEventBus:
    def test_on_and_emit(self) -> None:
        bus = EventBus()
        captured: list[Event] = []

        def handler(event: Event) -> None:
            captured.append(event)

        bus.on("test.event", handler)
        event = Event(name="test.event", data={"key": 42})
        bus.emit(event)
        assert len(captured) == 1
        assert captured[0].data["key"] == 42

    def test_multiple_handlers(self) -> None:
        bus = EventBus()
        results: list[str] = []

        def handler1(event: Event) -> None:
            results.append("h1")

        def handler2(event: Event) -> None:
            results.append("h2")

        bus.on("evt", handler1)
        bus.on("evt", handler2)
        bus.emit(Event(name="evt"))
        assert results == ["h1", "h2"]

    def test_cancelled_event_stops_propagation(self) -> None:
        bus = EventBus()
        results: list[str] = []

        def canceller(event: Event) -> None:
            results.append("cancel")
            event.cancel()

        def after(event: Event) -> None:
            results.append("after")

        bus.on("test", canceller, EventPriority.HIGH)
        bus.on("test", after, EventPriority.NORMAL)
        bus.emit(Event(name="test"))
        assert results == ["cancel"]

    def test_priority_order(self) -> None:
        bus = EventBus()
        results: list[str] = []

        def low(event: Event) -> None:
            results.append("low")

        def high(event: Event) -> None:
            results.append("high")

        bus.on("prio", low, EventPriority.LOW)
        bus.on("prio", high, EventPriority.HIGH)
        bus.emit(Event(name="prio"))
        assert results == ["high", "low"]

    def test_off_removes_handler(self) -> None:
        bus = EventBus()

        def handler(event: Event) -> None:
            pass

        bus.on("evt", handler)
        assert bus.listener_count == 1
        bus.off("evt", handler)
        assert bus.listener_count == 0

    def test_listener_count(self) -> None:
        bus = EventBus()
        assert bus.listener_count == 0
        bus.on("a", lambda e: None)
        bus.on("b", lambda e: None)
        assert bus.listener_count == 2

    def test_clear_removes_all(self) -> None:
        bus = EventBus()
        bus.on("a", lambda e: None)
        bus.on("b", lambda e: None)
        bus.clear()
        assert bus.listener_count == 0

    def test_handler_exception_wraps(self) -> None:
        bus = EventBus()

        def broken(event: Event) -> None:
            msg = "handler crash"
            raise ValueError(msg)

        bus.on("crash", broken)
        with pytest.raises(RuntimeError, match="handler crash"):
            bus.emit(Event(name="crash"))

    def test_emit_no_listeners_does_nothing(self) -> None:
        bus = EventBus()
        bus.emit(Event(name="orphan"))
