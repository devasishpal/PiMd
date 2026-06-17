"""PiDraw integration layer — delegates all diagram rendering to PiDraw.

This is the single source of truth for diagram operations.
PiMD never implements its own diagram rendering logic.
"""

from __future__ import annotations

import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from pimd.utils.logging import get_logger

logger = get_logger(__name__)

# ------------------------------------------------------------------
# Lazy PiDraw imports (graceful degradation if not installed)
# ------------------------------------------------------------------

_HAS_PIDRAW = False
try:
    from pidraw import render as _pidraw_render
    from pidraw import render_many as _pidraw_render_many
    from pidraw.backend.png import svg_to_png as _pidraw_svg_to_png
    from pidraw.detector import detect as _pidraw_detect
    from pidraw.models import DiagramLanguage
    from pidraw.registry import list_renderers as _pidraw_list_renderers

    _HAS_PIDRAW = True
except ImportError:
    _pidraw_render = None  # type: ignore
    _pidraw_render_many = None  # type: ignore
    _pidraw_svg_to_png = None  # type: ignore
    _pidraw_detect = None  # type: ignore
    DiagramLanguage = None  # type: ignore
    _pidraw_list_renderers = None  # type: ignore


def _get_diagram_result() -> type:
    """Lazy import of DiagramResult to avoid circular imports."""
    from pimd.diagrams.models import DiagramResult
    return DiagramResult


def _make_diagram_result(**kwargs: Any) -> Any:
    """Create a DiagramResult with lazy import."""
    cls = _get_diagram_result()
    return cls(**kwargs)


# ------------------------------------------------------------------
# Supported languages — queried from PiDraw, never hardcoded
# ------------------------------------------------------------------


def get_supported_languages() -> dict[str, str]:
    """Return all diagram languages PiDraw supports.

    Returns:
        ``{language_key: display_name}`` dictionary.
    """
    if not _HAS_PIDRAW:
        return {}
    try:
        renderers = _pidraw_list_renderers()
        return {k: v.get("name", k) for k, v in renderers.items()}
    except Exception:
        if DiagramLanguage is not None:
            return {lang.value: lang.value for lang in DiagramLanguage}
        return {}


def is_supported_language(language: str) -> bool:
    """Check if *language* is supported by PiDraw."""
    return language.lower() in get_supported_languages()


# ------------------------------------------------------------------
# Detection — delegates to PiDraw's 87-rule detector
# ------------------------------------------------------------------


def detect_language(source: str, hint: str | None = None) -> str | None:
    """Auto-detect diagram language using PiDraw's detector.

    Args:
        source: The diagram source code.
        hint: Optional language hint (e.g. from code block info string).

    Returns:
        Detected language string, or ``None``.
    """
    if not _HAS_PIDRAW:
        return None

    if hint:
        hint_lower = hint.lower()
        normalized = _normalize_language(hint_lower)
        if normalized in get_supported_languages():
            return normalized
        return None

    try:
        detected = _pidraw_detect(source)
        if detected and detected != "unknown":
            return detected
    except Exception:
        pass

    return None


_ALIAS_TO_PIDRAW: dict[str, str] = {
    "mmd": "mermaid",
    "puml": "plantuml",
    "dot": "graphviz",
    "ditaa": "ascii",
    "blockdiag": "blockdiag",
    "seqdiag": "seqdiag",
    "actdiag": "actdiag",
    "nwdiag": "nwdiag",
    "packetdiag": "packetdiag",
    "vega-lite": "vega-lite",
    "nomnoml": "nomnoml",
    "wavedrom": "wavedrom",
    "bpmn": "bpmn",
    "excalidraw": "excalidraw",
    "markmap": "markmap",
    "structurizr": "structurizr",
    "tikz": "tikz",
    "kroki": "kroki",
}


def _resolve_alias(hint: str, supported: dict[str, str]) -> str | None:
    """Resolve common language aliases."""
    resolved = _ALIAS_TO_PIDRAW.get(hint, hint)
    if resolved in supported:
        return resolved
    return None


def _normalize_language(language: str) -> str:
    """Normalize a language name to PiDraw's canonical form."""
    supported = get_supported_languages()
    lower = language.lower()
    if lower in supported:
        return lower
    alias = _ALIAS_TO_PIDRAW.get(lower)
    if alias and alias in supported:
        return alias
    return lower


# ------------------------------------------------------------------
# Rendering — delegates entirely to PiDraw
# ------------------------------------------------------------------

_cache_lock = threading.Lock()
_memory_cache: dict[str, Any] = {}


def make_cache_key(source: str, language: str) -> str:
    """Generate a deterministic SHA-256 cache key."""
    hasher = hashlib.sha256()
    hasher.update(source.encode("utf-8"))
    hasher.update(language.encode("utf-8"))
    return f"diagram:{language}:{hasher.hexdigest()[:32]}"


def _check_memory_cache(key: str) -> Any | None:
    with _cache_lock:
        return _memory_cache.get(key)


