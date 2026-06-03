"""Extended tests for the PiMD configuration system."""

from __future__ import annotations

from pathlib import Path

import pytest

from pimd.config import (
    BUILTIN_DEFAULTS,
    CONFIG_SCHEMA,
    Config,
    ConfigSchemaEntry,
    config_to_toml,
)


class TestConfigSchemaEntry:
    def test_create_with_required_fields(self) -> None:
        entry = ConfigSchemaEntry(type=str, default="Hello", description="A greeting")
        assert entry.type is str
        assert entry.default == "Hello"
        assert entry.description == "A greeting"
        assert entry.required is False
        assert entry.env_var is None

    def test_create_with_all_fields(self) -> None:
        entry = ConfigSchemaEntry(
            type=bool,
            default=True,
            description="Enable feature",
            required=True,
            env_var="PIMD_FEATURE_ENABLED",
        )
        assert entry.type is bool
        assert entry.required is True
        assert entry.env_var == "PIMD_FEATURE_ENABLED"


class TestConfigSchema:
    def test_has_expected_sections(self) -> None:
        sections = {k.split(".")[0] for k in CONFIG_SCHEMA}
        for expected in ["defaults", "conversion", "export", "security", "cache", "logging", "layout", "diagram"]:
            assert expected in sections

    def test_each_entry_has_type_and_default(self) -> None:
        for key, entry in CONFIG_SCHEMA.items():
            assert isinstance(key, str)
            assert isinstance(entry.type, type)
            assert "description" in entry.__dict__

    def test_some_entries_have_env_vars(self) -> None:
        env_vars = [e.env_var for e in CONFIG_SCHEMA.values() if e.env_var]
        assert len(env_vars) > 0
        assert "PIMD_DEFAULTS_THEME" in env_vars
        assert "PIMD_CACHE_ENABLED" in env_vars


class TestBuiltinDefaults:
    def test_is_dict_with_sections(self) -> None:
        assert isinstance(BUILTIN_DEFAULTS, dict)
        assert "defaults" in BUILTIN_DEFAULTS
        assert "conversion" in BUILTIN_DEFAULTS

    def test_theme_default(self) -> None:
        assert BUILTIN_DEFAULTS["defaults"]["theme"] == "professional"

    def test_default_format(self) -> None:
        assert BUILTIN_DEFAULTS["export"]["default_format"] == "docx"

    def test_cache_enabled(self) -> None:
        assert BUILTIN_DEFAULTS["cache"]["enabled"] is True


class TestConfigLoad:
    def test_load_global_nonexistent_path(self) -> None:
        cfg = Config()
        result = cfg.load_global("/nonexistent/path/config.toml")
        assert result is cfg

    def test_load_global_existent_path(self, tmp_path: Path) -> None:
        cfg = Config()
        config_file = tmp_path / "config.toml"
        config_file.write_text('[defaults]\ntheme = "dark"\n', encoding="utf-8")
        cfg.load_global(config_file)
        resolved = cfg.resolve()
        assert resolved["defaults"]["theme"] == "dark"

    def test_load_project_nonexistent_dir(self) -> None:
        cfg = Config()
        result = cfg.load_project("/nonexistent/dir")
        assert result is cfg

    def test_load_project_with_config(self, tmp_path: Path) -> None:
        cfg = Config()
        config_file = tmp_path / ".pimdconfig"
        config_file.write_text('[defaults]\nauthor = "ProjectAuthor"\n', encoding="utf-8")
        cfg.load_project(tmp_path)
        resolved = cfg.resolve()
        assert resolved["defaults"]["author"] == "ProjectAuthor"

    def test_load_project_legacy_config(self, tmp_path: Path) -> None:
        cfg = Config()
        config_file = tmp_path / "pimd.toml"
        config_file.write_text('[defaults]\ntheme = "legacy"\n', encoding="utf-8")
        cfg.load_project(tmp_path)
        resolved = cfg.resolve()
        assert resolved["defaults"]["theme"] == "legacy"

    def test_apply_runtime(self) -> None:
        cfg = Config()
        cfg.apply_runtime({"defaults": {"author": "RuntimeAuthor"}})
        resolved = cfg.resolve()
        assert resolved["defaults"]["author"] == "RuntimeAuthor"

    def test_priority_runtime_overrides_project(self, tmp_path: Path) -> None:
        cfg = Config()
        config_file = tmp_path / ".pimdconfig"
        config_file.write_text('[defaults]\ntheme = "project-theme"\n', encoding="utf-8")
        cfg.load_project(tmp_path)
        cfg.apply_runtime({"defaults": {"theme": "runtime-theme"}})
        resolved = cfg.resolve()
        assert resolved["defaults"]["theme"] == "runtime-theme"

    def test_priority_project_overrides_global(self, tmp_path: Path) -> None:
        cfg = Config()
        global_file = tmp_path / "global.toml"
        global_file.write_text('[defaults]\ntheme = "global-theme"\n', encoding="utf-8")
        project_file = tmp_path / ".pimdconfig"
        project_file.write_text('[defaults]\ntheme = "project-theme"\n', encoding="utf-8")
        cfg.load_global(global_file)
        cfg.load_project(tmp_path)
        resolved = cfg.resolve()
        assert resolved["defaults"]["theme"] == "project-theme"

    def test_apply_runtime_empty_does_nothing(self) -> None:
        cfg = Config()
        original = cfg.resolve()
        cfg.apply_runtime({})
        assert cfg.resolve() == original


