"""Tests for pimd.converters.interface — Converter ABC and registry."""

from __future__ import annotations

from pathlib import Path

from pimd.converters.interface import (
    ConversionResult,
    Converter,
    ConverterCapability,
    ConverterRegistry,
    get_converter_registry,
    reset_converter_registry,
)


class TestConverterInterface:
    def setup_method(self) -> None:
        reset_converter_registry()

    def test_converter_registry(self) -> None:
        registry = ConverterRegistry()
        cap = ConverterCapability.MARKDOWN_TO_DOCX
        cls = _make_converter("TestConv", cap)
        registry.register(cls)
        assert registry.get("TestConv") is cls
        assert registry.get_by_capability(cap) == [cls]

    def test_list_all(self) -> None:
        registry = ConverterRegistry()
        registry.register(_make_converter("A", ConverterCapability.MARKDOWN_TO_DOCX))
        registry.register(_make_converter("B", ConverterCapability.HTML_TO_DOCX))
        assert len(registry.list_all()) == 2

    def test_clear(self) -> None:
        registry = ConverterRegistry()
        registry.register(_make_converter("X", ConverterCapability.MARKDOWN_TO_DOCX))
        registry.clear()
        assert len(registry.list_all()) == 0

    def test_get_by_capability_empty(self) -> None:
        registry = ConverterRegistry()
        assert registry.get_by_capability(ConverterCapability.MARKDOWN_TO_PDF) == []

    def test_get_nonexistent(self) -> None:
        registry = ConverterRegistry()
        assert registry.get("nonexistent") is None

    def test_global_registry(self) -> None:
        reset_converter_registry()
        r1 = get_converter_registry()
        r2 = get_converter_registry()
        assert r1 is r2

    def test_reset_global(self) -> None:
        reset_converter_registry()
        r1 = get_converter_registry()
        reset_converter_registry()
        r2 = get_converter_registry()
        assert r1 is not r2


class _TestConverter(Converter):
    name = "test-converter"
    capability = ConverterCapability.MARKDOWN_TO_DOCX

    def convert(self, source: str | Path, destination: str | Path | None = None, **options: object) -> ConversionResult:
        return ConversionResult(success=True)


def _make_converter(cls_name: str, cap: ConverterCapability) -> type[Converter]:
    return type(
        cls_name,
        (Converter,),
        {
            "name": cls_name,
            "capability": cap,
            "convert": lambda self, source="", destination=None, **kw: ConversionResult(success=True),
        },
    )
