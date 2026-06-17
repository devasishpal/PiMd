"""Diagram engine — orchestration layer that delegates all rendering to PiDraw.

PiDraw is the authoritative diagram backend. This engine provides
a convenience wrapper with caching, concurrent rendering, and PiMD-specific
integration (plugins, error handling).

Never implements its own diagram rendering logic.
"""

from __future__ import annotations

import time
from typing import Any

from pimd.diagrams.models import DiagramConfig, DiagramContext, DiagramResult
from pimd.diagrams.pidraw_integration import (
    clear_cache as _clear_pidraw_cache,
)
from pimd.diagrams.pidraw_integration import (
    detect_language as _pidraw_detect,
)
from pimd.diagrams.pidraw_integration import (
    get_supported_languages,
    is_supported_language,
)
from pimd.diagrams.pidraw_integration import (
    render_diagram as _pidraw_render,
)
from pimd.diagrams.pidraw_integration import (
    render_many_diagrams as _pidraw_render_many,
)
from pimd.diagrams.registry import DiagramRegistry
from pimd.utils.logging import get_logger

try:
    from pimd.diagrams.plugin import DiagramHook, DiagramPluginEvent, DiagramPluginManager
except ImportError:
    DiagramPluginManager = None  # type: ignore
    DiagramHook = None  # type: ignore
    DiagramPluginEvent = None  # type: ignore

logger = get_logger(__name__)


class DiagramEngine:
    """Central diagram rendering engine.

    Orchestrates detection, rendering, caching, and fallback for all
    diagram types. All actual rendering is delegated to PiDraw.
    """

    def __init__(
        self,
        registry: DiagramRegistry | None = None,
        cache: Any = None,
        config: DiagramConfig | None = None,
        plugin_manager: DiagramPluginManager | None = None,
    ) -> None:
        self._registry = registry or DiagramRegistry()
        self._cache = cache
        self._config = config or DiagramConfig()
        self._plugin_manager = plugin_manager

    @property
    def plugin_manager(self) -> DiagramPluginManager | None:
        return self._plugin_manager

    @property
    def registry(self) -> DiagramRegistry:
        return self._registry

    @property
    def cache(self) -> Any:
        return self._cache

    @property
    def config(self) -> DiagramConfig:
        return self._config

    # ------------------------------------------------------------------
    # Auto-detection — delegates to PiDraw
    # ------------------------------------------------------------------

    def detect_language(self, source: str, hint: str | None = None) -> str | None:
        """Auto-detect the diagram language from source content.

        Delegates to PiDraw's 87-rule detector.

        Args:
            source: The diagram source code.
            hint: Optional language hint (e.g. from code block info string).

        Returns:
            Detected language string, or ``None`` if detection fails.
        """
        return _pidraw_detect(source, hint)

    @staticmethod
    def is_diagram_language(language: str) -> bool:
        """Check if *language* is a known diagram language (via PiDraw)."""
        return is_supported_language(language)

    @staticmethod
    def supported_languages() -> list[str]:
        """Return list of all supported diagram languages from PiDraw."""
        return list(get_supported_languages().keys())

    # ------------------------------------------------------------------
    # Single rendering — delegates to PiDraw
    # ------------------------------------------------------------------

    def render(
        self,
        source: str,
        language: str | None = None,
        **options: Any,
    ) -> DiagramResult:
        """Render a single diagram via PiDraw.

        If *language* is ``None``, auto-detection is attempted.

        Integrates with :class:`DiagramPluginManager` if configured.

        On failure, returns a ``DiagramResult`` with ``error`` set (never
        raises).
        """
        start = time.monotonic()

        # Auto-detect language if not provided
        if language is None:
            language = self.detect_language(source)
            if language is None:
                elapsed = time.monotonic() - start
                return DiagramResult(
                    source=source,
                    language="unknown",
                    error="Could not auto-detect diagram language. "
                    "Specify a language or install pidraw.",
                    render_time=elapsed,
                )

        # Build context for plugins
        context = DiagramContext(
            source=source,
            language=language,
            config=self._config,
            caption=options.get("caption"),
            label=options.get("label"),
        )

        # Plugin: before_render
        if self._plugin_manager and DiagramHook:
            event = DiagramPluginEvent(
                hook=DiagramHook.BEFORE_RENDER,
                context=context,
            )
            event = self._plugin_manager.dispatch(DiagramHook.BEFORE_RENDER, event)
            context = event.context

        # Check registry for custom renderers (PiMD plugins override PiDraw)
        renderer = self._registry.get(language)
        if renderer is not None and hasattr(renderer, "_renderers"):
            # It's a plugin renderer, use it directly
            if not renderer.is_available():
                elapsed = time.monotonic() - start
                result = DiagramResult(
                    source=source,
                    language=language,
                    error=f"Renderer for '{language}' is not available",
                    render_time=elapsed,
                )
                if self._plugin_manager and DiagramHook:
                    err_event = DiagramPluginEvent(
                        hook=DiagramHook.ON_ERROR,
                        context=context,
                        result=result,
                        error=result.error,
                    )
                    self._plugin_manager.dispatch(DiagramHook.ON_ERROR, err_event)
                return result
            try:
                result = renderer.render(source, **options)
                result.source = source
                result.language = language
            except Exception as exc:
                result = DiagramResult(
                    source=source,
                    language=language,
                    error=f"Renderer failed: {exc}",
                )
            result.render_time = time.monotonic() - start
            return result

        # Delegate to PiDraw
        dpi = options.get("dpi", self._config.dpi)
        transparent = options.get("transparent", True)
        use_cache = options.get("use_cache", self._config.cache)

        result = _pidraw_render(
            source,
            language,
            dpi=dpi,
            transparent=transparent,
            use_cache=use_cache,
            **{k: v for k, v in options.items() if k not in ("dpi", "transparent", "use_cache", "caption", "label")},
        )

        result.render_time = time.monotonic() - start

        # Plugin: after_render
        if self._plugin_manager and DiagramHook:
            after_event = DiagramPluginEvent(
                hook=DiagramHook.AFTER_RENDER,
                context=context,
                result=result,
            )
            after_event = self._plugin_manager.dispatch(DiagramHook.AFTER_RENDER, after_event)
            result = after_event.result or result

        logger.debug("Rendered %s diagram in %.2fs", language, result.render_time)
        return result

    # ------------------------------------------------------------------
    # Batch rendering (parallel, via PiDraw)
    # ------------------------------------------------------------------

    def render_all(
        self,
        diagrams: list[tuple[str, str | None]],
        max_workers: int | None = None,
        **options: Any,
    ) -> list[DiagramResult]:
        """Render multiple diagrams concurrently via PiDraw.

        Args:
            diagrams: List of ``(source, language)`` tuples (language can be
                      ``None`` for auto-detection).
            max_workers: Max worker threads (default from config).
            **options: Passed to each ``render()`` call.

        Returns:
            List of :class:`DiagramResult` in the same order as input.
        """
        workers = max_workers or self._config.max_concurrent
        return _pidraw_render_many(diagrams, max_workers=workers, **options)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Clear all cached diagram renders."""
        _clear_pidraw_cache()
        logger.info("Diagram cache cleared")

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def doctor(self) -> list[dict[str, str]]:
        """Run diagnostics on the PiDraw integration."""
        from pimd.diagrams.pidraw_integration import doctor as _doctor

        return _doctor()
