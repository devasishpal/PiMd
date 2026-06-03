"""Project conversion — convert entire documentation repositories."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pimd.export import ExportConverter
from pimd.incremental import IncrementalBuildTracker


@dataclass
class ProjectFile:
    """A single file found during project discovery."""

    path: Path
    relative_path: str
    format: str
    size_bytes: int = 0


@dataclass
class ProjectResult:
    """Result of a project conversion."""

    total_files: int = 0
    converted: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)
    output_dir: str = ""
    duration: float = 0.0
    files: list[ProjectFile] = field(default_factory=list)


class ProjectConverter:
    """Convert entire documentation repositories.

    Usage::

        pc = ProjectConverter()
        result = pc.convert_project("docs/", "output/")
        print(result.summary())
    """

    def __init__(self, incremental: bool = True) -> None:
        self._tracker = IncrementalBuildTracker() if incremental else None

    def discover_files(
        self,
        root_dir: str | Path,
        pattern: str = "*.md",
        recursive: bool = True,
        exclude_dirs: set[str] | None = None,
    ) -> list[ProjectFile]:
        """Discover all matching files in a directory tree."""
        root = Path(root_dir)
        exclude = exclude_dirs or {"node_modules", ".git", "__pycache__", ".venv", ".tox"}
        files: list[ProjectFile] = []
        if recursive:
            for p in root.rglob(pattern):
                if any(part in exclude for part in p.parts):
                    continue
                files.append(
                    ProjectFile(
                        path=p,
                        relative_path=str(p.relative_to(root)),
                        format=p.suffix.lstrip("."),
                        size_bytes=p.stat().st_size,
                    )
                )
        else:
            for p in root.glob(pattern):
                files.append(
                    ProjectFile(
                        path=p,
                        relative_path=p.name,
                        format=p.suffix.lstrip("."),
                        size_bytes=p.stat().st_size,
                    )
                )
        return sorted(files, key=lambda f: f.relative_path)

    def convert_project(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        *,
        merge: bool = False,
        output_format: str = "docx",
        pattern: str = "*.md",
        recursive: bool = True,
        exclude_dirs: set[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> ProjectResult:
        """Convert an entire project directory.

        Args:
            input_dir: Root directory to scan.
            output_dir: Output directory.
            merge: Merge all files into a single document.
            output_format: Output format for individual conversions.
            pattern: Glob pattern for file discovery.
            recursive: Search subdirectories.
            exclude_dirs: Directories to skip.
            options: Extra conversion options.

        Returns:
            ProjectResult with conversion statistics.
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files = self.discover_files(input_path, pattern, recursive, exclude_dirs)
        result = ProjectResult(
            total_files=len(files),
            output_dir=str(output_path),
        )

        if merge:
            self._convert_merged(files, output_path, output_format, options, result)
        else:
            self._convert_individual(files, output_path, output_format, options, result)

        return result

    def _convert_individual(
        self,
        files: list[ProjectFile],
        output_dir: Path,
        output_format: str,
        options: dict[str, Any] | None,
        result: ProjectResult,
    ) -> None:
        exporter = ExportConverter()
        opts = options or {}
        for pf in files:
            rel_stem = Path(pf.relative_path).stem
            out_path = output_dir / f"{rel_stem}.{output_format}"

            if self._tracker and not self._tracker.is_changed(pf.path):
                result.skipped += 1
                continue

            try:
                if output_format == "docx":
                    exporter.convert(str(pf.path), "docx", str(out_path), **opts)
                else:
                    exporter.convert(str(pf.path), output_format, str(out_path), **opts)
                result.converted += 1
                if self._tracker:
                    self._tracker.record_build(pf.path)
            except Exception as exc:
                result.failed += 1
                result.errors.append((pf.relative_path, str(exc)))

    def _convert_merged(
        self,
        files: list[ProjectFile],
        output_dir: Path,
        output_format: str,
        options: dict[str, Any] | None,
        result: ProjectResult,
    ) -> None:
        from pimd.merge import DocumentMerger

        merger = DocumentMerger()
        input_paths = [f.path for f in files]
        out_path = output_dir / f"merged.{output_format}"
        try:
            merger.merge(input_paths, str(out_path))
            result.converted = len(files)
        except Exception as exc:
            result.failed = len(files)
            for f in files:
                result.errors.append((f.relative_path, str(exc)))
