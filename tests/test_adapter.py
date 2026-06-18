"""Tests for pimd.diagrams.adapter — PiDraw integration layer."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pimd.diagrams.adapter import (
    _HAS_PIDRAW,
    get_supported_languages,
    is_supported_language,
    render_diagram,
    render_many_diagrams,
)


class TestAdapter:
    def test_render_without_pidraw(self) -> None:
        if _HAS_PIDRAW:
            pytest.skip("PiDraw is installed — skipping without-PiDraw test")
        result = render_diagram("graph TD; A-->B;", language="mermaid")
        assert result.success is False
        assert "PiDraw is not installed" in (result.error or "")

    def test_render_many_without_pidraw(self) -> None:
        if _HAS_PIDRAW:
            pytest.skip("PiDraw is installed — skipping without-PiDraw test")
        results = render_many_diagrams([("a", "mermaid"), ("b", "plantuml")])
        assert len(results) == 2
        assert all(r.success is False for r in results)
        assert all("PiDraw is not installed" in (r.error or "") for r in results)

    def test_get_supported_languages_without_pidraw(self) -> None:
        if _HAS_PIDRAW:
            pytest.skip("PiDraw is installed — skipping without-PiDraw test")
        langs = get_supported_languages()
        assert langs == {}

    def test_is_supported_language_without_pidraw(self) -> None:
        if _HAS_PIDRAW:
            pytest.skip("PiDraw is installed — skipping without-PiDraw test")
        assert is_supported_language("mermaid") is False

    @patch("pimd.diagrams.adapter._HAS_PIDRAW", True)
    @patch("pimd.diagrams.adapter._pidraw_detect")
    @patch("pimd.diagrams.adapter._pidraw_list_renderers")
    def test_detect_language_with_pidraw(self, mock_list: object, mock_detect: object) -> None:
        mock_list.return_value = {}
        mock_detect.return_value = None
        from pimd.diagrams.adapter import detect_language

        result = detect_language("test", hint="mermaid")
        assert result is None

    @patch("pimd.diagrams.adapter._HAS_PIDRAW", False)
    def test_doctor_without_pidraw(self) -> None:
        from pimd.diagrams.adapter import doctor

        results = doctor()
        assert len(results) >= 1
        assert results[0]["status"] == "error"

    def test_doctor_with_pidraw(self) -> None:
        if not _HAS_PIDRAW:
            pytest.skip("PiDraw not installed")
        from pimd.diagrams.adapter import doctor

        results = doctor()
        assert len(results) >= 1
        assert results[0]["status"] == "ok"
