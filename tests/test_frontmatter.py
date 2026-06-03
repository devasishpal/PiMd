"""Tests for frontmatter metadata parsing."""

from __future__ import annotations

from pathlib import Path

from pimd.frontmatter import (
    FrontmatterFormat,
    Metadata,
    detect_frontmatter,
    extract_raw,
    parse_frontmatter,
    parse_frontmatter_from_file,
    strip_frontmatter,
)


class TestDetectFrontmatter:
    def test_detect_yaml(self):
        text = "---\ntitle: Test\n---\n\nBody.\n"
        assert detect_frontmatter(text) == FrontmatterFormat.YAML

    def test_detect_toml(self):
        text = "+++\ntitle = \"Test\"\n+++\n\nBody.\n"
        assert detect_frontmatter(text) == FrontmatterFormat.TOML

    def test_detect_json(self):
        text = "---\n{\"title\": \"Test\"}\n---\n\nBody.\n"
        assert detect_frontmatter(text) == FrontmatterFormat.JSON

    def test_detect_none(self):
        assert detect_frontmatter("Just body text.\n") == FrontmatterFormat.NONE

    def test_detect_yaml_with_dots(self):
        text = "---\ntitle: Test\n...\n\nBody.\n"
        assert detect_frontmatter(text) == FrontmatterFormat.YAML


class TestExtractRaw:
    def test_extract_yaml(self):
        raw, body, fmt = extract_raw("---\ntitle: Hi\n---\n\nBody\n")
        assert "title: Hi" in raw
        assert body.strip() == "Body"
        assert fmt == FrontmatterFormat.YAML

    def test_extract_none(self):
        raw, body, fmt = extract_raw("Just body\n")
        assert raw == ""
        assert fmt == FrontmatterFormat.NONE

    def test_extract_toml(self):
        raw, body, fmt = extract_raw("+++\nkey = \"val\"\n+++\n\nBody\n")
        assert "key = \"val\"" in raw
        assert fmt == FrontmatterFormat.TOML


class TestParseFrontmatter:
    def test_parse_yaml_title(self):
        meta = parse_frontmatter("---\ntitle: Hello\n---\n\nWorld\n")
        assert meta.title == "Hello"

    def test_parse_yaml_author(self):
        meta = parse_frontmatter("---\nauthor: John\n---\n\nBody\n")
        assert meta.author == "John"

    def test_parse_yaml_tags(self):
        meta = parse_frontmatter("---\ntags: [a, b, c]\n---\n\nBody\n")
        assert meta.tags == ["a", "b", "c"]

    def test_parse_yaml_tags_string(self):
        meta = parse_frontmatter("---\ntags: a, b\n---\n\nBody\n")
        assert meta.tags == ["a", "b"]

    def test_parse_yaml_draft(self):
        meta = parse_frontmatter("---\ndraft: true\n---\n\nBody\n")
        assert meta.draft is True

    def test_parse_yaml_date(self):
        meta = parse_frontmatter("---\ndate: 2024-01-15\n---\n\nBody\n")
        assert meta.date is not None

    def test_parse_yaml_multiple_fields(self):
        text = "---\ntitle: Guide\nauthor: Jane\nversion: \"2.0\"\n---\n\nContent\n"
        meta = parse_frontmatter(text)
        assert meta.title == "Guide"
        assert meta.author == "Jane"
        assert meta.version == "2.0"

    def test_parse_toml(self):
        meta = parse_frontmatter("+++\ntitle = \"TOML Test\"\n+++\n\nBody\n")
        assert meta.title == "TOML Test"

    def test_parse_json(self):
        meta = parse_frontmatter("---\n{\"title\": \"JSON Test\"}\n---\n\nBody\n")
        assert meta.title == "JSON Test"

    def test_parse_no_frontmatter(self):
        meta = parse_frontmatter("Just body text.\n")
        assert meta.title == ""
        assert isinstance(meta, Metadata)

    def test_custom_fields(self):
        meta = parse_frontmatter("---\nunexpected: value\n---\n\nBody\n")
        assert meta.custom.get("unexpected") == "value"

    def test_to_dict(self):
        meta = Metadata(title="Test", author="Me", keywords=["a", "b"])
        d = meta.to_dict()
        assert d["title"] == "Test"
        assert d["keywords"] == ["a", "b"]

    def test_to_docx_properties(self):
        meta = Metadata(title="Doc", author="Author", subject="Subj", keywords=["k1", "k2"])
        props = meta.as_docx_properties()
        assert props["title"] == "Doc"
        assert props["keywords"] == "k1, k2"

    def test_empty_metadata(self):
        meta = Metadata()
        assert meta.to_dict() == {}

    def test_strip_frontmatter(self):
        body = strip_frontmatter("---\ntitle: X\n---\n\nContent\n")
        assert body.strip() == "Content"

    def test_parse_from_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\ntitle: File Test\n---\n\nBody\n")
        meta = parse_frontmatter_from_file(f)
        assert meta.title == "File Test"

    def test_parse_nonexistent_file(self):
        meta = parse_frontmatter_from_file(Path("/nonexistent/file.md"))
        assert meta.title == ""

    def test_authors_list(self):
        meta = parse_frontmatter("---\nauthors: [Alice, Bob]\n---\n\nBody\n")
        assert meta.authors == ["Alice", "Bob"]

    def test_meta_status(self):
        meta = parse_frontmatter("---\nstatus: published\n---\n\nBody\n")
        assert meta.status == "published"
