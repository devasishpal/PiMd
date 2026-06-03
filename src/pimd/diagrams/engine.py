"""Diagram engine — orchestration, caching, concurrent rendering."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from pimd.diagrams.cache import DiagramCache, MemoryDiagramCache
from pimd.diagrams.models import DiagramConfig, DiagramResult
from pimd.diagrams.registry import DiagramRegistry
from pimd.utils.logging import get_logger

logger = get_logger(__name__)


class DiagramEngine:
    """Central diagram rendering engine.

    Orchestrates detection, rendering, caching, and fallback for all
    diagram types.
    """

    def __init__(
        self,
        registry: DiagramRegistry | None = None,
        cache: DiagramCache | None = None,
        config: DiagramConfig | None = None,
    ) -> None:
        self._registry = registry or DiagramRegistry()
        self._cache = cache or MemoryDiagramCache()
        self._config = config or DiagramConfig()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def registry(self) -> DiagramRegistry:
        return self._registry

    @property
    def cache(self) -> DiagramCache:
        return self._cache

    @property
    def config(self) -> DiagramConfig:
        return self._config

    # ------------------------------------------------------------------
    # Single rendering
    # ------------------------------------------------------------------

    def render(
        self,
        source: str,
        language: str,
        **options: Any,
    ) -> DiagramResult:
        """Render a single diagram.

        Checks cache first, then dispatches to the appropriate renderer.
        On failure, returns a ``DiagramResult`` with ``error`` set (never
        raises).
        """
        start = time.monotonic()

        # Try cache
        cache_key = DiagramCache.make_key(source, language)
        cached = self._cache.get(cache_key)
        if cached is not None:
            cached.cached = True
            cached.render_time = time.monotonic() - start
            logger.debug("Cache hit for %s diagram", language)
            return cached

        # Find renderer
        renderer = self._registry.get(language)
        if renderer is None:
            elapsed = time.monotonic() - start
            return DiagramResult(
                source=source,
                language=language,
                error=f"No renderer registered for language '{language}'",
                render_time=elapsed,
            )

        # Render
        if not renderer.is_available():
            elapsed = time.monotonic() - start
            return DiagramResult(
                source=source,
                language=language,
                error=f"Renderer '{renderer.name}' is not available "
                f"(tool not installed: {renderer._tool_name()})",
                render_time=elapsed,
            )

        try:
            result = renderer.render(source, **options)
            result.source = source
            result.language = language
            result.render_time = time.monotonic() - start

            # Cache the result
            if result.success:
                self._cache.set(cache_key, result, ttl=options.get("cache_ttl"))

            logger.debug(
                "Rendered %s diagram in %.2fs",
                language,
                result.render_time,
            )
            return result
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.exception("Failed to render %s diagram", language)
            return DiagramResult(
                source=source,
                language=language,
                error=f"Rendering failed: {exc}",
                render_time=elapsed,
            )

    # ------------------------------------------------------------------
    # Batch rendering (parallel)
    # ------------------------------------------------------------------

    def render_all(
        self,
        diagrams: list[tuple[str, str]],  # (source, language)
        max_workers: int | None = None,
        **options: Any,
    ) -> list[DiagramResult]:
        """Render multiple diagrams concurrently.

        Args:
            diagrams: List of ``(source, language)`` tuples.
            max_workers: Max worker threads (default from config).
            **options: Passed to each ``render()`` call.

        Returns:
            List of :class:`DiagramResult` in the same order as input.
        """
        workers = max_workers or self._config.max_concurrent
        results: list[DiagramResult | None] = [None] * len(diagrams)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {}
            for idx, (source, lang) in enumerate(diagrams):
                future = executor.submit(self.render, source, lang, **options)
                future_map[future] = idx

            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    source, lang = diagrams[idx]
                    results[idx] = DiagramResult(
                        source=source,
                        language=lang,
                        error=f"Rendering failed: {exc}",
                    )

        return [r for r in results if r is not None]

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    @staticmethod
    def is_diagram_language(language: str) -> bool:
        """Check if *language* is a known diagram language."""
        from pimd.diagrams.models import DIAGRAM_LANGUAGES

        return language.lower() in DIAGRAM_LANGUAGES

    @staticmethod
    def supported_languages() -> list[str]:
        """Return list of all supported diagram languages."""
        from pimd.diagrams.models import DIAGRAM_LANGUAGES

        return list(DIAGRAM_LANGUAGES.keys())

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Clear all cached diagram renders."""
        self._cache.clear()
        logger.info("Diagram cache cleared")

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def doctor(self) -> list[dict[str, str]]:
        """Run diagnostics on all registered renderers."""
        results: list[dict[str, str]] = []
        for renderer in self._registry._renderers.values():
            available = renderer.is_available()
            results.append(
                {
                    "language": renderer.language,
                    "name": renderer.name,
                    "available": "OK" if available else "Not installed",
                    "tool": renderer._tool_name(),
                }
            )
        return results
