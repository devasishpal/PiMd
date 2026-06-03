"""Tests for Markdown flavor detection and compatibility layer."""

from __future__ import annotations

from pathlib import Path

from pimd.compatibility import (
    CompatibilityLayer,
    MarkdownFlavor,
    detect_flavor,
    detect_flavor_from_file,
)


class TestDetectFlavor:
    def test_detect_gfm_task_list(self):
        text = "- [x] done\n- [ ] todo\n"
        result = detect_flavor(text=text)
        assert result.flavor == MarkdownFlavor.GFM
        assert result.confidence > 0

    def test_detect_gfm_table(self):
        text = "| H1 | H2 |\n|---|---|\n| A | B |\n"
        result = detect_flavor(text=text)
        assert result.flavor == MarkdownFlavor.GFM

    def test_detect_obsidian_wikilinks(self):
        text = "Link to [[another page]] here\n"
        result = detect_flavor(text=text)
        assert result.flavor == MarkdownFlavor.OBSIDIAN

    def test_detect_obsidian_embed(self):
        text = "![[image.png]]\n"
        result = detect_flavor(text=text)
        assert result.flavor == MarkdownFlavor.OBSIDIAN

    def test_detect_sphinx_directive(self):
        text = ".. note::\n\n   This is a note.\n"
        result = detect_flavor(text=text)
        assert result.flavor == MarkdownFlavor.SPHINX

    def test_detect_sphinx_ref(self):
        text = "See :ref:`target` for details.\n"
        result = detect_flavor(text=text)
        assert result.flavor == MarkdownFlavor.SPHINX

    def test_detect_mkdocs_config(self):
        text = "site_name: My Docs\nnav:\n  - Home: index.md\n"
        result = detect_flavor(text=text)
        assert result.flavor == MarkdownFlavor.MKDOCS

    def test_detect_docusaurus_frontmatter(self):
        text = "---\nid: my-page\nsidebar_position: 2\n---\n\nContent.\n"
        result = detect_flavor(text=text)
        assert result.flavor == MarkdownFlavor.DOCUSAURUS

    def test_detect_docusaurus_import(self):
        text = "import Admonition from '@theme/Admonition';\n\n<Admonition type=\"tip\">\n"
        result = detect_flavor(text=text)
        assert result.flavor == MarkdownFlavor.DOCUSAURUS

    def test_detect_from_path_mdx(self):
        result = detect_flavor(path=Path("file.mdx"))
        assert result.flavor == MarkdownFlavor.DOCUSAURUS

    def test_detect_from_path_mkdocs_yml(self):
        result = detect_flavor(path=Path("mkdocs.yml"))
        assert result.flavor == MarkdownFlavor.MKDOCS

    def test_unknown_flavor(self):
        text = "Just some plain text.\n\nNothing special here.\n"
        result = detect_flavor(text=text)
        assert result.flavor in (MarkdownFlavor.COMMONMARK, MarkdownFlavor.UNKNOWN)

    def test_detect_gitlab_alert(self):
        text = "> [!SUCCESS] Worked!\n"
        result = detect_flavor(text=text)
        assert result.flavor == MarkdownFlavor.GITLAB

    def test_detect_from_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("- [x] task\n")
        result = detect_flavor_from_file(f)
        assert result.flavor == MarkdownFlavor.GFM


class TestCompatibilityLayer:
    def test_normalize_obsidian_wikilinks(self):
        layer = CompatibilityLayer()
        result = layer.normalize("See [[target|display]]", MarkdownFlavor.OBSIDIAN)
        assert "[display](target)" in result

    def test_normalize_obsidian_wikilinks_no_pipe(self):
        layer = CompatibilityLayer()
        result = layer.normalize("See [[target]]", MarkdownFlavor.OBSIDIAN)
        assert "[target](target)" in result

    def test_normalize_obsidian_callouts(self):
        layer = CompatibilityLayer()
        result = layer.normalize("> [!WARNING] Be careful\n", MarkdownFlavor.OBSIDIAN)
        assert "WARNING" in result or "Warning" in result

    def test_normalize_obsidian_embeds(self):
        layer = CompatibilityLayer()
        result = layer.normalize("![[image.png]]", MarkdownFlavor.OBSIDIAN)
        assert "image.png" in result
        assert "![" in result

    def test_normalize_sphinx_directives(self):
        layer = CompatibilityLayer()
        result = layer.normalize(".. warning::\n\n   Danger!", MarkdownFlavor.SPHINX)
        assert "sphinx" in result or "warning" in result.lower()

    def test_normalize_mkdocs(self):
        layer = CompatibilityLayer()
        text = "site_name: Docs\nnav:\n  - Home: index.md\n\n# Content\n"
        result = layer.normalize(text, MarkdownFlavor.MKDOCS)
        assert "site_name:" not in result

    def test_normalize_docusaurus_imports(self):
        layer = CompatibilityLayer()
        text = "import Admonition from '@site/src/components'\n\nContent\n"
        result = layer.normalize(text, MarkdownFlavor.DOCUSAURUS)
        assert "import Admonition" not in result

    def test_auto_detect_and_normalize(self):
        layer = CompatibilityLayer()
        result = layer.normalize("See [[WikiLink]]\n")
        assert "[WikiLink](WikiLink)" in result

    def test_applied_transforms(self):
        layer = CompatibilityLayer()
        layer.normalize("See [[target]]", MarkdownFlavor.OBSIDIAN)
        assert len(layer.applied_transforms) > 0
        assert layer.applied_transforms[0].name == "obsidian_wikilink"

    def test_gfm_alert_normalize(self):
        layer = CompatibilityLayer()
        result = layer.normalize("> [!NOTE] Note title\n", MarkdownFlavor.GFM)
        assert "NOTE" in result or "Note" in result
