"""Diagram engine — delegates all rendering to PiDraw via the stable adapter.

No rendering logic lives here. All calls go through :func:`adapter.render_diagram`.
"""

from __future__ import annotations

from typing import Any

from pimd.diagrams.adapter import (
    clear_cache as _clear_cache,
)
from pimd.diagrams.adapter import (
    detect_language as _detect,
)
from pimd.diagrams.adapter import (
    doctor as _doctor,
)
from pimd.diagrams.adapter import (
    get_supported_languages,
    is_supported_language,
)
from pimd.diagrams.adapter import (
    render_diagram as _render,
)
from pimd.diagrams.adapter import (
    render_many_diagrams as _render_many,
)
from pimd.diagrams.models import DiagramConfig, DiagramResult
from pimd.utils.logging import get_logger

logger = get_logger(__name__)


class DiagramEngine:
    """Central diagram rendering engine.

    Orchestrates detection, rendering, and diagnostics.
    All actual rendering is delegated to PiDraw via the stable adapter.
    """

    def __init__(self, config: DiagramConfig | None = None) -> None:
        self._config = config or DiagramConfig()

    @property
    def config(self) -> DiagramConfig:
        return self._config

    def detect_language(self, source: str, hint: str | None = None) -> str | None:
        return _detect(source, hint)

    @staticmethod
    def is_diagram_language(language: str) -> bool:
        return is_supported_language(language)

    @staticmethod
    def supported_languages() -> list[str]:
        return list(get_supported_languages().keys())

    def render(self, source: str, language: str | None = None, **options: Any) -> DiagramResult:
        dpi = options.pop("dpi", self._config.dpi)
        transparent = options.pop("transparent", True)
        use_cache = options.pop("use_cache", self._config.cache)
        return _render(source, language, dpi=dpi, transparent=transparent, use_cache=use_cache, **options)

    def render_all(self, diagrams: list[tuple[str, str | None]], max_workers: int | None = None, **options: Any) -> list[DiagramResult]:
        workers = max_workers or self._config.max_concurrent
        return _render_many(diagrams, max_workers=workers, **options)

    def clear_cache(self) -> None:
        _clear_cache()
        logger.info("Diagram cache cleared")

    def doctor(self) -> list[dict[str, str]]:
        return _doctor()
