"""Stable PiDraw adapter — PiMD's single integration point with PiDraw.

No rendering logic lives here. All calls are delegated to ``pidraw.render()``.
Errors are normalized to ``DiagramResult(success=False, error=...)``.
The adapter is the backward-compatibility boundary.
"""

from __future__ import annotations

import time
from typing import Any

from pimd.diagrams.models import DiagramResult
from pimd.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Lazy PiDraw import — graceful degradation
# ---------------------------------------------------------------------------

_HAS_PIDRAW = False
_pidraw_render = None
_pidraw_detect = None
_pidraw_list_renderers = None
_pidraw_svg_to_png = None

try:
    from pidraw import render as _pidraw_render
    from pidraw.backend.png import svg_to_png as _pidraw_svg_to_png
    from pidraw.detector import detect as _pidraw_detect
    from pidraw.registry import list_renderers as _pidraw_list_renderers
    _HAS_PIDRAW = True
except ImportError:
    pass


def _get_pidraw_version() -> str:
    try:
        from pidraw import __version__
        return __version__
    except ImportError:
        return "?"


# ---------------------------------------------------------------------------
# Language support — queried from PiDraw at runtime
# ---------------------------------------------------------------------------


def get_supported_languages() -> dict[str, str]:
    if not _HAS_PIDRAW:
        return {}
    try:
        renderers = _pidraw_list_renderers()
        return {k: v.get("name", k) for k, v in renderers.items()}
    except Exception:
        try:
            from pidraw.models import DiagramLanguage
            return {lang.value: lang.value for lang in DiagramLanguage}
        except Exception:
            return {}


def is_supported_language(language: str) -> bool:
    return language.lower() in get_supported_languages()


def detect_language(source: str, hint: str | None = None) -> str | None:
    """Detect diagram language via PiDraw, optionally using a hint."""
    if not _HAS_PIDRAW:
        return None
    if hint:
        norm = _normalize(hint)
        if norm in get_supported_languages():
            return norm
        return None
    try:
        detected = _pidraw_detect(source)
        if detected and detected != "unknown":
            return detected
    except Exception:
        pass
    return None


_ALIASES: dict[str, str] = {
    "mmd": "mermaid",
    "puml": "plantuml",
    "dot": "graphviz",
    "ditaa": "ascii",
    "wave": "wavedrom",
}


def _normalize(language: str) -> str:
    supported = get_supported_languages()
    lower = language.lower()
    if lower in supported:
        return lower
    alias = _ALIASES.get(lower)
    if alias and alias in supported:
        return alias
    return lower


def normalize_language(language: str) -> str:
    """Normalize a diagram language name, resolving aliases.

    Returns the canonical language name (lowercase).
    """
    return _normalize(language)


# ---------------------------------------------------------------------------
# Primary render function — never raises
# ---------------------------------------------------------------------------


def render_diagram(
    source: str,
    language: str | None = None,
    *,
    dpi: int = 300,
    transparent: bool = True,
    use_cache: bool = True,
    **options: Any,
) -> DiagramResult:
    """Render a diagram via PiDraw. Never raises — returns DiagramResult.

    Args:
        source: Raw diagram source code.
        language: Language hint (auto-detected if ``None``).
        dpi: DPI for PNG output.
        transparent: Whether PNG should have transparent background.
        use_cache: Whether to use PiDraw's cache.
        **options: Passed through to PiDraw.

    Returns:
        :class:`DiagramResult` — always, even on error.
    """
    start = time.monotonic()

    if not _HAS_PIDRAW:
        return _result(source, language or "unknown", error="PiDraw is not installed. Run: pip install pidraw", start=start)

    if language is None:
        language = detect_language(source)
        if language is None:
            return _result(source, "unknown", error="Could not auto-detect diagram language. Specify a language or install pidraw.", start=start)
    else:
        language = _normalize(language)

    # Filter options to only those recognized by PiDraw's render()
    _pidraw_kwargs = {}
    for k in ("format", "optimize", "quality", "scale", "transparent", "timeout", "theme"):
        if k in options:
            _pidraw_kwargs[k] = options[k]

    # Render SVG first. SVG-to-PNG conversion is done separately so
    # a PNG backend failure never loses the SVG — the DOCX renderer
    # falls back to a placeholder showing the source code.
    try:
        result = _pidraw_render(source, language=language, format="svg", **_pidraw_kwargs)
        if hasattr(result, "success") and not result.success:
            return _result(source, language, error=result.error or "Render failed", start=start)
    except Exception as exc:
        logger.exception("PiDraw rendering failed for %s", language)
        return _result(source, language, error=f"PiDraw rendering failed: {exc}", start=start)

    svg = result.svg if hasattr(result, "svg") else ""

    # Separate SVG→PNG conversion — errors are non-fatal
    png: bytes | None = None
    if svg and _pidraw_svg_to_png is not None:
        try:
            png = _pidraw_svg_to_png(svg, scale=dpi / 96.0, transparent=transparent)
        except Exception as exc:
            logger.warning("SVG-to-PNG conversion failed for %s: %s", language, exc)

    return _result(
        source,
        language,
        svg=svg,
        png=png,
        width=_extract_width(svg),
        height=_extract_height(svg),
        start=start,
    )


