from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

__all__ = [
    "IssueSeverity",
    "AnalysisIssue",
    "AnalysisReport",
    "ProjectAnalyzer",
    "analyze_project",
    "find_broken_links",
    "find_missing_assets",
    "find_duplicate_pages",
    "find_unused_files",
    "find_orphaned_assets",
    "check_missing_references",
]


class IssueSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class AnalysisIssue:
    severity: IssueSeverity
    category: str
    file: str | None = None
    line: int | None = None
    message: str = ""
    suggestion: str | None = None


@dataclass
class AnalysisReport:
    issues: list[AnalysisIssue] = field(default_factory=list)
    total_files: int = 0
    total_issues: int = 0

    def __post_init__(self) -> None:
        if self.total_issues == 0 and self.issues:
            self.total_issues = len(self.issues)

    @property
    def by_category(self) -> dict[str, list[AnalysisIssue]]:
        result: dict[str, list[AnalysisIssue]] = {}
        for issue in self.issues:
            result.setdefault(issue.category, []).append(issue)
        return result

    @property
    def by_severity(self) -> dict[IssueSeverity, list[AnalysisIssue]]:
        result: dict[IssueSeverity, list[AnalysisIssue]] = {}
        for issue in self.issues:
            result.setdefault(issue.severity, []).append(issue)
        return result

    @property
    def summary(self) -> dict[str, int]:
        return {
            "total_files": self.total_files,
            "total_issues": self.total_issues,
            "errors": len(self.by_severity.get(IssueSeverity.ERROR, [])),
            "warnings": len(self.by_severity.get(IssueSeverity.WARNING, [])),
            "info": len(self.by_severity.get(IssueSeverity.INFO, [])),
        }


@dataclass
class ProjectAnalyzer:
    max_issues: int = 0
    check_categories: tuple[str, ...] = (
        "broken_links",
        "missing_assets",
        "missing_references",
        "duplicate_pages",
        "unused_files",
        "orphaned_assets",
    )
    output_format: str = "text"

    def analyze(self, path: str | Path) -> AnalysisReport:
        return analyze_project(path, self)

    def analyze_project(self, path: str | Path) -> AnalysisReport:
        return analyze_project(path, self)


LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
REF_RE = re.compile(r"\\ref\{([^}]+)\}")
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
ASSET_RE = re.compile(r"(?:src|href)=[\"']([^\"']+)[\"']")


def find_broken_links(
    text: str, source_path: Path, all_files: set[Path]
) -> list[AnalysisIssue]:
    issues: list[AnalysisIssue] = []
    for match in LINK_RE.finditer(text):
        target = match.group(2)
        if target.startswith(("http://", "https://", "#")):
            continue
        resolved = source_path.parent / target
        if not resolved.exists():
            issues.append(
                AnalysisIssue(
                    severity=IssueSeverity.ERROR,
                    category="broken_links",
                    file=str(source_path),
                    message=f"Broken link: {target}",
                    suggestion=f"Ensure {target} exists at {resolved}",
                )
            )
    return issues


def find_missing_assets(
    text: str, source_path: Path
) -> list[AnalysisIssue]:
    issues: list[AnalysisIssue] = []
    for match in IMAGE_RE.finditer(text):
        asset_path = match.group(2)
        if asset_path.startswith(("http://", "https://")):
            continue
        resolved = source_path.parent / asset_path
        if not resolved.exists():
            issues.append(
                AnalysisIssue(
                    severity=IssueSeverity.WARNING,
                    category="missing_assets",
                    file=str(source_path),
                    message=f"Missing asset: {asset_path}",
                    suggestion=f"Place {asset_path} at {resolved}",
                )
            )
    return issues


def check_missing_references(text: str) -> list[AnalysisIssue]:
    labels = set(LABEL_RE.findall(text))
    issues: list[AnalysisIssue] = []
    for match in REF_RE.finditer(text):
        ref = match.group(1)
        if ref not in labels:
            issues.append(
                AnalysisIssue(
                    severity=IssueSeverity.WARNING,
                    category="missing_references",
                    message=f"Reference to undefined label: \\ref{{{ref}}}",
                    suggestion=f"Add \\label{{{ref}}} to the corresponding element",
                )
            )
    return issues


