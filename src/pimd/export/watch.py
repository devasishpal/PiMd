"""Watch mode — file system monitoring for automatic document rebuilds.

Usage::

    from pimd.export.watch import WatchMode

    watcher = WatchMode(patterns=["*.md", "*.html"])
    watcher.run("docs/")
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pimd.export.converter import ExportConverter

logger = logging.getLogger(__name__)


class WatchMode:
    """Monitor a directory for file changes and trigger automatic rebuilds.

    Implements a simple polling-based watcher (no external dependencies).
    For production use, install ``watchdog`` for event-driven file monitoring.
    """

    def __init__(
        self,
        patterns: list[str] | None = None,
        recursive: bool = True,
        poll_interval: float = 1.0,
        callback: Callable[[str, Path], None] | None = None,
        output_format: str = "docx",
        output_dir: str | None = None,
    ) -> None:
        self.patterns = patterns or ["*.md", "*.html", "*.htm"]
        self.recursive = recursive
        self.poll_interval = poll_interval
        self.callback = callback
        self.output_format = output_format
        self.output_dir = output_dir
        self._running = False
        self._snapshots: dict[Path, float] = {}

    def run(self, directory: str | Path, output_directory: str | Path | None = None) -> None:
        """Start watching a directory for changes.

        Blocks until interrupted (Ctrl+C).
        """
        root = Path(directory).resolve()
        out_dir: Path | None = None
        if output_directory:
            out_dir = Path(output_directory).resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
        elif self.output_dir:
            out_dir = Path(self.output_dir).resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = root.parent / f"{root.name}-output"
            out_dir.mkdir(parents=True, exist_ok=True)

        self._running = True
        logger.info("Watching %s for changes (patterns: %s)", root, self.patterns)
        logger.info("Output directory: %s", out_dir)
        logger.info("Press Ctrl+C to stop")
        print(f"Watching {root} for changes...")

        try:
            while self._running:
                self._check_once(root, out_dir)
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            self._running = False
            logger.info("Watch mode stopped")
            print("\nWatch mode stopped.")

    def _check_once(self, root: Path, output_dir: Path) -> None:
        from pimd.export.converter import ExportConverter

        files = self._discover_files(root)
        for file_path in files:
            current_mtime = file_path.stat().st_mtime
            if file_path not in self._snapshots:
                self._snapshots[file_path] = current_mtime
                continue

            if current_mtime > self._snapshots[file_path]:
                self._snapshots[file_path] = current_mtime
                rel = file_path.relative_to(root)
                out_path = output_dir / f"{file_path.stem}.{self.output_format}"
                print(f"Changed: {rel} -> Rebuilding...")
                try:
                    exporter = ExportConverter()
                    result = exporter.convert(
                        str(file_path),
                        self.output_format,
                        str(out_path),
                    )
                    if result.success:
                        print(f"  Done: {out_path}")
                    else:
                        print(f"  Failed: {result.error}")
                except Exception as exc:
                    print(f"  Error: {exc}")

                if self.callback:
                    self.callback(str(file_path), out_path)

    def _discover_files(self, root: Path) -> list[Path]:
        files: list[Path] = []
        if self.recursive:
            for pattern in self.patterns:
                files.extend(root.rglob(pattern))
        else:
            for pattern in self.patterns:
                files.extend(root.glob(pattern))
        return sorted(set(files))

    def stop(self) -> None:
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def use_watchdog(self, directory: str | Path) -> None:
        """Use the watchdog library for efficient event-driven monitoring.

        Falls back to polling if watchdog is not installed.
        """
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer

            class _Handler(FileSystemEventHandler):
                def __init__(self, watch_mode: WatchMode, output_dir: Path) -> None:
                    self.watch_mode = watch_mode
                    self.output_dir = output_dir
                    self._debounce: dict[str, float] = {}

                def on_modified(self, event: Any) -> None:
                    if event.is_directory:
                        return
                    src_path = Path(event.src_path)
                    if any(src_path.match(p) for p in self.watch_mode.patterns):
                        now = time.time()
                        last = self._debounce.get(event.src_path, 0)
                        if now - last < 0.5:
                            return
                        self._debounce[event.src_path] = now
                        out_path = self.output_dir / f"{src_path.stem}.{self.watch_mode.output_format}"
                        print(f"Changed: {src_path.name} -> Rebuilding...")
                        try:
                            exporter = ExportConverter()
                            result = exporter.convert(
                                str(src_path),
                                self.watch_mode.output_format,
                                str(out_path),
                            )
                            if result.success:
                                print(f"  Done: {out_path}")
                            else:
                                print(f"  Failed: {result.error}")
                        except Exception as exc:
                            print(f"  Error: {exc}")

            root = Path(directory).resolve()
            out_dir = root.parent / f"{root.name}-output"
            out_dir.mkdir(parents=True, exist_ok=True)

            event_handler = _Handler(self, out_dir)
            observer = Observer()
            observer.schedule(event_handler, str(root), recursive=self.recursive)
            observer.start()
            print(f"Watching {root} with watchdog...")
            try:
                while self._running:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()
        except ImportError:
            logger.info("watchdog not installed, falling back to polling")
            self.run(directory)
