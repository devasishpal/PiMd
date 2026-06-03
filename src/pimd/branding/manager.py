"""Branding manager — load, store, and apply brand identity to documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pimd.branding.models import Brand, BrandConfig, BrandMetadata


class BrandingManager:
    """Manage brand identity loading, storage, and application."""

    def __init__(self) -> None:
        self._brand: Brand | None = None

    @property
    def brand(self) -> Brand | None:
        return self._brand

    def load(self, source: str | Path | dict[str, Any]) -> Brand:
        if isinstance(source, dict):
            brand = _brand_from_dict(source)
        else:
            path = Path(source)
            with path.open("rb") as f:
                if path.suffix == ".json":
                    import json

                    data: dict[str, Any] = json.load(f)
                elif path.suffix in (".toml", ".tml"):
                    import tomllib

                    data = tomllib.load(f)
                else:
                    raise ValueError(f"Unsupported format: {path.suffix}")
            brand = _brand_from_dict(data)
        self._brand = brand
        return brand

    def set(self, brand: Brand) -> None:
        self._brand = brand

    def clear(self) -> None:
        self._brand = None

    def to_dict(self) -> dict[str, Any]:
        if self._brand is None:
            return {}
        result: dict[str, Any] = {"name": self._brand.name}
        if self._brand.metadata:
            m = self._brand.metadata
            meta: dict[str, Any] = {}
            if m.company:
                meta["company"] = m.company
            if m.author:
                meta["author"] = m.author
            if m.version:
                meta["version"] = m.version
            if m.subject:
                meta["subject"] = m.subject
            result["metadata"] = meta
        if self._brand.config:
            c = self._brand.config
            cfg: dict[str, Any] = {}
            if c.primary_color:
                cfg["primary_color"] = c.primary_color
            if c.secondary_color:
                cfg["secondary_color"] = c.secondary_color
            if c.font_family:
                cfg["font_family"] = c.font_family
            if c.font_size_base:
                cfg["font_size_base"] = c.font_size_base
            if c.logo_path:
                cfg["logo_path"] = str(c.logo_path)
            if c.website:
                cfg["website"] = c.website
            result["config"] = cfg
        return result

    def apply(self, doc: Any) -> None:
        if self._brand is None:
            return
        config = self._brand.config
        if config.primary_color:
            _apply_primary_color(doc, config.primary_color)
        if config.font_family:
            _apply_font(doc, config.font_family, config.font_size_base or 11)


def _brand_from_dict(data: dict[str, Any]) -> Brand:
    name = data.get("name", "")
    meta_data = data.get("metadata", {}) or {}
    config_data = data.get("config", {}) or {}
    metadata = BrandMetadata(
        title=meta_data.get("title", ""),
        subtitle=meta_data.get("subtitle", ""),
        author=meta_data.get("author", ""),
        company=meta_data.get("company", ""),
        subject=meta_data.get("subject", ""),
        version=meta_data.get("version", "1.0.0"),
        revision=meta_data.get("revision", ""),
    )
    config = BrandConfig(
        primary_color=config_data.get("primary_color"),
        secondary_color=config_data.get("secondary_color"),
        font_family=config_data.get("font_family"),
        font_size_base=config_data.get("font_size_base"),
        logo_path=config_data.get("logo_path"),
        website=config_data.get("website"),
    )
    return Brand(name=name, metadata=metadata, config=config)


def _hex_to_rgb(hex_color: str) -> Any:
    try:
        from docx.shared import RGBColor

        return RGBColor(int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))
    except (ValueError, IndexError):
        return None


def _apply_primary_color(doc: Any, hex_color: str) -> None:
    color = _hex_to_rgb(hex_color)
    if color is None:
        return
    try:
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                run.font.color.rgb = color
    except Exception:
        pass


def _apply_font(doc: Any, font_family: str, font_size: int) -> None:
    try:
        style = doc.styles["Normal"]
        style.font.name = font_family
        style.font.size = 914400 // 72 * font_size
    except Exception:
        pass