def render_many_diagrams(
    diagrams: list[tuple[str, str | None]],
    max_workers: int = 4,
    **options: Any,
) -> list[DiagramResult]:
    """Render multiple diagrams in parallel. Never raises.

    Args:
        diagrams: List of ``(source, language)`` tuples.
        max_workers: Max parallel workers.
        **options: Passed to each :func:`render_diagram` call.

    Returns:
        List of :class:`DiagramResult` — one per input, in order.
    """
    results: list[DiagramResult | None] = [None] * len(diagrams)

    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for idx, (src, lang) in enumerate(diagrams):
            futures[pool.submit(render_diagram, src, lang, **options)] = idx
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                results[idx] = fut.result()
            except Exception as exc:
                src, lang = diagrams[idx]
                results[idx] = _result(src, lang or "unknown", error=f"Rendering failed: {exc}")

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def doctor() -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    if _HAS_PIDRAW:
        checks.append({"check": "PiDraw installed", "status": "ok", "detail": f"pidraw v{_get_pidraw_version()}"})
        langs = get_supported_languages()
        checks.append({"check": f"Supported languages ({len(langs)})", "status": "ok", "detail": ", ".join(sorted(langs.keys()))})
    else:
        checks.append({"check": "PiDraw installed", "status": "error", "detail": "Not installed — pip install pidraw"})
    return checks


def clear_cache() -> None:
    try:
        from pidraw.cache import CacheManager
        CacheManager().clear()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _result(
    source: str,
    language: str,
    svg: str | None = None,
    png: bytes | None = None,
    width: int | None = None,
    height: int | None = None,
    error: str | None = None,
    start: float | None = None,
) -> DiagramResult:
    elapsed = (time.monotonic() - start) if start is not None else 0.0
    return DiagramResult(
        source=source,
        language=language,
        svg=svg,
        png=png,
        width=width,
        height=height,
        error=error,
        render_time=elapsed,
    )


def _extract_width(svg: str) -> int | None:
    import re
    try:
        m = re.search(r'<svg[^>]*\swidth="(\d+(?:\.\d+)?)"', svg)
        if m:
            return int(float(m.group(1)))
        m = re.search(r'viewBox="\d+\s+\d+\s+(\d+(?:\.\d+)?)\s+\d+(?:\.\d+)?"', svg)
        if m:
            return int(float(m.group(1)))
    except Exception:
        pass
    return None


def _extract_height(svg: str) -> int | None:
    import re
    try:
        m = re.search(r'<svg[^>]*\sheight="(\d+(?:\.\d+)?)"', svg)
        if m:
            return int(float(m.group(1)))
        m = re.search(r'viewBox="\d+\s+\d+\s+\d+(?:\.\d+)?\s+(\d+(?:\.\d+)?)"', svg)
        if m:
            return int(float(m.group(1)))
    except Exception:
        pass
    return None