def find_duplicate_pages(files: list[Path]) -> list[AnalysisIssue]:
    seen: dict[str, list[Path]] = {}
    for fp in files:
        if fp.suffix not in (".md", ".pimd"):
            continue
        title = fp.stem.lower().replace("-", " ").replace("_", " ")
        seen.setdefault(title, []).append(fp)

    issues: list[AnalysisIssue] = []
    for title, paths in seen.items():
        if len(paths) > 1:
            issues.append(
                AnalysisIssue(
                    severity=IssueSeverity.WARNING,
                    category="duplicate_pages",
                    message=f"Duplicate page title/slug: {title!r}",
                    suggestion=f"Rename or merge: {', '.join(str(p) for p in paths)}",
                )
            )
    return issues


def find_unused_files(
    files: list[Path], linked_files: set[Path]
) -> list[AnalysisIssue]:
    issues: list[AnalysisIssue] = []
    for fp in files:
        if fp.suffix not in (".md", ".pimd"):
            continue
        if fp not in linked_files:
            issues.append(
                AnalysisIssue(
                    severity=IssueSeverity.INFO,
                    category="unused_files",
                    file=str(fp),
                    message=f"File not linked from any index or TOC: {fp.name}",
                    suggestion=f"Add a link to {fp.name} from an index page or remove it",
                )
            )
    return issues


def find_orphaned_assets(
    asset_dir: Path, referenced: set[str]
) -> list[AnalysisIssue]:
    issues: list[AnalysisIssue] = []
    if not asset_dir.is_dir():
        return issues
    for fp in asset_dir.rglob("*"):
        if not fp.is_file():
            continue
        relative = fp.relative_to(asset_dir.parent if asset_dir.parent else asset_dir)
        if str(relative) not in referenced and str(fp.name) not in referenced:
            issues.append(
                AnalysisIssue(
                    severity=IssueSeverity.INFO,
                    category="orphaned_assets",
                    file=str(fp),
                    message=f"Orphaned asset not referenced anywhere: {fp.name}",
                    suggestion=f"Remove {fp.name} or add a reference to it",
                )
            )
    return issues


def analyze_project(
    path: str | Path, analyzer: ProjectAnalyzer | None = None
) -> AnalysisReport:
    root = Path(path).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory")

    cfg = analyzer or ProjectAnalyzer()

    all_files: list[Path] = list(root.rglob("*"))
    md_files: list[Path] = [f for f in all_files if f.is_file() and f.suffix in (".md", ".pimd")]
    linked_files: set[Path] = set()
    referenced_assets: set[str] = set()
    asset_dir = root / "assets"

    issues: list[AnalysisIssue] = []

    for md in md_files:
        text = md.read_text(encoding="utf-8", errors="replace")

        if "broken_links" in cfg.check_categories:
            issues.extend(find_broken_links(text, md, set(md_files)))
            for link in LINK_RE.finditer(text):
                target = link.group(2)
                resolved = (md.parent / target).resolve()
                if resolved.exists() and resolved.suffix in (".md", ".pimd"):
                    linked_files.add(resolved)

        if "missing_assets" in cfg.check_categories:
            issues.extend(find_missing_assets(text, md))
            for asset in IMAGE_RE.finditer(text):
                path_str = asset.group(2)
                if not path_str.startswith(("http://", "https://")):
                    referenced_assets.add(path_str)
            for a in ASSET_RE.finditer(text):
                val = a.group(1)
                if not val.startswith(("http://", "https://", "#")):
                    referenced_assets.add(val)

        if "missing_references" in cfg.check_categories:
            issues.extend(check_missing_references(text))

    if "duplicate_pages" in cfg.check_categories:
        issues.extend(find_duplicate_pages(md_files))

    if "unused_files" in cfg.check_categories:
        issues.extend(find_unused_files(md_files, linked_files))

    if "orphaned_assets" in cfg.check_categories:
        issues.extend(find_orphaned_assets(asset_dir, referenced_assets))

    if cfg.max_issues > 0:
        issues = issues[: cfg.max_issues]

    total_src = sum(
        1 for f in all_files if f.is_file() and f.suffix in (".md", ".pimd", ".html", ".css", ".js")
    )

    return AnalysisReport(issues=issues, total_files=total_src, total_issues=len(issues))
