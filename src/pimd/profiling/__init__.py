"""Profiling — backwards-compatible re-exports from :mod:`pimd.observability`.

.. deprecated:: 2.0.0
    Use ``pimd.observability`` directly. This module is kept for
    backward compatibility and will be removed in 3.0.0.
"""

from pimd.observability import (
    ConversionReport,
    MemorySnapshot,
    PipelineProfile,
    Profiler,
    Timer,
    measure_time,
    profile_conversion,
)

__all__ = [
    "ConversionReport",
    "measure_time",
    "MemorySnapshot",
    "PipelineProfile",
    "Profiler",
    "profile_conversion",
    "Timer",
]
