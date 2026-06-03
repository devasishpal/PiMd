"""Batch processing — convert hundreds of files in parallel."""

from __future__ import annotations

import concurrent.futures
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pimd.export.converter import ExportConverter
from pimd.export.models import ExportFormat, ExportResult


@dataclass
class BatchResult:
    """Result of a batch processing run."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    duration: float = 0.0
    results: list[ExportResult] = field(default_factory=list)


class BatchProcessor:
    """Process multiple input files in parallel across formats."""

    def __init__(self, max_workers: int = 4) -> None:
        self.max_workers = max_workers
        self._results: list[ExportResult] = []
        self._converter = ExportConverter()

    def process_directory(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        pattern: str = "*.md",
        output_format: str | ExportFormat = ExportFormat.DOCX,
        recursive: bool = True,
        **overrides: Any,
    ) -> BatchResult:
        """Process all matching files in a directory.

        Args:
            input_dir: Directory containing input files.
            output_dir: Directory for output files.
            pattern: Glob pattern for input files (e.g. '*.md', '*.html').
            output_format: Target output format.
            recursive: Search subdirectories if True.
            **overrides: Additional export options.

        Returns:
            BatchResult with statistics.
        """
        inp = Path(input_dir)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        if recursive:
            files = sorted(inp.rglob(pattern))
        else:
            files = sorted(inp.glob(pattern))

        if not files:
            return BatchResult()

        start = time.time()
        self._results = self._process_files(files, out, output_format, **overrides)
        duration = time.time() - start

        succeeded = sum(1 for r in self._results if r.success)
        return BatchResult(
            total=len(files),
            succeeded=succeeded,
            failed=len(files) - succeeded,
            duration=duration,
            results=self._results,
        )

    def process_file_list(
        self,
        files: list[str | Path],
        output_dir: str | Path,
        output_format: str | ExportFormat = ExportFormat.DOCX,
        **overrides: Any,
    ) -> BatchResult:
        """Process a specific list of files.

        Args:
            files: List of input file paths.
            output_dir: Directory for output files.
            output_format: Target output format.
            **overrides: Additional export options.

        Returns:
            BatchResult with statistics.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        start = time.time()
        self._results = self._process_files(
            [Path(f) for f in files], out, output_format, **overrides
        )
        duration = time.time() - start

        succeeded = sum(1 for r in self._results if r.success)
        return BatchResult(
            total=len(files),
            succeeded=succeeded,
            failed=len(files) - succeeded,
            duration=duration,
            results=self._results,
        )

    def _process_files(
        self,
        files: list[Path],
        output_dir: Path,
        output_format: str | ExportFormat,
        **overrides: Any,
    ) -> list[ExportResult]:
        """Process files in parallel using a thread pool."""
        results: list[ExportResult] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map: dict[concurrent.futures.Future[ExportResult], Path] = {}
            for fpath in files:
                out_path = output_dir / f"{fpath.stem}_{output_format}.{output_format}"
                future = executor.submit(
                    self._converter.convert, fpath, output_format, out_path, **overrides
                )
                future_map[future] = fpath

            for future in concurrent.futures.as_completed(future_map):
                fpath = future_map[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    results.append(
                        ExportResult(
                            output_path=output_dir / fpath.name,
                            format=ExportFormat(output_format)
                            if isinstance(output_format, str)
                            else output_format,  # noqa: E501
                            success=False,
                            error=str(exc),
                        )
                    )

        return results

    def summary(self) -> str:
        """Return a human-readable summary of the last batch run."""
        succeeded = sum(1 for r in self._results if r.success)
        failed = sum(1 for r in self._results if not r.success)
        total = len(self._results)
        return f"Processed {total} files: {succeeded} succeeded, {failed} failed"
