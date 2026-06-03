"""Tests for the PiMD plugin system."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pimd.plugins.base import PLUGIN_TYPES, ConversionHook, Plugin, PluginMetadata
from pimd.plugins.manager import PluginManager


class TestPluginMetadata:
    def test_create_with_defaults(self) -> None:
        md = PluginMetadata(name="test")
        assert md.name == "test"
        assert md.version == "0.1.0"
        assert md.description == ""
        assert md.author == ""
        assert md.plugin_type == ""
        assert md.dependencies == []
        assert md.tags == []
        assert md.homepage == ""
        assert md.license == ""

    def test_create_with_all_fields(self) -> None:
        md = PluginMetadata(
            name="my-plugin",
            version="2.0.0",
            description="Does stuff",
            author="Me",
            plugin_type="diagram",
            dependencies=["rich", "click"],
            tags=["diagram", "svg"],
            homepage="https://example.com",
            license="MIT",
        )
        assert md.name == "my-plugin"
        assert md.version == "2.0.0"
        assert md.author == "Me"
        assert md.plugin_type == "diagram"


class TestConversionHook:
    def test_enum_values(self) -> None:
        assert ConversionHook.BEFORE_PARSE.value == "before_parse"
        assert ConversionHook.AFTER_PARSE.value == "after_parse"
        assert ConversionHook.BEFORE_RENDER.value == "before_render"
        assert ConversionHook.AFTER_RENDER.value == "after_render"
        assert ConversionHook.BEFORE_CONVERT.value == "before_convert"
        assert ConversionHook.AFTER_CONVERT.value == "after_convert"

    def test_all_hooks_present(self) -> None:
        values = {h.value for h in ConversionHook}
        expected = {
            "before_parse",
            "after_parse",
            "before_render",
            "after_render",
            "before_convert",
            "after_convert",
        }
        assert values == expected


class TestPluginTypes:
    def test_plugin_types_list(self) -> None:
        expected = [
            "diagram",
            "template",
            "citation",
            "renderer",
            "exporter",
            "asset",
            "validation",
            "parser",
            "publishing",
        ]
        assert PLUGIN_TYPES == expected


class TestPluginBase:
    def test_instantiate_concrete_plugin(self) -> None:
        class MyPlugin(Plugin):
            name = "my_plugin"
            version = "1.0.0"

            def attach(self, manager: Any) -> None:
                pass

        instance = MyPlugin()
        assert instance.name == "my_plugin"
        assert instance.version == "1.0.0"
        assert instance.enabled is True
        assert instance.description == ""
        assert isinstance(instance.metadata, PluginMetadata)
        assert instance.metadata.name == "my_plugin"
        assert instance.metadata.version == "1.0.0"

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        with pytest.raises(TypeError):
            Plugin()  # type: ignore[abstract]

    def test_hook_defaults(self) -> None:
        class TestPlugin(Plugin):
            name = "test"

            def attach(self, manager: Any) -> None:
                pass

        p = TestPlugin()
        assert p.before_parse("source", {}) == "source"
        assert p.after_parse("doc", {}) == "doc"
        assert p.before_render("doc", {}) == "doc"
        assert p.after_render("out", {}) == "out"
        assert p.before_convert({"key": "val"}) == {"key": "val"}
        assert p.after_convert({"key": "val"}) == {"key": "val"}

    def test_lifecycle_hooks_are_noop(self) -> None:
        class TestPlugin(Plugin):
            name = "test"

            def attach(self, manager: Any) -> None:
                pass

        p = TestPlugin()
        p.on_install()
        p.on_uninstall()
        p.on_enable()
        p.on_disable()

    def test_check_dependencies_all_present(self) -> None:
        class TestPlugin(Plugin):
            name = "test"

            def attach(self, manager: Any) -> None:
                pass

        p = TestPlugin()
        p.metadata.dependencies = ["os", "json"]
        assert p.check_dependencies() == []

    def test_check_dependencies_missing(self) -> None:
        class TestPlugin(Plugin):
            name = "test"

            def attach(self, manager: Any) -> None:
                pass

        p = TestPlugin()
        p.metadata.dependencies = ["nonexistent_package_xyz_123"]
        missing = p.check_dependencies()
        assert "nonexistent_package_xyz_123" in missing


class TestPluginManager:
    def test_register_and_list(self) -> None:
        manager = PluginManager()

        class TestPlugin(Plugin):
            name = "alpha"

            def attach(self, manager: Any) -> None:
                pass

        p = TestPlugin()
        manager.register(p, ConversionHook.AFTER_PARSE)
        plugins = manager.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "alpha"
        assert plugins[0]["enabled"] == "True"

    def test_register_disabled_plugin_does_nothing(self) -> None:
        manager = PluginManager()

        class TestPlugin(Plugin):
            name = "disabled-one"

            def attach(self, manager: Any) -> None:
                pass

        p = TestPlugin()
        p.enabled = False
        manager.register(p, ConversionHook.AFTER_PARSE)
        assert manager.plugin_count == 0

    def test_unregister_removes_plugin(self) -> None:
        manager = PluginManager()

        class TestPlugin(Plugin):
            name = "alpha"

            def attach(self, manager: Any) -> None:
                pass

        p = TestPlugin()
        manager.register(p, ConversionHook.AFTER_PARSE)
        assert manager.plugin_count == 1
        manager.unregister("alpha")
        assert manager.plugin_count == 0

    def test_unregister_unknown_plugin_does_not_raise(self) -> None:
        manager = PluginManager()
        manager.unregister("does-not-exist")

    def test_dispatch_returns_transformed_value(self) -> None:
        manager = PluginManager()

        class UpperPlugin(Plugin):
            name = "upper"

            def attach(self, manager: Any) -> None:
                pass

            def after_parse(self, document: str, context: dict[str, Any]) -> str:
                return document.upper()

        p = UpperPlugin()
        manager.register(p, ConversionHook.AFTER_PARSE)
        result = manager.dispatch(ConversionHook.AFTER_PARSE, "hello", context={})
        assert result == "HELLO"

    def test_dispatch_passes_context(self) -> None:
        manager = PluginManager()
        captured: dict[str, Any] = {}

        class CapturePlugin(Plugin):
            name = "capture"

            def attach(self, manager: Any) -> None:
                pass

            def before_parse(self, source: str, context: dict[str, Any]) -> str:
                captured.update(context)
                return source

        p = CapturePlugin()
        manager.register(p, ConversionHook.BEFORE_PARSE)
        manager.dispatch(ConversionHook.BEFORE_PARSE, "src", context={"key": 42})
        assert captured.get("key") == 42

    def test_dispatch_multiple_handlers_chain(self) -> None:
        manager = PluginManager()

        class AddExclaim(Plugin):
            name = "exclaim"

            def attach(self, manager: Any) -> None:
                pass

            def after_render(self, output: str, context: dict[str, Any]) -> str:
                return output + "!"

        class AddQuestion(Plugin):
            name = "question"

            def attach(self, manager: Any) -> None:
                pass

            def after_render(self, output: str, context: dict[str, Any]) -> str:
                return output + "?"

        manager.register(AddExclaim(), ConversionHook.AFTER_RENDER)
        manager.register(AddQuestion(), ConversionHook.AFTER_RENDER)
        result = manager.dispatch(ConversionHook.AFTER_RENDER, "hi", context={})
        assert result == "hi!?"

    def test_handler_exception_wraps_in_runtime_error(self) -> None:
        manager = PluginManager()

        class BrokenPlugin(Plugin):
            name = "broken"

            def attach(self, manager: Any) -> None:
                pass

            def after_parse(self, document: str, context: dict[str, Any]) -> str:
                msg = "something went wrong"
                raise ValueError(msg)

        p = BrokenPlugin()
        manager.register(p, ConversionHook.AFTER_PARSE)
        with pytest.raises(RuntimeError, match="broken"):
            manager.dispatch(ConversionHook.AFTER_PARSE, "doc", context={})

    def test_enable_disable(self) -> None:
        manager = PluginManager()
        events: list[str] = []

        class LifecyclePlugin(Plugin):
            name = "life"

            def attach(self, manager: Any) -> None:
                pass

            def on_enable(self) -> None:
                events.append("enabled")

            def on_disable(self) -> None:
                events.append("disabled")

        p = LifecyclePlugin()
        manager.register(p, ConversionHook.AFTER_PARSE)
        manager.disable("life")
        assert p.enabled is False
        assert "disabled" in events
        manager.enable("life")
        assert p.enabled is True
        assert "enabled" in events

    def test_plugin_count(self) -> None:
        manager = PluginManager()

        class P1(Plugin):
            name = "p1"
            def attach(self, manager: Any) -> None:
                pass

        class P2(Plugin):
            name = "p2"
            def attach(self, manager: Any) -> None:
                pass

        assert manager.plugin_count == 0
        manager.register(P1(), ConversionHook.BEFORE_PARSE)
        assert manager.plugin_count == 1
        manager.register(P2(), ConversionHook.AFTER_PARSE)
        assert manager.plugin_count == 2

    def test_get_plugin_metadata(self) -> None:
        manager = PluginManager()

        class TestPlugin(Plugin):
            name = "meta-test"
            version = "2.0.0"
            description = "desc"

            def attach(self, manager: Any) -> None:
                pass

        p = TestPlugin()
        manager.register(p, ConversionHook.BEFORE_PARSE)
        md = manager.get_plugin_metadata("meta-test")
        assert md is not None
        assert md.name == "meta-test"
        assert md.version == "2.0.0"

        missing = manager.get_plugin_metadata("does-not-exist")
        assert missing is None

    @patch("importlib.metadata.entry_points")
    def test_discover_entry_points(self, mock_entry_points: MagicMock) -> None:
        class DemoPlugin(Plugin):
            name = "demo"
            def attach(self, manager: Any) -> None:
                pass

        ep_mock = MagicMock()
        ep_mock.load.return_value = DemoPlugin
        mock_entry_points.return_value = [ep_mock]

        plugins = PluginManager.discover_entry_points()
        assert len(plugins) == 1
        assert plugins[0].name == "demo"

    @patch("importlib.metadata.entry_points")
    def test_discover_entry_points_errors_are_silent(self, mock_entry_points: MagicMock) -> None:
        mock_entry_points.side_effect = Exception("boom")
        plugins = PluginManager.discover_entry_points()
        assert plugins == []

    def test_doctor_returns_diagnostics(self) -> None:
        manager = PluginManager()

        class TestPlugin(Plugin):
            name = "healthy"

            def attach(self, manager: Any) -> None:
                pass

        manager.register(TestPlugin(), ConversionHook.AFTER_PARSE)
        results = manager.doctor()
        assert len(results) == 1
        diag = results[0]
        assert diag["name"] == "healthy"
        assert diag["enabled"] is True
        assert diag["has_attach"] is True
        assert diag["metadata_valid"] is True
        assert diag["missing_dependencies"] == []
        assert diag["compatible"] is True

    def test_install_plugin_from_nonexistent_path(self) -> None:
        manager = PluginManager()
        result = manager.install_plugin("/nonexistent/path.py")
        assert result is None

    def test_uninstall_unknown_plugin_returns_false(self, tmp_path: Any) -> None:
        manager = PluginManager()
        plugin_dir = tmp_path / ".pimd" / "plugins"
        plugin_dir.mkdir(parents=True)
        with patch.object(PluginManager, "_get_user_plugin_dir", return_value=plugin_dir):
            result = manager.uninstall_plugin("does-not-exist")
            assert result is False


class TestPluginManagerDiscoverFilesystem:
    def test_discover_filesystem_empty_dir(self, tmp_path: Any) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        plugins = PluginManager.discover_filesystem(empty)
        assert plugins == []

    def test_discover_filesystem_nonexistent_path(self) -> None:
        plugins = PluginManager.discover_filesystem("/nonexistent/path")
        assert plugins == []
