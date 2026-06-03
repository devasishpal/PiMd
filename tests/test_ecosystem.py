"""Tests for documentation ecosystem modules."""

from __future__ import annotations


class TestMkDocs:
    def test_detect_project(self, tmp_path):
        from pimd.mkdocs_ import detect_mkdocs_project
        assert not detect_mkdocs_project(tmp_path)
        (tmp_path / "mkdocs.yml").write_text("site_name: Test\n")
        assert detect_mkdocs_project(tmp_path)

    def test_parse_config(self, tmp_path):
        from pimd.mkdocs_ import parse_mkdocs_config
        cfg = tmp_path / "mkdocs.yml"
        cfg.write_text("site_name: My Docs\ntheme: material\n")
        config = parse_mkdocs_config(cfg)
        assert config.site_name == "My Docs"

    def test_parse_nav_list(self):
        from pimd.mkdocs_ import parse_nav
        nav = parse_nav([{"Home": "index.md"}, {"Guide": "guide.md"}])
        assert len(nav) == 2
        assert nav[0].title == "Home"

    def test_flatten_nav(self):
        from pimd.mkdocs_ import NavItem, flatten_nav
        items = [NavItem(title="A", path="a.md", children=[NavItem(title="B", path="b.md")])]
        flat = flatten_nav(items)
        assert len(flat) == 2


class TestDocusaurus:
    def test_detect_project(self, tmp_path):
        from pimd.docusaurus import detect_docusaurus_project
        assert not detect_docusaurus_project(tmp_path)
        (tmp_path / "docusaurus.config.js").write_text("module.exports = {};\n")
        assert detect_docusaurus_project(tmp_path)

    def test_parse_sidebar(self, tmp_path):
        from pimd.docusaurus import parse_sidebar
        f = tmp_path / "sidebar.json"
        f.write_text('[{"type": "doc", "id": "intro", "label": "Intro"}]')
        items = parse_sidebar(f)
        assert len(items) == 1
        assert items[0].id == "intro"

    def test_parse_docusaurus_frontmatter(self):
        from pimd.docusaurus import parse_docusaurus_frontmatter
        meta = parse_docusaurus_frontmatter("---\nid: test\nsidebar_position: 2\n---\n")
        assert meta["id"] == "test"
        assert meta["sidebar_position"] == 2

    def test_strip_imports(self):
        from pimd.docusaurus import strip_docusaurus_imports
        result = strip_docusaurus_imports("import X from '@site/Y'\n\nContent\n")
        assert "import X" not in result

    def test_find_versioned_docs(self, tmp_path):
        from pimd.docusaurus import find_versioned_docs
        (tmp_path / "versioned_docs" / "version-1.0").mkdir(parents=True)
        (tmp_path / "versioned_docs" / "version-1.0" / "intro.md").write_text("# Intro")
        versions = find_versioned_docs(tmp_path)
        assert len(versions) > 0


class TestObsidian:
    def test_parse_wikilink(self):
        from pimd.obsidian import parse_wikilink
        link = parse_wikilink("[[target]]")
        assert link.target == "target"
        assert link.display_text == "target"

    def test_parse_wikilink_with_pipe(self):
        from pimd.obsidian import parse_wikilink
        link = parse_wikilink("[[target|Display]]")
        assert link.target == "target"
        assert link.display_text == "Display"

    def test_parse_wikilink_with_section(self):
        from pimd.obsidian import parse_wikilink
        link = parse_wikilink("[[page#section]]")
        assert link.target == "page"
        assert link.section == "section"

    def test_extract_embeds(self):
        from pimd.obsidian import extract_embeds
        embeds = extract_embeds("![[image.png]] text ![[other.pdf]]")
        assert len(embeds) == 2

    def test_extract_wikilinks(self):
        from pimd.obsidian import extract_wikilinks
        links = extract_wikilinks("Link to [[page1]] and [[page2|two]]")
        assert len(links) == 2
        assert links[0].target == "page1"

    def test_parse_callout(self):
        from pimd.obsidian import parse_callout
        callout = parse_callout("> [!NOTE] Title\n> Content\n")
        assert callout is not None
        assert callout.type == "note"

    def test_detect_vault(self, tmp_path):
        from pimd.obsidian import detect_obsidian_vault
        assert not detect_obsidian_vault(tmp_path)
        (tmp_path / ".obsidian").mkdir()
        assert detect_obsidian_vault(tmp_path)

    def test_process_content_wikilinks(self):
        from pimd.obsidian import process_obsidian_content
        result = process_obsidian_content("See [[target]] for info")
        assert "target" in result


class TestSphinx:
    def test_detect_project(self, tmp_path):
        from pimd.sphinx import detect_sphinx_project
        assert not detect_sphinx_project(tmp_path)
        (tmp_path / "conf.py").write_text("project = 'Test'\n")
        assert detect_sphinx_project(tmp_path)

    def test_parse_conf_py(self, tmp_path):
        from pimd.sphinx import parse_conf_py
        f = tmp_path / "conf.py"
        f.write_text("project = 'My Project'\nversion = '1.0'\n")
        config = parse_conf_py(f)
        assert config.project == "My Project"
        assert config.version == "1.0"

    def test_convert_rst_to_markdown_basic(self):
        from pimd.sphinx import convert_rst_to_markdown
        result = convert_rst_to_markdown("Hello\n=====\n\nWorld.\n")
        assert "Hello" in result

    def test_convert_rst_note_directive(self):
        from pimd.sphinx import convert_rst_to_markdown
        result = convert_rst_to_markdown(".. note::\n\n   A note.\n")
        assert "note" in result.lower() or "Note" in result

    def test_strip_rst_roles(self):
        from pimd.sphinx import strip_rst_roles
        result = strip_rst_roles("See :ref:`target` for details.\n")
        assert ":ref:" not in result

    def test_parse_rst_directive(self):
        from pimd.sphinx import parse_rst_directive
        directive, end = parse_rst_directive(".. warning::\n\n   Careful!\n", 0)
        assert directive is not None
        assert directive.name == "warning"

    def test_parse_rst_role(self):
        from pimd.sphinx import parse_rst_role
        role = parse_rst_role(":ref:`target`")
        assert role is not None
        assert role.name == "ref"
        assert role.target == "target"
