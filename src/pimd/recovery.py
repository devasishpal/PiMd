"""Failure recovery — graceful degradation, warning reports, never lose entire document.

When a diagram fails, equation fails, image is missing, or table is malformed,
the conversion continues and a warning report is generated.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pimd.models import Document


@dataclass
class RecoveryWarning:
    """A single warning generated during recovery."""

    stage: str
    message: str
    block_index: int | None = None
    block_type: str = ""
    details: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class RecoveryReport:
    """Report of all warnings generated during a fault-tolerant conversion."""

    warnings: list[RecoveryWarning] = field(default_factory=list)
    document: Document | None = None
    total_blocks: int = 0
    failed_blocks: int = 0
    succeeded_blocks: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_blocks == 0:
            return 1.0
        return self.succeeded_blocks / self.total_blocks

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_blocks": self.total_blocks,
            "failed_blocks": self.failed_blocks,
            "succeeded_blocks": self.succeeded_blocks,
            "success_rate": round(self.success_rate, 4),
            "warnings": [
                {
                    "stage": w.stage,
                    "message": w.message,
                    "block_index": w.block_index,
                    "block_type": w.block_type,
                    "timestamp": w.timestamp,
                }
                for w in self.warnings
            ],
        }

    def summary(self) -> str:
        lines = [
            f"Recovery Report ({len(self.warnings)} warnings)",
            f"  Blocks: {self.succeeded_blocks}/{self.total_blocks} succeeded "
            f"({self.success_rate:.1%})",
        ]
        if self.warnings:
            lines.append("  Warnings:")
            for w in self.warnings[:20]:
                lines.append(f"    [{w.stage}] {w.message}")
            if len(self.warnings) > 20:
                lines.append(f"    ... and {len(self.warnings) - 20} more")
        return "\n".join(lines)


class RecoveryContext:
    """Context manager for fault-tolerant block processing.

    Usage::

        recovery = RecoveryContext()
        with recovery:
            for block in doc.blocks:
                recovery.process_block(block, render_block)
        report = recovery.report
    """

    def __init__(self) -> None:
        self.report = RecoveryReport()
        self._document = Document()

    def __enter__(self) -> RecoveryContext:
        return self

    def __exit__(self, *args: Any) -> None:
        self.report.document = self._document

    def process_block(
        self,
        block: Any,
        processor: Any,
        block_index: int | None = None,
    ) -> Any:
        """Process a block with fault tolerance.

        Returns the processed block or a placeholder on failure.
        """
        from pimd.models import Paragraph, Span

        self.report.total_blocks += 1
        try:
            result = processor(block)
            self.report.succeeded_blocks += 1
            return result
        except Exception as exc:
            self.report.failed_blocks += 1
            bt = type(block).__name__ if block is not None else "unknown"
            self.report.warnings.append(
                RecoveryWarning(
                    stage="process_block",
                    message=f"Failed to process {bt}: {exc}",
                    block_index=block_index,
                    block_type=bt,
                    details=traceback.format_exc(),
                )
            )
            placeholder = Paragraph(spans=[Span(text=f"[{bt} processing failed: {exc}]")])
            self._document.blocks.append(placeholder)
            return placeholder

    def warn(self, stage: str, message: str, block: Any = None) -> None:
        bt = type(block).__name__ if block is not None else ""
        self.report.warnings.append(
            RecoveryWarning(
                stage=stage,
                message=message,
                block_type=bt,
            )
        )


def safe_convert(fn: Any, *args: Any, **kwargs: Any) -> tuple[Any, RecoveryReport | None]:
    """Wrap a conversion function with full recovery.

    Returns (result, recovery_report). If recovery was triggered,
    the report contains warnings. If no issues, report is None.
    """
    from pimd.exceptions import PiMDError

    try:
        result = fn(*args, **kwargs)
        return result, None
    except PiMDError:
        raise
    except Exception as exc:
        report = RecoveryReport()
        report.warnings.append(
            RecoveryWarning(
                stage="safe_convert",
                message=str(exc),
                details=traceback.format_exc(),
            )
        )
        report.total_blocks = 1
        report.failed_blocks = 1
        return None, report


__all__ = [
    "RecoveryWarning",
    "RecoveryReport",
    "RecoveryContext",
    "safe_convert",
]
