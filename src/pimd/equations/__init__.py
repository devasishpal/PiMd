"""Equation rendering system — renders via PiDraw's Playwright→PNG pipeline."""

from pimd.equations.engine import EquationEngine
from pimd.equations.models import EquationConfig, EquationResult

__all__ = [
    "EquationEngine",
    "EquationResult",
    "EquationConfig",
]
