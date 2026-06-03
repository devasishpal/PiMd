"""Equation rendering system — native OMML Word equations with SVG fallback."""

from pimd.equations.engine import EquationEngine
from pimd.equations.models import EquationConfig, EquationResult

__all__ = [
    "EquationEngine",
    "EquationResult",
    "EquationConfig",
]
