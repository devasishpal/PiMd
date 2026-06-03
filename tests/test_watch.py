"""Tests for watch mode."""

from pathlib import Path

from pimd.export.watch import WatchMode


class TestWatchMode:
    def test_create_watch_mode_defaults(self) -> None:
        watcher = WatchMode()
        assert not watcher.is_running
        assert watcher.poll_interval == 1.0
        assert "*.md" in watcher.patterns

    def test_create_watch_mode_custom(self) -> None:
        watcher = WatchMode(patterns=["*.rst"], poll_interval=2.5)
        assert watcher.poll_interval == 2.5
        assert watcher.patterns == ["*.rst"]

    def test_discover_files_empty_directory(self, tmp_path: Path) -> None:
        watcher = WatchMode()
        files = watcher._discover_files(tmp_path)
        assert files == []

    def test_discover_files_with_markdown(self, tmp_path: Path) -> None:
        (tmp_path / "test.md").write_text("# Hello", encoding="utf-8")
        watcher = WatchMode()
        files = watcher._discover_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "test.md"

    def test_discover_files_recursive(self, tmp_path: Path) -> None:
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "deep.md").write_text("content", encoding="utf-8")
        watcher = WatchMode(recursive=True)
        files = watcher._discover_files(tmp_path)
        assert any("deep.md" in str(f) for f in files)

    def test_discover_files_non_recursive(self, tmp_path: Path) -> None:
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "deep.md").write_text("content", encoding="utf-8")
        watcher = WatchMode(recursive=False)
        files = watcher._discover_files(tmp_path)
        assert all("deep.md" not in str(f) for f in files)

    def test_stop(self) -> None:
        watcher = WatchMode()
        assert not watcher.is_running
        watcher.stop()
        assert not watcher.is_running

    def test_check_once_no_changes(self, tmp_path: Path) -> None:
        watcher = WatchMode()
        (tmp_path / "test.md").write_text("hello", encoding="utf-8")
        output = tmp_path / "output"
        output.mkdir()
        watcher._check_once(tmp_path, output)
        # First run should snapshot, no rebuild
        watcher._check_once(tmp_path, output)
        # No changes, should still work silently

    def test_snapshot_updates(self, tmp_path: Path) -> None:
        watcher = WatchMode()
        test_file = tmp_path / "test.md"
        test_file.write_text("v1", encoding="utf-8")
        output = tmp_path / "output"
        output.mkdir()
        watcher._check_once(tmp_path, output)
        assert test_file in watcher._snapshots
