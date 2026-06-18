"""PiDraw integration layer — delegates all diagram rendering to PiDraw.

This module is the backward-compatibility boundary.
All rendering logic is delegated to :mod:`pimd.diagrams.adapter`.
"""

from pimd.diagrams.adapter import (
    _HAS_PIDRAW,
    clear_cache,
    detect_language,
    doctor,
    get_supported_languages,
    is_supported_language,
    normalize_language,
    render_diagram,
    render_many_diagrams,
)

# Backward compatibility alias
_normalize_language = normalize_language

__all__ = [
    "_HAS_PIDRAW",
    "_normalize_language",
    "clear_cache",
    "detect_language",
    "doctor",
    "get_supported_languages",
    "is_supported_language",
    "normalize_language",
    "render_diagram",
    "render_many_diagrams",
]
