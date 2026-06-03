"""Diagram engine — orchestration, caching, concurrent rendering, auto-detection."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from pimd.diagrams.cache import DiagramCache, MemoryDiagramCache
from pimd.diagrams.models import AUTO_DETECT_PATTERNS, DIAGRAM_LANGUAGES, DiagramConfig, DiagramResult
from pimd.diagrams.registry import DiagramRegistry
from pimd.utils.logging import get_logger

logger = get_logger(__name__)


_BOX_CHARS = frozenset(
    "\u2500\u2502\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c"
    "\u2550\u2551\u2554\u2557\u255a\u255d\u2560\u2563\u2566\u2569\u256c"
    "\u2501\u2503\u250f\u2513\u2517\u251b\u2523\u252b\u2533\u253b\u254b"
)


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
    # Auto-detection
    # ------------------------------------------------------------------

    def detect_language(self, source: str, hint: str | None = None) -> str | None:
        """Auto-detect the diagram language from source content.

        Args:
            source: The diagram source code.
            hint: Optional language hint (e.g. from code block info string).

        Returns:
            Detected language string, or ``None`` if detection fails.
        """
        if hint:
            hint_lower = hint.lower()
            from pimd.diagrams.models import DIAGRAM_LANGUAGE_ALIASES
            alias = DIAGRAM_LANGUAGE_ALIASES.get(hint_lower)
            if alias:
                return alias
            resolved = DIAGRAM_LANGUAGES.get(hint_lower)
            if resolved:
                return hint_lower
            return None

        # Try pattern-based detection
        stripped = source.strip()
        for lang, pattern in AUTO_DETECT_PATTERNS.items():
            if re.search(pattern, stripped, re.MULTILINE):
                return lang

        # Check for ASCII diagram heuristics
        if self._looks_like_ascii_diagram(stripped):
            return "ascii"

        return None

    @staticmethod
    def _looks_like_ascii_diagram(code: str) -> bool:
        lines = code.strip().splitlines()
        if len(lines) < 3:
            return False
        for ch in _BOX_CHARS:
            if ch in code:
                return True
        has_plus_minus = False
        has_pipe = False
        for line in lines:
            stripped = line.strip()
            if "+" in stripped and "-" in stripped:
                has_plus_minus = True
            if "|" in stripped:
                has_pipe = True
            if has_plus_minus and has_pipe:
                return True
        return False

    # ------------------------------------------------------------------
    # Single rendering
    # ------------------------------------------------------------------

    def render(
        self,
        source: str,
        language: str | None = None,
        **options: Any,
    ) -> DiagramResult:
        """Render a single diagram.

        If *language* is ``None``, auto-detection is attempted.

        Checks cache first, then dispatches to the appropriate renderer.
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
                    "Specify a language or register a renderer.",
                    render_time=elapsed,
                )

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
            if result.success and self._config.cache:
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
        diagrams: list[tuple[str, str | None]],  # (source, language or None)
        max_workers: int | None = None,
        **options: Any,
    ) -> list[DiagramResult]:
        """Render multiple diagrams concurrently.

        Args:
            diagrams: List of ``(source, language)`` tuples (language can be
                      ``None`` for auto-detection).
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
                        language=lang or "unknown",
                        error=f"Rendering failed: {exc}",
                    )

        return [r for r in results if r is not None]

    # ------------------------------------------------------------------
    # Language helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_diagram_language(language: str) -> bool:
        """Check if *language* is a known diagram language."""
        return language.lower() in DIAGRAM_LANGUAGES

    @staticmethod
    def supported_languages() -> list[str]:
        """Return list of all supported diagram languages."""
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
