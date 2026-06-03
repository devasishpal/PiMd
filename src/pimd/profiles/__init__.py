from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

__all__ = [
    "ProfileType",
    "ExportProfile",
    "ProfileManager",
    "builtin_profile",
    "all_builtin_profiles",
    "profile_to_config",
    "apply_profile",
    "customize_profile",
    "save_profile",
    "load_profile",
    "detect_profile_from_source",
]


class ProfileType(str, Enum):
    GITHUB = "github"
    ACADEMIC = "academic"
    CORPORATE = "corporate"
    BOOK = "book"
    TECHNICAL = "technical"


GITHUB_DEFAULTS: dict[str, Any] = {
    "output_format": "md",
    "markdown_flavor": "gfm",
    "task_lists": True,
    "tables": True,
    "strikethrough": True,
    "autolinks": True,
    "emoji": True,
    "footnotes": False,
    "math": False,
    "code_highlighting": True,
    "yaml_front_matter": True,
    "wrap_width": 88,
    "line_breaks": "unix",
    "smart_quotes": False,
    "toc": False,
}

ACADEMIC_DEFAULTS: dict[str, Any] = {
    "output_format": "docx",
    "template": "academic",
    "numbered_headings": True,
    "bibliography": True,
    "citation_style": "apa",
    "equation_numbering": True,
    "equation_format": "latex",
    "font_family": "Times New Roman",
    "font_size": 12,
    "line_spacing": 2.0,
    "margin_top": 1.0,
    "margin_bottom": 1.0,
    "margin_left": 1.0,
    "margin_right": 1.0,
    "page_numbers": True,
    "toc": True,
    "toc_depth": 3,
    "footnotes": True,
    "abstract": True,
    "section_numbering_style": "decimal",
}

CORPORATE_DEFAULTS: dict[str, Any] = {
    "output_format": "docx",
    "template": "corporate",
    "cover_page": True,
    "toc": True,
    "toc_depth": 3,
    "page_numbers": True,
    "header_text": None,
    "footer_text": None,
    "brand_font": "Calibri",
    "brand_colors": {
        "primary": "#1F4E79",
        "secondary": "#2E75B6",
        "accent": "#C55A11",
    },
    "logo_path": None,
    "font_family": "Calibri",
    "font_size": 11,
    "line_spacing": 1.15,
    "margin_top": 1.0,
    "margin_bottom": 1.0,
    "margin_left": 1.25,
    "margin_right": 1.0,
    "heading_font": "Calibri Light",
    "heading_color": "#1F4E79",
    "table_style": "Light Grid Accent 1",
    "code_block_style": None,
    "watermark": None,
    "document_security": {
        "read_only": False,
        "password": None,
    },
}

BOOK_DEFAULTS: dict[str, Any] = {
    "output_format": "docx",
    "template": "book",
    "parts": True,
    "chapters": True,
    "appendices": True,
    "index": True,
    "page_numbers": True,
    "page_number_alignment": "center",
    "headers": True,
    "header_style": "chapter_title",
    "footers": True,
    "toc": True,
    "toc_depth": 3,
    "cover_page": True,
    "verso_page": True,
    "font_family": "Garamond",
    "font_size": 11,
    "line_spacing": 1.15,
    "chapter_start": "recto",
    "section_breaks": True,
    "widow_orphan_control": True,
    "hyphenation": True,
    "drop_caps": False,
    "margin_top": 0.75,
    "margin_bottom": 0.75,
    "margin_left": 1.0,
    "margin_right": 0.75,
    "gutter": 0.5,
    "mirror_margins": True,
}

TECHNICAL_DEFAULTS: dict[str, Any] = {
    "output_format": "docx",
    "template": "technical",
    "code_highlighting": True,
    "code_font": "Consolas",
    "code_font_size": 9.5,
    "code_block_background": "#F5F5F5",
    "code_block_border": "#CCCCCC",
    "diagram_support": True,
    "diagram_format": "png",
    "cross_references": True,
    "cross_reference_style": "section_number",
    "numbered_headings": True,
    "toc": True,
    "toc_depth": 4,
    "index": True,
    "glossary": True,
    "table_captions": True,
    "figure_captions": True,
    "listing_captions": True,
    "callout_blocks": True,
    "admonitions": True,
    "admonition_style": "formal",
    "margin_top": 1.0,
    "margin_bottom": 1.0,
    "margin_left": 1.0,
    "margin_right": 1.0,
    "font_family": "Segoe UI",
    "font_size": 10,
    "line_spacing": 1.2,
}

BUILTIN_PROFILES: dict[ProfileType, dict[str, Any]] = {
    ProfileType.GITHUB: {
        "name": "GitHub",
        "description": "Clean Markdown output compatible with GitHub Flavored Markdown, with task lists, tables, and emoji support.",
        "settings": GITHUB_DEFAULTS,
    },
    ProfileType.ACADEMIC: {
        "name": "Academic",
        "description": "Formal DOCX output with numbered headings, APA bibliography support, and equation numbering for academic papers.",
        "settings": ACADEMIC_DEFAULTS,
    },
    ProfileType.CORPORATE: {
        "name": "Corporate",
        "description": "Branded DOCX output with cover page, table of contents, page numbers, and customizable headers and footers.",
        "settings": CORPORATE_DEFAULTS,
    },
    ProfileType.BOOK: {
        "name": "Book",
        "description": "Chapter-based DOCX output with parts, appendices, index, and print-ready page layout features.",
        "settings": BOOK_DEFAULTS,
    },
    ProfileType.TECHNICAL: {
        "name": "Technical",
        "description": "Structured DOCX output optimized for technical documentation with diagrams, code blocks, and cross-references.",
        "settings": TECHNICAL_DEFAULTS,
    },
}


