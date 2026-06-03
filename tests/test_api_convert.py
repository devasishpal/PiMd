"""Tests for the unified convert() API on PiMD."""

from pathlib import Path

import pytest

from pimd import PiMD


class TestUnifiedConvertAPI:
    def test_convert_md_to_docx(self, tmp_path: Path) -> None:
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\n\nWorld.\n", encoding="utf-8")
        output = tmp_path / "output.docx"

        engine = PiMD(enable_cache=False)
        result = engine.convert(str(md_file), "docx", str(output))
        assert result.output_path is not None
        assert output.exists()

    def test_convert_with_auto_output_path(self, tmp_path: Path) -> None:
        md_file = tmp_path / "test.md"
        md_file.write_text("Hello\n", encoding="utf-8")

        engine = PiMD(enable_cache=False)
        result = engine.convert(str(md_file), "docx")
        assert result.output_path is not None

    def test_convert_html_to_docx(self, tmp_path: Path) -> None:
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><h1>Title</h1></body></html>", encoding="utf-8")
        output = tmp_path / "output.docx"

        engine = PiMD(enable_cache=False)
        result = engine.convert(str(html_file), "docx", str(output))
        assert result.output_path is not None

    def test_convert_unsupported_format_raises(self, tmp_path: Path) -> None:
        md_file = tmp_path / "test.md"
        md_file.write_text("Hello\n", encoding="utf-8")

        engine = PiMD(enable_cache=False)
        with pytest.raises((ValueError, KeyError)):
            engine.convert(str(md_file), "exe", str(tmp_path / "out.exe"))

    def test_convert_passthrough_options(self, tmp_path: Path) -> None:
        md_file = tmp_path / "test.md"
        md_file.write_text("# Title\n\nContent.\n", encoding="utf-8")
        output = tmp_path / "with-toc.docx"

        engine = PiMD(enable_cache=False)
        result = engine.convert(str(md_file), "docx", str(output), generate_toc=True)
        assert result.output_path is not None
        assert output.exists()
