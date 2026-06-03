"""Tests for the PiMD configuration system."""

from pathlib import Path

import pytest

from pimd.cli.config import DEFAULT_CONFIG, get_config_path, load_config, write_default_config


class TestConfig:
    """Verify configuration loading and defaults."""

    def test_default_config_has_required_keys(self) -> None:
        assert "defaults" in DEFAULT_CONFIG
        assert "logging" in DEFAULT_CONFIG
        assert "theme" in DEFAULT_CONFIG["defaults"]

    def test_load_config_returns_dict(self) -> None:
        config = load_config()
        assert isinstance(config, dict)
        assert "defaults" in config
        assert "logging" in config

    def test_get_config_path_returns_path(self) -> None:
        path = get_config_path()
        assert isinstance(path, Path)
        assert path.name == "config.toml"
        assert ".pimd" in str(path)

    def test_write_default_config_creates_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.setattr("pimd.cli.config._CONFIG_DIR", tmp_path / ".pimd")
        monkeypatch.setattr("pimd.cli.config._CONFIG_PATH", tmp_path / ".pimd" / "config.toml")

        write_default_config()
        config_path = tmp_path / ".pimd" / "config.toml"
        assert config_path.exists()

        # Should not overwrite
        config_path.write_text("changed")
        write_default_config()
        assert config_path.read_text() == "changed"

    def test_load_config_from_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_dir = tmp_path / ".pimd"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('[defaults]\ntheme = "custom"\nauthor = "Test"\n')

        monkeypatch.setattr("pimd.cli.config._CONFIG_PATH", config_file)

        config = load_config()
        assert config["defaults"]["theme"] == "custom"
        assert config["defaults"]["author"] == "Test"
        # Other defaults should still be present
        assert "output_directory" in config["defaults"]
        assert "logging" in config