class TestConfigGet:
    def test_get_simple_key(self, tmp_path: Path) -> None:
        cfg = Config()
        cfg.apply_runtime({"defaults": {"theme": "dark"}})
        assert cfg.get("defaults.theme") == "dark"

    def test_get_with_default(self) -> None:
        cfg = Config()
        assert cfg.get("nonexistent.key", "fallback") == "fallback"

    def test_get_missing_no_default(self) -> None:
        cfg = Config()
        assert cfg.get("does.not.exist") is None

    def test_get_from_builtin_defaults(self) -> None:
        cfg = Config()
        assert cfg.get("defaults.theme") == "professional"

    def test_get_nested_key(self) -> None:
        cfg = Config()
        val = cfg.get("security.max_input_size_mb")
        assert val == 100

    def test_get_after_resolve(self) -> None:
        cfg = Config()
        cfg.apply_runtime({"defaults": {"author": "TestAuthor"}})
        assert cfg.get("defaults.author") == "TestAuthor"


class TestConfigApplyEnv:
    def test_apply_env_sets_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIMD_DEFAULTS_THEME", "env-theme")
        cfg = Config()
        cfg.apply_env()
        assert cfg.get("defaults.theme") == "env-theme"

    def test_apply_env_sets_bool(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIMD_CACHE_ENABLED", "false")
        cfg = Config()
        cfg.apply_env()
        assert cfg.get("cache.enabled") is False

    def test_apply_env_sets_int(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIMD_SECURITY_MAX_INPUT_SIZE_MB", "200")
        cfg = Config()
        cfg.apply_env()
        assert cfg.get("security.max_input_size_mb") == 200

    def test_apply_env_no_env_vars(self) -> None:
        cfg = Config()
        before = cfg.resolve()
        cfg.apply_env()
        assert cfg.resolve() == before

    def test_apply_env_priority_over_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIMD_DEFAULTS_THEME", "env-theme")
        cfg = Config()
        config_file = tmp_path / ".pimdconfig"
        config_file.write_text('[defaults]\ntheme = "project-theme"\n', encoding="utf-8")
        cfg.load_project(tmp_path)
        cfg.apply_env()
        assert cfg.get("defaults.theme") == "env-theme"


class TestConfigValidate:
    def test_validate_passes_on_default_config(self) -> None:
        cfg = Config()
        errors = cfg.validate()
        assert errors == []

    def test_validate_detects_type_mismatch(self) -> None:
        cfg = Config()
        cfg.apply_runtime({"defaults": {"theme": 42}})
        errors = cfg.validate()
        assert len(errors) >= 1
        assert any("theme" in e for e in errors)

    def test_validate_multiple_errors(self) -> None:
        cfg = Config()
        cfg.apply_runtime({
            "defaults": {"theme": 42, "author": True},
        })
        errors = cfg.validate()
        assert len(errors) >= 2


class TestConfigGenerateDefault:
    def test_generate_default_returns_dict(self) -> None:
        defaults = Config.generate_default()
        assert isinstance(defaults, dict)
        assert "defaults" in defaults
        assert "conversion" in defaults
        assert "export" in defaults
        assert "security" in defaults
        assert "cache" in defaults
        assert "logging" in defaults
        assert "layout" in defaults
        assert "diagram" in defaults

    def test_generate_default_values_match_schema(self) -> None:
        defaults = Config.generate_default()
        assert defaults["defaults"]["theme"] == "professional"
        assert defaults["cache"]["enabled"] is True
        assert defaults["conversion"]["page_numbers"] is False


class TestConfigWriteDefault:
    def test_write_default_creates_file(self, tmp_path: Path) -> None:
        dest = tmp_path / ".pimdconfig"
        result = Config.write_default(dest)
        assert result == dest
        assert dest.exists()
        content = dest.read_text(encoding="utf-8")
        assert "[defaults]" in content
        assert "theme" in content

    def test_write_default_does_not_overwrite(self, tmp_path: Path) -> None:
        dest = tmp_path / ".pimdconfig"
        dest.write_text("already here", encoding="utf-8")
        Config.write_default(dest)
        assert dest.read_text(encoding="utf-8") == "already here"

    def test_write_default_creates_parent_dirs(self, tmp_path: Path) -> None:
        dest = tmp_path / "a" / "b" / "config.toml"
        assert not dest.parent.exists()
        Config.write_default(dest)
        assert dest.exists()


class TestConfigToToml:
    def test_serializes_sections(self) -> None:
        config = {"defaults": {"theme": "dark", "author": "me"}}
        toml = config_to_toml(config)
        assert "[defaults]" in toml
        assert 'theme = "dark"' in toml
        assert 'author = "me"' in toml

    def test_serializes_bool(self) -> None:
        config = {"features": {"enabled": True, "visible": False}}
        toml = config_to_toml(config)
        assert "true" in toml
        assert "false" in toml

    def test_serializes_int(self) -> None:
        config = {"limits": {"max_size": 100}}
        toml = config_to_toml(config)
        assert "max_size = 100" in toml

    def test_serializes_list(self) -> None:
        config = {"security": {"allowed_paths": ["/a", "/b"]}}
        toml = config_to_toml(config)
        assert '/a' in toml
        assert '/b' in toml

    def test_with_header(self) -> None:
        toml = config_to_toml({"x": {"y": 1}}, header="# PiMD Config")
        assert "# PiMD Config" in toml

    def test_flat_keys(self) -> None:
        config = {"key": "value"}
        toml = config_to_toml(config)
        assert 'key = "value"' in toml


class TestConfigFindConfigFiles:
    def test_returns_empty_list_when_no_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = Config()
        monkeypatch.setattr("pathlib.Path.exists", lambda *args, **kwargs: False)
        files = cfg.find_config_files()
        assert files == []

    def test_find_config_files_with_user_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        user_config = tmp_path / ".pimd" / "config.toml"
        user_config.parent.mkdir(parents=True)
        user_config.write_text("", encoding="utf-8")
        monkeypatch.setattr("pimd.config._USER_CONFIG_PATH", user_config)
        cfg = Config()
        files = cfg.find_config_files()
        assert user_config in files

    def test_resolve_returns_builtin_defaults_when_no_sources(self) -> None:
        cfg = Config()
        resolved = cfg.resolve()
        assert resolved["defaults"]["theme"] == "professional"


class TestConfigDeepMerge:
    def test_deep_merge_nested(self) -> None:
        cfg = Config()
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": {"b": 99, "d": 3}}
        cfg._deep_merge(base, override)
        assert base["a"]["b"] == 99
        assert base["a"]["c"] == 2
        assert base["a"]["d"] == 3

    def test_deep_merge_overwrites_non_dict(self) -> None:
        cfg = Config()
        base = {"a": "old"}
        override = {"a": "new"}
        cfg._deep_merge(base, override)
        assert base["a"] == "new"
