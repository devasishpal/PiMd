"""Tests for the PiMD CLI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from pimd.cli.app import app

if TYPE_CHECKING:
    pass

runner = CliRunner()


class TestCLI:
    """Verify the CLI using Typer's CliRunner."""

    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, [])
        assert result.exit_code != 0
        assert "Usage:" in result.output or "pimd" in result.output

    def test_unknown_command_fails(self) -> None:
        result = runner.invoke(app, ["unknown"])
        assert result.exit_code != 0
        assert "Error" in result.output or "No such command" in result.output

    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "PiMD v" in result.output

    def test_md_conversion_missing_input(self) -> None:
        result = runner.invoke(app, ["md", "nonexistent.md", "out.docx"])
        assert result.exit_code != 0

    def test_md_conversion_success(self, tmp_path: Path) -> None:
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\n\nWorld.")
        out_file = tmp_path / "out.docx"
        result = runner.invoke(app, ["md", str(md_file), str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        assert "completed" in result.output.lower()

    def test_html_conversion_success(self, tmp_path: Path) -> None:
        html_file = tmp_path / "test.html"
        html_file.write_text("<h1>Hello</h1><p>World</p>")
        out_file = tmp_path / "out.docx"
        result = runner.invoke(app, ["html", str(html_file), str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        assert "completed" in result.output.lower()

    def test_html_conversion_missing_input(self) -> None:
        result = runner.invoke(app, ["html", "nonexistent.html", "out.docx"])
        assert result.exit_code != 0

    def test_info_command(self) -> None:
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "Version" in result.output

    def test_doctor_command(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Python" in result.output or "python-docx" in result.output or "OK" in result.output

    def test_version_command(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "PiMD v" in result.output

    def test_md_with_all_flags(self, tmp_path: Path) -> None:
        md_file = tmp_path / "full.md"
        md_file.write_text("# Title\n\nContent.\n\n## Section\n\nMore.")
        out_file = tmp_path / "full.docx"
        result = runner.invoke(
            app,
            [
                "md",
                str(md_file),
                str(out_file),
                "--toc",
                "--page-numbers",
                "--cover",
                "--title",
                "Document",
                "--author",
                "Author",
                "--company",
                "ACME",
                "--subject",
                "Test",
                "--keywords",
                "a,b,c",
                "--header",
                "Header",
                "--footer",
                "Footer",
            ],
        )
        assert result.exit_code == 0, result.output
        assert out_file.exists()

    def test_html_with_all_flags(self, tmp_path: Path) -> None:
        html_file = tmp_path / "full.html"
        html_file.write_text("<h1>Title</h1><p>Content</p>")
        out_file = tmp_path / "full.docx"
        result = runner.invoke(
            app,
            [
                "html",
                str(html_file),
                str(out_file),
                "--toc",
                "--page-numbers",
                "--cover",
                "--title",
                "Document",
                "--author",
                "Author",
            ],
        )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
