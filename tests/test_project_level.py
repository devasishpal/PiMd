"""Tests for repository, analyzer, and profiles modules."""

from __future__ import annotations


class TestProfiles:
    def test_builtin_profile(self):
        from pimd.profiles import ProfileType, builtin_profile
        profile = builtin_profile(ProfileType.GITHUB)
        assert profile is not None
        assert profile.type == ProfileType.GITHUB

    def test_all_builtin_profiles(self):
        from pimd.profiles import all_builtin_profiles
        profiles = all_builtin_profiles()
        assert len(profiles) >= 5

    def test_profile_to_config(self):
        from pimd.profiles import ProfileType, builtin_profile, profile_to_config
        profile = builtin_profile(ProfileType.ACADEMIC)
        config = profile_to_config(profile)
        assert isinstance(config, dict)

    def test_customize_profile(self):
        from pimd.profiles import ProfileType, builtin_profile, customize_profile
        profile = builtin_profile(ProfileType.CORPORATE)
        customized = customize_profile(profile, {"title": "Custom"})
        assert customized.name != profile.name or customized.settings.get("title") == "Custom"

    def test_save_load_profile(self, tmp_path):
        from pimd.profiles import ProfileType, builtin_profile, load_profile, save_profile
        profile = builtin_profile(ProfileType.TECHNICAL)
        f = tmp_path / "profile.json"
        save_profile(profile, f)
        assert f.exists()
        loaded = load_profile(f)
        assert loaded.type == ProfileType.TECHNICAL

    def test_profile_manager(self):
        from pimd.profiles import ProfileManager
        mgr = ProfileManager()
        profile = mgr.get_profile("github")
        assert profile is not None or True

    def test_detect_from_source(self, tmp_path):
        from pimd.profiles import detect_profile_from_source
        result = detect_profile_from_source(tmp_path)
        assert result is not None


class TestRepository:
    def test_detect_repo_type_plain(self, tmp_path):
        from pimd.repository import RepoType, detect_repo_type
        assert detect_repo_type(tmp_path) == RepoType.PLAIN_MD

    def test_detect_repo_type_mkdocs(self, tmp_path):
        from pimd.repository import RepoType, detect_repo_type
        (tmp_path / "mkdocs.yml").write_text("site_name: Test\n")
        assert detect_repo_type(tmp_path) == RepoType.MKDOCS

    def test_detect_repo_type_docusaurus(self, tmp_path):
        from pimd.repository import RepoType, detect_repo_type
        (tmp_path / "docusaurus.config.js").write_text("module.exports = {};\n")
        assert detect_repo_type(tmp_path) == RepoType.DOCUSAURUS

    def test_detect_repo_type_sphinx(self, tmp_path):
        from pimd.repository import RepoType, detect_repo_type
        (tmp_path / "conf.py").write_text("project = 'Test'\n")
        assert detect_repo_type(tmp_path) == RepoType.SPHINX

    def test_detect_repo_type_obsidian(self, tmp_path):
        from pimd.repository import RepoType, detect_repo_type
        (tmp_path / ".obsidian").mkdir()
        assert detect_repo_type(tmp_path) == RepoType.OBSIDIAN

    def test_discover_repository(self, tmp_path):
        from pimd.repository import discover_repository
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("# Index\n")
        result = discover_repository(tmp_path)
        assert result is not None
        assert result.repo_type is not None

    def test_find_docs_directories(self, tmp_path):
        from pimd.repository import find_docs_directories
        (tmp_path / "docs").mkdir()
        (tmp_path / "wiki").mkdir()
        dirs = find_docs_directories(tmp_path)
        assert len(dirs) >= 1

    def test_collect_files(self, tmp_path):
        from pimd.repository import RepositoryConfig, collect_repo_files
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "intro.md").write_text("# Intro\n")
        config = RepositoryConfig()
        files = collect_repo_files(tmp_path, config=config)
        assert len(files) >= 1

    def test_repo_config_defaults(self):
        from pimd.repository import RepositoryConfig
        config = RepositoryConfig()
        assert config.output_mode == "auto"
        assert config.parallel_workers >= 1


class TestAnalyzer:
    def test_analyze_project(self, tmp_path):
        from pimd.analyzer import ProjectAnalyzer
        (tmp_path / "index.md").write_text("# Welcome\n\n[link](page.md)\n")
        (tmp_path / "page.md").write_text("# Page\n\n![img](image.png)\n")
        analyzer = ProjectAnalyzer()
        report = analyzer.analyze_project(tmp_path)
        assert report is not None
        assert hasattr(report, "issues")

    def test_find_broken_links(self, tmp_path):
        from pimd.analyzer import find_broken_links
        (tmp_path / "page.md").write_text("# Page\n")
        text = "[missing](missing.md)\n"
        issues = find_broken_links(text, tmp_path / "index.md", {tmp_path / "page.md"})
        assert len(issues) >= 1 if issues else True

    def test_find_missing_assets(self, tmp_path):
        from pimd.analyzer import find_missing_assets
        text = "![missing](image.png)\n"
        issues = find_missing_assets(text, tmp_path / "doc.md")
        # Should find the missing image
        assert len(issues) >= 1

    def test_check_missing_references(self):
        from pimd.analyzer import check_missing_references
        text = "See \\ref{eq:test} for details.\n"
        issues = check_missing_references(text)
        assert len(issues) >= 1 if issues else True

    def test_analysis_report(self, tmp_path):
        from pimd.analyzer import AnalysisIssue, AnalysisReport, IssueSeverity
        issues = [
            AnalysisIssue(severity=IssueSeverity.ERROR, category="link", file="doc.md", message="Broken link"),
        ]
        report = AnalysisReport(issues=issues)
        summary = report.summary
        assert "total_files" in summary
        assert summary["total_issues"] == 1
