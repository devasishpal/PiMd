"""Documentation repository conversion mode."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from pimd.export.converter import ExportConverter
from pimd.export.models import ExportFormat
from pimd.incremental import IncrementalBuildTracker
from pimd.merge import DocumentMerger
from pimd.parallel import parallel_map


class RepoType(Enum):
    MKDOCS = "mkdocs"
    DOCUSAURUS = "docusaurus"
    SPHINX = "sphinx"
    OBSIDIAN = "obsidian"
    GITHUB_WIKI = "github_wiki"
    PLAIN_MD = "plain_md"
    UNKNOWN = "unknown"


REPO_CONFIG_FILES: set[str] = {
    ".pimdconfig",
    "pimd.toml",
    ".pimd/config.toml",
    "mkdocs.yml",
    "mkdocs.yaml",
    "docusaurus.config.js",
    "docusaurus.config.ts",
    "conf.py",
    "sidebars.js",
    "sidebars.ts",
    "sidebars.json",
}

REPO_DOCS_DIR_NAMES: set[str] = {
    "docs",
    "wiki",
    "knowledge-base",
    "knowledge_base",
    "kb",
    "documentation",
    "help",
    "guide",
    "manual",
    "content",
    "markdown",
    "pages",
    "src",
    "source",
}

_FILE_EXTENSIONS: set[str] = {".md", ".mdx", ".rst", ".html", ".htm", ".txt", ".markdown"}

_HUMAN_UNITS: list[tuple[int, str]] = [
    (1024 * 1024 * 1024, "GB"),
    (1024 * 1024, "MB"),
    (1024, "KB"),
]


@dataclass
class DiscoveryResult:
    repo_type: RepoType
    root_path: Path
    docs_dirs: list[Path]
    config_files: list[Path]
    file_count: int
    ecosystem: str


@dataclass
class RepositoryConfig:
    output_mode: str = "auto"
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    parallel_workers: int = 1
    incremental: bool = False
    merge: bool = False
    preserve_structure: bool = True
    output_format: str = "docx"
    recursive: bool = True


@dataclass
class RepoFile:
    relative_path: Path
    absolute_path: Path
    title: str
    section: str
    last_modified: float
    hash: str
    status: str = "pending"


@dataclass
class RepoResult:
    total_files: int = 0
    converted: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)
    output_path: str = ""
    duration: float = 0.0


def discover_repository(path: str | Path) -> DiscoveryResult:
    root = Path(path).resolve()
    repo_type = detect_repo_type(root)
    docs_dirs = find_docs_directories(root)
    config_files = _find_config_files(root)
    ecosystem = repo_type.value if repo_type != RepoType.UNKNOWN else "unknown"
    file_count = _count_doc_files(docs_dirs) if docs_dirs else _count_doc_files([root])
    return DiscoveryResult(
        repo_type=repo_type,
        root_path=root,
        docs_dirs=docs_dirs,
        config_files=config_files,
        file_count=file_count,
        ecosystem=ecosystem,
    )


def detect_repo_type(path: str | Path, files: list[Path] | None = None) -> RepoType:
    root = Path(path).resolve()
    if not root.is_dir():
        return RepoType.UNKNOWN

    if files is not None:
        names = {f.name for f in files}
    else:
        try:
            names = {p.name for p in root.iterdir() if p.is_file()}
        except PermissionError:
            return RepoType.UNKNOWN

    if "mkdocs.yml" in names or "mkdocs.yaml" in names:
        return RepoType.MKDOCS

    if "docusaurus.config.js" in names or "docusaurus.config.ts" in names:
        return RepoType.DOCUSAURUS

    if "conf.py" in names or ((root / "source").is_dir() and (root / "source" / "conf.py").is_file()):
        return RepoType.SPHINX

    if (root / ".obsidian").is_dir():
        return RepoType.OBSIDIAN

    if (root / "wiki").is_dir() and any(
        (root / "wiki").rglob("*.md")
    ):
        return RepoType.GITHUB_WIKI

    docs_dirs = find_docs_directories(root)
    if docs_dirs:
        return RepoType.PLAIN_MD

    if any(p.suffix == ".md" for p in root.iterdir() if p.is_file()):
        return RepoType.PLAIN_MD

    return RepoType.PLAIN_MD


def find_docs_directories(path: Path) -> list[Path]:
    result: list[Path] = []
    try:
        for entry in path.iterdir():
            if entry.is_dir() and entry.name.lower() in REPO_DOCS_DIR_NAMES:
                result.append(entry)
    except PermissionError:
        pass
    return result


def collect_repo_files(
    path: str | Path,
    config: RepositoryConfig | None = None,
) -> list[RepoFile]:
    root = Path(path).resolve()
    cfg = config or RepositoryConfig()
    docs_dirs = find_docs_directories(root)
    search_roots: list[Path] = docs_dirs if docs_dirs else [root]

    files: list[RepoFile] = []
    seen: set[Path] = set()

    for search_root in search_roots:
        if not search_root.is_dir():
            continue
        try:
            candidates = list(search_root.rglob("*")) if cfg.recursive else list(search_root.glob("*"))
        except PermissionError:
            continue

        for candidate in candidates:
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in _FILE_EXTENSIONS:
                continue
            if candidate in seen:
                continue

            rel = candidate.relative_to(root)
            if not _matches_patterns(rel, cfg.include_patterns, cfg.exclude_patterns):
                continue

            seen.add(candidate)
            try:
                stat = candidate.stat()
                file_hash = _fast_hash(candidate)
            except OSError:
                file_hash = ""

            title = candidate.stem.replace("-", " ").replace("_", " ").title()
            section = _determine_section(candidate, root)

            files.append(
                RepoFile(
                    relative_path=rel,
                    absolute_path=candidate,
                    title=title,
                    section=section,
                    last_modified=stat.st_mtime,
                    hash=file_hash,
                )
            )

    files.sort(key=lambda f: f.relative_path)
    return files


def convert_repository(
    path: str | Path,
    output_path: str | Path,
    config: RepositoryConfig | None = None,
) -> RepoResult:
    root = Path(path).resolve()
    out = Path(output_path).resolve()
    cfg = config or RepositoryConfig()

    files = collect_repo_files(root, cfg)
    if not files:
        return RepoResult(
            total_files=0,
            errors=[("", "No documentation files found")],
            output_path=str(out),
        )

    out.mkdir(parents=True, exist_ok=True)
    result = RepoResult(total_files=len(files), output_path=str(out))

    mode = cfg.output_mode
    if mode == "both":
        single_result = convert_repository_single(root, out / "merged", files, cfg)
        multi_result = convert_repository_multi(root, out / "pages", files, cfg)
        result.converted = single_result.converted + multi_result.converted
        result.skipped = single_result.skipped + multi_result.skipped
        result.failed = single_result.failed + multi_result.failed
        result.errors = single_result.errors + multi_result.errors
    elif mode == "single":
        single_path = out / f"{root.name}.{cfg.output_format}"
        result = convert_repository_single(root, single_path, files, cfg)
    else:
        result = convert_repository_multi(root, out, files, cfg)

    return result


def convert_repository_multi(
    input_dir: Path,
    output_dir: Path,
    files: list[RepoFile],
    config: RepositoryConfig,
) -> RepoResult:
    result = RepoResult(total_files=len(files), output_path=str(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    tracker: IncrementalBuildTracker | None = None
    if config.incremental:
        tracker = IncrementalBuildTracker(output_dir / ".pimd-build-state.json")

    errors: list[tuple[str, str]] = []
    converted = 0
    skipped = 0
    failed = 0

    if config.parallel_workers:
        work_items = [
            _MultiWorkItem(
                f, input_dir, output_dir, config, tracker,
            )
            for f in files
        ]

        max_workers = config.parallel_workers if config.parallel_workers > 0 else None
        p_results = parallel_map(
            _convert_multi_file,
            work_items,
            max_workers=max_workers,
        )

        for r in p_results:
            if r.success:
                data = r.data
                converted += data.get("converted", 0)
                skipped += data.get("skipped", 0)
                if data.get("error"):
                    failed += 1
                    errors.append(data["error"])
            else:
                failed += 1
                errors.append(("", r.error or "Unknown error"))
    else:
        for rf in files:
            out_path = _resolve_multi_output(input_dir, output_dir, rf, config)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            if _should_skip(rf, out_path, tracker):
                skipped += 1
                continue

            try:
                _convert_file(rf.absolute_path, out_path, config.output_format)
                converted += 1
                if tracker:
                    tracker.record_build(rf.absolute_path)
            except Exception as exc:
                failed += 1
                errors.append((str(rf.relative_path), str(exc)))

    result.converted = converted
    result.skipped = skipped
    result.failed = failed
    result.errors = errors
    return result


def convert_repository_single(
    input_dir: Path,
    output_path: Path,
    files: list[RepoFile],
    config: RepositoryConfig,
) -> RepoResult:
    result = RepoResult(total_files=len(files), output_path=str(output_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not files:
        return result

    input_paths: list[Path] = []
    skipped = 0

    for rf in files:
        if not rf.absolute_path.is_file():
            skipped += 1
            continue
        input_paths.append(rf.absolute_path)

    if not input_paths:
        result.skipped = skipped
        return result

    try:
        merger = DocumentMerger()
        fmt = ExportFormat(config.output_format) if config.output_format != "docx" else ExportFormat.DOCX
        merger.merge(input_paths, output_path, format=fmt)
        result.converted = len(input_paths)
        result.skipped = skipped
    except Exception as exc:
        result.failed = len(input_paths)
        result.errors = [(str(output_path), str(exc))]

    return result


def estimate_output_size(files: list[RepoFile]) -> str:
    total_bytes = 0
    for rf in files:
        try:
            total_bytes += rf.absolute_path.stat().st_size
        except OSError:
            pass

    total_bytes = max(total_bytes, 1)
    ratio = 3.5
    estimated = int(total_bytes * ratio)

    for threshold, unit in _HUMAN_UNITS:
        if estimated >= threshold:
            value = estimated / threshold
            if value >= 100:
                return f"{int(round(value))} {unit}"
            return f"{value:.1f} {unit}"
    return f"{estimated} B"


def build_section_index(files: list[RepoFile]) -> dict[str, list[RepoFile]]:
    index: dict[str, list[RepoFile]] = {}
    for rf in files:
        section = rf.section or "_root"
        if section not in index:
            index[section] = []
        index[section].append(rf)
    return dict(sorted(index.items()))


@dataclass
class _MultiWorkItem:
    file: RepoFile
    input_dir: Path
    output_dir: Path
    config: RepositoryConfig
    tracker: IncrementalBuildTracker | None


def _convert_multi_file(item: _MultiWorkItem) -> dict[str, Any]:
    out_path = _resolve_multi_output(item.input_dir, item.output_dir, item.file, item.config)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if _should_skip(item.file, out_path, item.tracker):
        return {"converted": 0, "skipped": 1}

    try:
        _convert_file(item.file.absolute_path, out_path, item.config.output_format)
        if item.tracker:
            item.tracker.record_build(item.file.absolute_path)
        return {"converted": 1, "skipped": 0}
    except Exception as exc:
        return {"converted": 0, "skipped": 0, "error": (str(item.file.relative_path), str(exc))}


def _resolve_multi_output(
    input_dir: Path,
    output_dir: Path,
    file: RepoFile,
    config: RepositoryConfig,
) -> Path:
    stem = file.absolute_path.stem
    ext = f".{config.output_format}"

    if config.preserve_structure:
        parts = file.relative_path.parent
        return output_dir / parts / f"{stem}{ext}"

    return output_dir / f"{stem}{ext}"


def _should_skip(
    file: RepoFile,
    output_path: Path,
    tracker: IncrementalBuildTracker | None,
) -> bool:
    if tracker is None:
        return False
    if not output_path.exists():
        return False
    return not tracker.needs_rebuild(file.absolute_path)


def _convert_file(source: Path, destination: Path, output_format: str) -> None:
    converter = ExportConverter()
    fmt = ExportFormat(output_format) if output_format != "docx" else ExportFormat.DOCX
    result = converter.convert(str(source), fmt, str(destination))
    if not result.success:
        raise RuntimeError(result.error or "Conversion failed")


def _find_config_files(root: Path) -> list[Path]:
    found: list[Path] = []
    try:
        for entry in root.iterdir():
            if entry.is_file() and entry.name in REPO_CONFIG_FILES:
                found.append(entry)
    except PermissionError:
        pass
    return found


def _count_doc_files(dirs: list[Path]) -> int:
    count = 0
    for d in dirs:
        try:
            for p in d.rglob("*"):
                if p.is_file() and p.suffix.lower() in _FILE_EXTENSIONS:
                    count += 1
        except PermissionError:
            continue
    return count


def _determine_section(file: Path, root: Path) -> str:
    try:
        rel = file.relative_to(root)
        parent = rel.parent
        if str(parent) == ".":
            return ""
        return str(parent.as_posix()).lower()
    except ValueError:
        return ""


def _matches_patterns(
    rel_path: Path,
    include: list[str],
    exclude: list[str],
) -> bool:
    rel_str = rel_path.as_posix().lower()

    if exclude:
        from fnmatch import fnmatch

        for pat in exclude:
            if fnmatch(rel_str, pat.lower()) or fnmatch(rel_path.name, pat.lower()):
                return False

    if include:
        from fnmatch import fnmatch

        for pat in include:
            if fnmatch(rel_str, pat.lower()) or fnmatch(rel_path.name, pat.lower()):
                return True

        return False

    return True


def _fast_hash(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


__all__ = [
    "RepoType",
    "DiscoveryResult",
    "RepositoryConfig",
    "RepoFile",
    "RepoResult",
    "discover_repository",
    "detect_repo_type",
    "find_docs_directories",
    "collect_repo_files",
    "convert_repository",
    "convert_repository_multi",
    "convert_repository_single",
    "estimate_output_size",
    "build_section_index",
]