@dataclass
class ExportProfile:
    name: str
    type: ProfileType
    description: str
    settings: dict[str, Any] = field(default_factory=dict)

    def merge_settings(self, overrides: dict[str, Any]) -> ExportProfile:
        merged = {**self.settings, **overrides}
        return ExportProfile(
            name=self.name,
            type=self.type,
            description=self.description,
            settings=merged,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportProfile:
        return cls(
            name=data["name"],
            type=ProfileType(data["type"]),
            description=data.get("description", ""),
            settings=data.get("settings", {}),
        )


class ProfileManager:
    def __init__(self, profiles_dir: Path | None = None) -> None:
        self._profiles: dict[str, ExportProfile] = {}
        self._profiles_dir = profiles_dir
        for profile in all_builtin_profiles():
            self._profiles[profile.type.value] = profile

    def list_profiles(self) -> list[ExportProfile]:
        return list(self._profiles.values())

    def get_profile(self, name_or_type: str | ProfileType) -> ExportProfile | None:
        key = name_or_type.value if isinstance(name_or_type, ProfileType) else name_or_type
        return self._profiles.get(key)

    def add_profile(self, profile: ExportProfile) -> None:
        self._profiles[profile.type.value] = profile

    def remove_profile(self, name_or_type: str | ProfileType) -> bool:
        key = name_or_type.value if isinstance(name_or_type, ProfileType) else name_or_type
        if key in self._profiles:
            del self._profiles[key]
            return True
        return False

    def load_from_dir(self, directory: Path | None = None) -> None:
        target = directory or self._profiles_dir
        if target is None or not target.exists():
            return
        for filepath in target.glob("*.json"):
            try:
                profile = load_profile(filepath)
                self._profiles[profile.type.value] = profile
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    def save_to_dir(self, directory: Path | None = None) -> None:
        target = directory or self._profiles_dir
        if target is None:
            raise ValueError("No directory specified for saving profiles")
        target.mkdir(parents=True, exist_ok=True)
        for profile in self._profiles.values():
            save_profile(profile, target / f"{profile.type.value}.json")

    def merge_settings(self, profile_type: ProfileType | str, overrides: dict[str, Any]) -> ExportProfile | None:
        profile = self.get_profile(profile_type)
        if profile is None:
            return None
        merged = profile.merge_settings(overrides)
        self._profiles[profile.type.value] = merged
        return merged


def builtin_profile(profile_type: ProfileType) -> ExportProfile:
    data = BUILTIN_PROFILES[profile_type]
    return ExportProfile(
        name=data["name"],
        type=profile_type,
        description=data["description"],
        settings=dict(data["settings"]),
    )


def all_builtin_profiles() -> list[ExportProfile]:
    return [builtin_profile(pt) for pt in ProfileType]


def profile_to_config(profile: ExportProfile) -> dict:
    return {
        "export": {
            "format": profile.settings.get("output_format", "md"),
            "profile": profile.type.value,
            "settings": profile.settings,
        }
    }


def apply_profile(
    input_file: str | Path,
    output_file: str | Path,
    profile_spec: ProfileType | str,
) -> None:
    from pimd.core import convert as _pimd_convert

    if isinstance(profile_spec, str):
        try:
            profile_type = ProfileType(profile_spec)
        except ValueError:
            profile_type = ProfileType.GITHUB
    else:
        profile_type = profile_spec

    profile = builtin_profile(profile_type)
    config = profile_to_config(profile)
    _pimd_convert(
        input_path=Path(input_file),
        output_path=Path(output_file),
        config=config,
    )


def customize_profile(base: ExportProfile, overrides: dict[str, Any]) -> ExportProfile:
    return base.merge_settings(overrides)


def save_profile(profile: ExportProfile, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(profile.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_profile(path: str | Path) -> ExportProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ExportProfile.from_dict(data)


def detect_profile_from_source(source_dir: str | Path) -> ProfileType:
    src = Path(source_dir)
    if not src.is_dir():
        return ProfileType.GITHUB

    md_files = list(src.rglob("*.md"))
    tex_files = list(src.rglob("*.tex"))
    bib_files = list(src.rglob("*.bib"))
    code_extensions = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs", ".rb"}
    code_files = [f for f in src.rglob("*") if f.suffix in code_extensions]
    diagram_extensions = {".puml", ".drawio", ".d2", ".mmd", ".dot", ".graphml"}
    diagram_files = [f for f in src.rglob("*") if f.suffix in diagram_extensions]

    has_bibliography = len(bib_files) > 0
    has_tex = len(tex_files) > 0
    has_diagrams = len(diagram_files) > 0
    has_code = len(code_files) > 4
    has_chapters = sum(1 for f in md_files if f.stem.lower().startswith("chapter")) > 1
    has_parts = sum(1 for f in md_files if f.stem.lower().startswith("part")) > 0
    has_appendices = sum(1 for f in md_files if f.stem.lower().startswith("appendix")) > 0

    if has_bibliography or has_tex:
        return ProfileType.ACADEMIC
    if has_chapters or has_parts or has_appendices:
        return ProfileType.BOOK
    if has_diagrams or has_code:
        return ProfileType.TECHNICAL
    if len(md_files) > 10:
        return ProfileType.CORPORATE
    return ProfileType.GITHUB
