"""Incremental builds — hash tracking, file tracking, avoid unnecessary reconversion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BuildState:
    """Captured state of a file at build time."""

    path: str
    mtime: float
    size: int
    sha256: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_file(path: str | Path) -> BuildState:
        p = Path(path)
        stat = p.stat()
        return BuildState(
            path=str(p),
            mtime=stat.st_mtime,
            size=stat.st_size,
            sha256=_fast_hash(p),
        )

    def matches(self, other: BuildState) -> bool:
        return self.mtime == other.mtime and self.size == other.size and self.sha256 == other.sha256


def _fast_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class IncrementalBuildTracker:
    """Track file states to detect changes and avoid unnecessary reconversion.

    State is persisted to a JSON file in the output directory.
    """

    def __init__(self, state_file: str | Path | None = None) -> None:
        self._state_file = Path(state_file) if state_file else Path(".pimd-build-state.json")
        self._states: dict[str, BuildState] = {}
        self._load()

    def _load(self) -> None:
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                for key, val in data.items():
                    self._states[key] = BuildState(**val)
            except (json.JSONDecodeError, KeyError, TypeError):
                self._states = {}

    def _save(self) -> None:
        data = {k: v.__dict__ for k, v in self._states.items()}
        self._state_file.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def is_changed(self, path: str | Path) -> bool:
        """Check if a file has changed since the last build."""
        p = Path(path)
        if not p.exists():
            return True
        try:
            current = BuildState.from_file(p)
            key = str(p)
            if key not in self._states:
                return True
            return not current.matches(self._states[key])
        except (OSError, PermissionError):
            return True

    def record_build(self, path: str | Path, metadata: dict[str, Any] | None = None) -> None:
        """Record a file state after a successful build."""
        try:
            state = BuildState.from_file(path)
            if metadata:
                state.metadata.update(metadata)
            self._states[str(path)] = state
            self._save()
        except (OSError, PermissionError):
            pass

    def needs_rebuild(self, path: str | Path) -> bool:
        """Convenience: returns True if the file is new or changed."""
        return self.is_changed(path)

    def clear(self) -> None:
        """Clear all tracked states."""
        self._states.clear()
        if self._state_file.exists():
            self._state_file.unlink()

    def get_state(self, path: str | Path) -> BuildState | None:
        return self._states.get(str(path))

    def list_tracked(self) -> list[str]:
        return list(self._states.keys())

    def remove_stale(self, existing_paths: set[str]) -> int:
        """Remove states for files that no longer exist."""
        stale = [k for k in self._states if k not in existing_paths]
        for k in stale:
            del self._states[k]
        if stale:
            self._save()
        return len(stale)
