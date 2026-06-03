"""Plugin manager — registration, dispatch, lifecycle, discovery."""

from __future__ import annotations

import importlib
import importlib.metadata
import inspect
import sys
from pathlib import Path
from typing import Any

from pimd.plugins.base import ConversionHook, Plugin, PluginMetadata


def _parse_version(ver: str) -> tuple[int, ...]:
    return tuple(int(p) for p in ver.split(".") if p.isdigit())


def _get_pimd_version() -> str:
    """Return the installed PiMD version string."""
    try:
        return importlib.metadata.version("pimd")
    except Exception:
        pass
    try:
        from pimd import __version__ as _ver  # noqa: PLC0415
        return _ver
    except Exception:
        return "0.0.0"


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
        self._discovered_paths: list[str] = []

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
            plugin.on_enable()

    def disable(self, plugin_name: str) -> None:
        """Disable a registered plugin."""
        plugin = self._plugins.get(plugin_name)
        if plugin:
            plugin.enabled = False
            plugin.on_disable()

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

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_plugin_metadata(self, plugin_name: str) -> PluginMetadata | None:
        """Return metadata for a registered plugin, or ``None``."""
        plugin = self._plugins.get(plugin_name)
        if plugin is None:
            return None
        return plugin.metadata

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    @staticmethod
    def discover_entry_points() -> list[Plugin]:
        """Discover plugins registered via the ``pimd.plugins`` entry point group.

        Uses ``importlib.metadata.entry_points`` to find installed packages
        that advertise PiMD plugins.
        """
        plugins: list[Plugin] = []
        try:
            eps = importlib.metadata.entry_points(group="pimd.plugins")
            for ep in eps:
                try:
                    cls = ep.load()
                    if inspect.isclass(cls) and issubclass(cls, Plugin) and not inspect.isabstract(cls):
                        instance = cls()
                        plugins.append(instance)
                except Exception:
                    continue
        except Exception:
            pass
        return plugins

    @staticmethod
    def discover_filesystem(path: str | Path) -> list[Plugin]:
        """Discover plugins from a filesystem directory.

        Scans *path* for ``.py`` files and packages, imports them,
        and instantiates any concrete ``Plugin`` subclasses found.
        """
        plugins: list[Plugin] = []
        scan_path = Path(path)
        if not scan_path.is_dir():
            return plugins

        original_path = list(sys.path)
        sys.path.insert(0, str(scan_path.resolve()))

        try:
            for entry in sorted(scan_path.iterdir()):
                plugin_cls = None
                if entry.suffix == ".py" and entry.stem != "__init__":
                    module_name = entry.stem
                    try:
                        spec = importlib.util.spec_from_file_location(module_name, str(entry))
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                            plugin_cls = _find_plugin_class(mod)
                    except Exception:
                        continue
                elif entry.is_dir() and (entry / "__init__.py").exists():
                    module_name = entry.name
                    try:
                        mod = importlib.import_module(module_name)
                        plugin_cls = _find_plugin_class(mod)
                    except Exception:
                        continue

                if plugin_cls is not None:
                    try:
                        instance = plugin_cls()
                        plugins.append(instance)
                    except Exception:
                        continue
        finally:
            sys.path = original_path

        return plugins

    # ------------------------------------------------------------------
    # Install / Uninstall
    # ------------------------------------------------------------------

    def install_plugin(self, plugin_path: str | Path) -> Plugin | None:
        """Install a plugin from a file or directory path.

        Copies the plugin into PiMD's user plugin directory
        and returns the loaded plugin instance, or ``None`` on failure.
        """
        src = Path(plugin_path).resolve()
        if not src.exists():
            return None

        plugin_dir = self._get_user_plugin_dir()
        plugin_dir.mkdir(parents=True, exist_ok=True)

        if src.is_file() and src.suffix == ".py":
            dst = plugin_dir / src.name
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        elif src.is_dir():
            dst = plugin_dir / src.name
            if not dst.exists():
                _copy_directory(src, dst)
        else:
            return None

        discovered = self.discover_filesystem(plugin_dir)
        for plugin in discovered:
            if plugin.name in self._plugins:
                continue
            plugin.on_install()
            plugin.attach(self)
            return plugin
        return None

    def uninstall_plugin(self, plugin_name: str) -> bool:
        """Uninstall a plugin by name. Returns ``True`` on success."""
        plugin = self._plugins.get(plugin_name)
        if plugin is not None:
            plugin.on_uninstall()
            self.unregister(plugin_name)

        plugin_dir = self._get_user_plugin_dir()
        for entry in plugin_dir.iterdir():
            stem = entry.stem
            if stem == plugin_name or stem == plugin_name.replace(".", "_"):
                if entry.is_dir():
                    _remove_directory(entry)
                else:
                    entry.unlink()
                return True
        return plugin is not None

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def doctor(self) -> list[dict[str, Any]]:
        """Run diagnostics on all registered plugins.

        Returns a list of dicts, one per plugin, with fields:
        ``name``, ``version``, ``enabled``, ``has_attach``, ``metadata_valid``,
        ``missing_dependencies``, ``compatible``, ``issues``.
        """
        results: list[dict[str, Any]] = []
        for plugin in self._plugins.values():
            missing_deps = plugin.check_dependencies()
            issues: list[str] = []

            if missing_deps:
                issues.append(f"Missing dependencies: {', '.join(missing_deps)}")

            md = plugin.metadata
            metadata_valid = bool(md.name) and bool(md.version)
            if not metadata_valid:
                issues.append("Invalid metadata (name or version missing)")

            compat = self._check_compatibility(plugin)
            if not compat["compatible"]:
                issues.append(compat["reason"])

            try:
                has_attach = callable(getattr(plugin, "attach", None))
            except Exception:
                has_attach = False

            results.append({
                "name": plugin.name,
                "version": plugin.version,
                "enabled": plugin.enabled,
                "has_attach": has_attach,
                "metadata_valid": metadata_valid,
                "missing_dependencies": missing_deps,
                "compatible": compat["compatible"],
                "compatibility_reason": compat.get("reason", ""),
                "issues": issues,
            })
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_user_plugin_dir() -> Path:
        """Return the user-level plugin directory."""
        home = Path.home()
        return home / ".pimd" / "plugins"

    @staticmethod
    def _check_compatibility(plugin: Plugin) -> dict[str, Any]:
        """Check PiMD version compatibility for a plugin.

        Returns a dict with ``compatible`` (bool) and optionally ``reason``.
        """
        result: dict[str, Any] = {"compatible": True}
        pimd_ver = _parse_version(_get_pimd_version())

        deps = plugin.metadata.dependencies
        for dep in deps:
            if dep.startswith("pimd>=") or dep.startswith("pimd=="):
                req_ver = dep.split("=", 2)[-1]
                req_parts = _parse_version(req_ver)
                if pimd_ver < req_parts:
                    result["compatible"] = False
                    result["reason"] = (
                        f"PiMD {_get_pimd_version()} < required {req_ver}"
                    )
                    break

        return result


def _find_plugin_class(module: object) -> type[Plugin] | None:
    """Find the first concrete Plugin subclass in a module."""
    for _name, obj in inspect.getmembers(module):
        if (
            inspect.isclass(obj)
            and issubclass(obj, Plugin)
            and obj is not Plugin
            and not inspect.isabstract(obj)
        ):
            return obj
    return None


def _copy_directory(src: Path, dst: Path) -> None:
    """Recursively copy a directory."""
    import shutil
    shutil.copytree(src, dst)


def _remove_directory(path: Path) -> None:
    """Recursively remove a directory."""
    import shutil
    shutil.rmtree(path)


__all__ = [
    "PluginManager",
]
