"""Tests for pimd.security — SVG sanitization, plugin verification, secrets scanning."""

from __future__ import annotations

from pathlib import Path

from pimd.security import (
    SafeSubprocess,
    safe_temp_dir,
    sanitize_svg,
    sanitize_svg_file,
    scan_for_secrets,
    verify_plugin_hash,
    verify_toml_manifest,
)


class TestSecurity:
    def test_sanitize_svg_strips_scripts(self) -> None:
        dirty = '<svg><script>alert("xss")</script><rect width="100" height="100"/></svg>'
        clean = sanitize_svg(dirty)
        assert "<script>" not in clean
        assert "<rect" in clean

    def test_sanitize_svg_strips_event_handlers(self) -> None:
        dirty = '<svg><rect onload="evil()" width="100" height="100"/></svg>'
        clean = sanitize_svg(dirty)
        assert "onload" not in clean

    def test_sanitize_svg_strips_javascript(self) -> None:
        dirty = '<svg><a href="javascript:alert(1)">click</a></svg>'
        clean = sanitize_svg(dirty)
        assert "javascript:" not in clean

    def test_sanitize_svg_adds_csp(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
        result = sanitize_svg(svg, add_csp=True)
        assert "content-security-policy" in result

    def test_sanitize_svg_skips_csp(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
        result = sanitize_svg(svg, add_csp=False)
        assert "content-security-policy" not in result

    def test_sanitize_svg_file_returns_false_if_missing(self) -> None:
        assert sanitize_svg_file("/nonexistent/file.svg") is False

    def test_sanitize_svg_file_modifies_file(self, tmp_path: Path) -> None:
        p = tmp_path / "test.svg"
        p.write_text('<svg><script>alert(1)</script></svg>', encoding="utf-8")
        modified = sanitize_svg_file(p)
        assert modified is True
        content = p.read_text(encoding="utf-8")
        assert "<script>" not in content

    def test_verify_plugin_hash_missing_file(self) -> None:
        assert verify_plugin_hash("/nonexistent", "abc") is False

    def test_verify_plugin_hash_valid(self, tmp_path: Path) -> None:
        import hashlib

        p = tmp_path / "plugin.py"
        p.write_text("# test plugin", encoding="utf-8")
        expected = hashlib.sha256(p.read_bytes()).hexdigest()
        assert verify_plugin_hash(p, expected) is True

    def test_verify_toml_manifest_missing(self) -> None:
        result = verify_toml_manifest("/nonexistent/manifest.toml")
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_verify_toml_manifest_valid(self, tmp_path: Path) -> None:
        p = tmp_path / "plugin.toml"
        p.write_text(
            '[plugin]\nname = "test-plugin"\nversion = "1.0"\ncapabilities = ["renderer:mermaid"]',
            encoding="utf-8",
        )
        result = verify_toml_manifest(p)
        assert result["valid"] is True
        assert result["manifest"]["plugin"]["name"] == "test-plugin"

    def test_safe_subprocess_creates(self) -> None:
        runner = SafeSubprocess(timeout=10)
        assert runner._timeout == 10

    def test_safe_temp_dir_creates(self) -> None:
        with safe_temp_dir() as tmpdir:
            assert Path(tmpdir).exists()

    def test_scan_for_secrets_detects_api_key(self) -> None:
        text = "api_key = sk-abc123def456ghi789jkl"
        findings = scan_for_secrets(text)
        assert len(findings) >= 1

    def test_scan_for_secrets_detects_private_key(self) -> None:
        text = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC"
        findings = scan_for_secrets(text)
        assert len(findings) >= 1

    def test_scan_for_secrets_clean(self) -> None:
        text = "Hello, this is safe content without secrets."
        findings = scan_for_secrets(text)
        assert len(findings) == 0