def _store_memory_cache(key: str, result: Any) -> None:
    with _cache_lock:
        _memory_cache[key] = result


def render_diagram(
    source: str,
    language: str | None = None,
    *,
    dpi: int = 300,
    transparent: bool = True,
    use_cache: bool = True,
    **options: Any,
) -> Any:
    """Render a diagram via PiDraw.

    This is the primary rendering function. All diagram rendering in PiMD
    must go through this function.

    Args:
        source: Raw diagram source code.
        language: Diagram language (auto-detected if ``None``).
        dpi: DPI for PNG output (default 300).
        transparent: Whether PNG should have transparent background.
        use_cache: Whether to use in-memory cache.
        **options: Additional options passed to PiDraw.

    Returns:
        :class:`DiagramResult` with SVG, PNG, and metadata.
    """
    if not _HAS_PIDRAW:
        return _make_diagram_result(
            source=source,
            language=language or "unknown",
            error="PiDraw is not installed. Run: pip install pidraw",
        )

    if language is None:
        language = detect_language(source)
        if language is None:
            return _make_diagram_result(
                source=source,
                language="unknown",
                error="Could not auto-detect diagram language. "
                "Specify a language or install pidraw.",
            )
    else:
        language = _normalize_language(language)

    cache_key = make_cache_key(source, language)
    if use_cache:
        cached = _check_memory_cache(cache_key)
        if cached is not None:
            return cached

    try:
        result = _pidraw_render(
            source,
            language=language,
            format="svg",
            transparent=transparent,
            **options,
        )

        svg = result.svg if hasattr(result, "svg") else str(result)

        png: bytes | None = None
        if _pidraw_svg_to_png is not None:
            try:
                png = _pidraw_svg_to_png(
                    svg,
                    scale=dpi / 96.0,
                    transparent=transparent,
                )
            except Exception as exc:
                logger.warning("SVG-to-PNG conversion failed: %s", exc)

        width, height = _extract_svg_dimensions(svg)

        diagram_result = _make_diagram_result(
            source=source,
            language=language,
            svg=svg,
            png=png,
            width=width,
            height=height,
        )

        if use_cache:
            _store_memory_cache(cache_key, diagram_result)

        return diagram_result

    except Exception as exc:
        logger.exception("PiDraw rendering failed for %s", language)
        return _make_diagram_result(
            source=source,
            language=language,
            error=f"PiDraw rendering failed: {exc}",
        )


def render_many_diagrams(
    diagrams: list[tuple[str, str | None]],
    max_workers: int = 4,
    **options: Any,
) -> list[Any]:
    """Render multiple diagrams concurrently via PiDraw.

    Args:
        diagrams: List of ``(source, language)`` tuples.
        max_workers: Number of parallel workers (default 4).
        **options: Passed to each :func:`render_diagram` call.

    Returns:
        List of :class:`DiagramResult` in input order.
    """
    results: list[Any | None] = [None] * len(diagrams)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for idx, (source, lang) in enumerate(diagrams):
            future = executor.submit(render_diagram, source, lang, **options)
            future_map[future] = idx

        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                source, lang = diagrams[idx]
                results[idx] = _make_diagram_result(
                    source=source,
                    language=lang or "unknown",
                    error=f"Rendering failed: {exc}",
                )

    return [r for r in results if r is not None]


def clear_cache() -> None:
    """Clear the in-memory diagram cache."""
    with _cache_lock:
        _memory_cache.clear()


def doctor() -> list[dict[str, str]]:
    """Run diagnostics on the PiDraw integration."""
    results: list[dict[str, str]] = []

    if _HAS_PIDRAW:
        results.append({
            "check": "PiDraw installed",
            "status": "ok",
            "detail": f"pidraw v{_get_pidraw_version()}",
        })
        languages = get_supported_languages()
        results.append({
            "check": f"Supported languages ({len(languages)})",
            "status": "ok",
            "detail": ", ".join(sorted(languages.keys())),
        })
    else:
        results.append({
            "check": "PiDraw installed",
            "status": "error",
            "detail": "Not installed — pip install pidraw",
        })

    return results


def _get_pidraw_version() -> str:
    try:
        from pidraw import __version__
        return __version__
    except ImportError:
        return "?"


def _extract_svg_dimensions(svg: str) -> tuple[int | None, int | None]:
    """Extract width and height from an SVG string."""
    width: int | None = None
    height: int | None = None
    try:
        import re
        m = re.search(r'<svg[^>]*\swidth="(\d+(?:\.\d+)?)"', svg)
        if m:
            width = int(float(m.group(1)))
        m = re.search(r'<svg[^>]*\sheight="(\d+(?:\.\d+)?)"', svg)
        if m:
            height = int(float(m.group(1)))
        if width is None and height is None:
            m = re.search(r'viewBox="\d+\s+\d+\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)"', svg)
            if m:
                width = int(float(m.group(1)))
                height = int(float(m.group(2)))
    except Exception:
        pass
    return width, height
