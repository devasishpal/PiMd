"""Enterprise safety — configurable limits, guards, path validation, and input sanitization."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pimd.exceptions import PiMDError


class SafetyError(PiMDError):
    """Raised when a safety limit is exceeded."""


class PathTraversalError(SafetyError):
    """Raised when a path traversal attempt is detected."""


class MalformedInputError(SafetyError):
    """Raised when input appears malformed or malicious."""


class ResourceExhaustionError(SafetyError):
    """Raised when resource limits are exceeded."""


@dataclass
class SafetyLimits:
    """Configurable safety limits for the conversion pipeline.

    Attributes:
        max_input_size: Maximum input text size in bytes (default 100 MB).
        max_file_size: Maximum input file size in bytes (default 500 MB).
        max_nesting_depth: Maximum block nesting depth (default 100).
        max_document_blocks: Maximum blocks in a single document (default 100 000).
        max_list_items: Maximum items in a single list (default 10 000).
        max_table_rows: Maximum rows in a single table (default 10 000).
        max_table_cols: Maximum columns in a single table (default 100).
        max_image_size: Maximum image file size in bytes (default 10 MB).
        max_recursion_depth: Maximum recursion depth (default 1000).
        max_url_length: Maximum URL length in characters (default 2048).
        allowed_tags: Allowed HTML tags (empty = all allowed).
        blocked_tags: Blocked HTML tags.
        blocked_paths: List of blocked path patterns (glob).
        allowed_schemes: Allowed URL schemes for images/links.
    """

    max_input_size: int = 100 * 1024 * 1024
    max_file_size: int = 500 * 1024 * 1024
    max_nesting_depth: int = 100
    max_document_blocks: int = 100_000
    max_list_items: int = 10_000
    max_table_rows: int = 10_000
    max_table_cols: int = 100
    max_image_size: int = 10 * 1024 * 1024
    max_recursion_depth: int = 1000
    max_url_length: int = 2048
    allowed_tags: list[str] = field(default_factory=list)
    blocked_tags: list[str] = field(default_factory=list)
    blocked_paths: list[str] = field(
        default_factory=lambda: ["/etc", "/proc", "/sys", "C:\\Windows"]
    )
    allowed_schemes: list[str] = field(default_factory=lambda: ["http", "https", "ftp", "file"])

    @classmethod
    def permissive(cls) -> SafetyLimits:
        return cls(
            max_input_size=500 * 1024 * 1024,
            max_file_size=1024 * 1024 * 1024,
            max_nesting_depth=500,
            max_document_blocks=500_000,
            max_recursion_depth=5000,
        )

    @classmethod
    def strict(cls) -> SafetyLimits:
        return cls(
            max_input_size=10 * 1024 * 1024,
            max_file_size=50 * 1024 * 1024,
            max_nesting_depth=20,
            max_document_blocks=10_000,
            max_list_items=1000,
            max_table_rows=500,
            max_image_size=2 * 1024 * 1024,
            max_recursion_depth=100,
        )


class SafetyGuard:
    """Check input data against safety limits before processing."""

    _PATH_TRAVERSAL_RE = re.compile(r"(\.\./|\.\.\\)")
    _NULL_BYTE_RE = re.compile(r"\x00")
    _CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

    def __init__(self, limits: SafetyLimits | None = None) -> None:
        self._limits = limits or SafetyLimits()

    @property
    def limits(self) -> SafetyLimits:
        return self._limits

    def check_text_size(self, text: str) -> None:
        size = len(text.encode("utf-8"))
        if size > self._limits.max_input_size:
            raise SafetyError(
                f"Input text exceeds safety limit: "
                f"{_fmt_size(size)} > {_fmt_size(self._limits.max_input_size)}"
            )

    def check_file_size(self, path: str | Path) -> None:
        size = Path(path).stat().st_size
        if size > self._limits.max_file_size:
            raise SafetyError(
                f"Input file exceeds safety limit: "
                f"{_fmt_size(size)} > {_fmt_size(self._limits.max_file_size)}"
            )

    def check_nesting_depth(self, depth: int) -> None:
        if depth > self._limits.max_nesting_depth:
            raise SafetyError(
                f"Nesting depth {depth} exceeds limit of {self._limits.max_nesting_depth}"
            )

    def check_block_count(self, count: int) -> None:
        if count > self._limits.max_document_blocks:
            raise SafetyError(
                f"Document block count {count} exceeds limit of {self._limits.max_document_blocks}"
            )

    def check_image_size(self, size: int) -> None:
        if size > self._limits.max_image_size:
            limit_str = _fmt_size(self._limits.max_image_size)
            raise SafetyError(f"Image size {_fmt_size(size)} exceeds limit of {limit_str}")

    def check_recursion_depth(self, depth: int) -> None:
        if depth > self._limits.max_recursion_depth:
            raise SafetyError(
                f"Recursion depth {depth} exceeds limit of {self._limits.max_recursion_depth}"
            )

    def check_path_traversal(self, path: str | Path) -> str:
        """Detect and block path traversal attempts.

        Raises PathTraversalError if traversal detected.
        Returns the resolved absolute path on success.
        """
        p = Path(path)
        if self._PATH_TRAVERSAL_RE.search(str(p)):
            raise PathTraversalError(f"Path traversal detected: {path}")
        try:
            resolved = p.resolve(strict=False)
        except (OSError, RuntimeError):
            raise PathTraversalError(f"Cannot resolve path: {path}") from None
        resolved_str = str(resolved)
        for blocked in self._limits.blocked_paths:
            if resolved_str.startswith(blocked):
                raise PathTraversalError(f"Path is blocked: {path} (resolves to {resolved_str})")
        return resolved_str

    def check_path_allowed(self, path: str | Path, base_dir: str | Path | None = None) -> str:
        """Verify a path is within an allowed base directory."""
        resolved = Path(path).resolve()
        if base_dir:
            base = Path(base_dir).resolve()
            try:
                resolved.relative_to(base)
            except ValueError:
                raise PathTraversalError(
                    f"Path {path} is outside allowed base directory {base_dir}"
                ) from None
        return str(resolved)

    def check_malformed_input(self, text: str) -> None:
        """Check for null bytes, excessive control characters, or other red flags."""
        if self._NULL_BYTE_RE.search(text):
            raise MalformedInputError("Input contains null bytes — possible attack")
        control_count = len(self._CONTROL_CHARS_RE.findall(text))
        total = len(text)
        if total > 0 and control_count / total > 0.1:
            raise MalformedInputError(
                f"Input contains {control_count}/{total} control characters — possible attack"
            )
        if len(text) > 10_000_000:
            self.check_text_size(text)

    def check_url_safe(self, url: str) -> None:
        """Verify URL scheme and length."""
        if len(url) > self._limits.max_url_length:
            raise SafetyError(
                f"URL exceeds maximum length ({len(url)} > {self._limits.max_url_length})"
            )
        if ":" in url:
            scheme = url.split(":", 1)[0].lower()
            if scheme not in self._limits.allowed_schemes:
                raise SafetyError(f"URL scheme '{scheme}' is not allowed")

    def validate_all(self, text: str | None = None, path: str | Path | None = None) -> list[str]:
        """Run all applicable checks. Returns list of error messages (empty = all passed)."""
        errors: list[str] = []
        if text is not None:
            try:
                self.check_text_size(text)
                self.check_malformed_input(text)
            except PiMDError as exc:
                errors.append(str(exc))
        if path is not None:
            try:
                self.check_file_size(path)
                self.check_path_traversal(path)
            except PiMDError as exc:
                errors.append(str(exc))
        return errors

    def wrap(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)


def _fmt_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
