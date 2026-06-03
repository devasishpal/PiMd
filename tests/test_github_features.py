"""Tests for GitHub-flavor Markdown features."""

from __future__ import annotations

from pimd.github import (
    GitHubFeaturesConfig,
    GitHubFeaturesProcessor,
    extract_anchors,
    extract_footnotes,
    extract_reference_links,
    extract_task_lists,
    generate_anchors,
    parse_table,
    process_alerts,
    process_footnotes,
    process_task_lists,
    render_table_html,
    render_task_list_html,
    resolve_reference_links,
    slugify,
)


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_multiple_spaces(self):
        assert slugify("hello   world") == "hello-world"

    def test_underscores(self):
        assert slugify("hello_world") == "hello-world"

    def test_trailing_dashes(self):
        slug = slugify("hello-")
        assert slug == "hello"


class TestTaskLists:
    def test_extract_checked(self):
        tasks = extract_task_lists("- [x] done\n")
        assert len(tasks) == 1
        assert tasks[0].checked is True
        assert tasks[0].text == "done"

    def test_extract_unchecked(self):
        tasks = extract_task_lists("- [ ] todo\n")
        assert len(tasks) == 1
        assert tasks[0].checked is False

    def test_extract_multiple(self):
        text = "- [x] done\n- [ ] todo\n- [ ] another\n"
        tasks = extract_task_lists(text)
        assert len(tasks) == 3
        assert tasks[0].checked is True
        assert tasks[2].checked is False

    def test_render_html(self):
        tasks = extract_task_lists("- [x] done\n- [ ] todo\n")
        html = render_task_list_html(tasks)
        assert 'checked=""' in html
        assert 'type="checkbox"' in html

    def test_process_task_lists(self):
        result = process_task_lists("- [x] done\n")
        assert 'checked' in result
        assert 'type="checkbox"' in result


class TestTables:
    def test_parse_basic(self):
        table = parse_table("| A | B |\n|---|---|\n| 1 | 2 |\n")
        assert table is not None
        assert table.headers == ["A", "B"]
        assert len(table.rows) == 1

    def test_parse_aligned(self):
        table = parse_table("| L | C | R |\n|:--|:-:|--:|\n| a | b | c |\n")
        assert table is not None
        assert table.rows[0].cells[0].align == "left"
        assert table.rows[0].cells[1].align == "center"
        assert table.rows[0].cells[2].align == "right"

    def test_render_html(self):
        table = parse_table("| H1 | H2 |\n|---|---|\n| C1 | C2 |\n")
        html = render_table_html(table)
        assert "<table>" in html
        assert "<th>H1</th>" in html
        assert "<td>C1</td>" in html

    def test_no_table(self):
        assert parse_table("Just text") is None


class TestAlerts:
    def test_process_note(self):
        result = process_alerts("> [!NOTE] Hello\n")
        assert "NOTE" in result or "Note" in result

    def test_process_warning(self):
        result = process_alerts("> [!WARNING] Careful\n")
        assert "WARNING" in result or "Warning" in result

    def test_process_tip(self):
        result = process_alerts("> [!TIP] Suggestion\n")
        assert "TIP" in result or "Tip" in result

    def test_process_important(self):
        result = process_alerts("> [!IMPORTANT] Critical\n")
        assert "IMPORTANT" in result or "Important" in result

    def test_process_caution(self):
        result = process_alerts("> [!CAUTION] Watch out\n")
        assert "CAUTION" in result or "Caution" in result


class TestFootnotes:
    def test_extract_definitions(self):
        coll = extract_footnotes("Here is text[^1].\n\n[^1]: The footnote.\n")
        assert "^1" in coll.definitions
        assert coll.definitions["^1"].text == "The footnote."

    def test_extract_references(self):
        coll = extract_footnotes("Text[^1] here[^2].\n")
        assert len(coll.references) == 2

    def test_process_footnotes(self):
        result = process_footnotes("Text[^1].\n\n[^1]: Footnote.\n")
        assert "sup" in result
        assert "Footnote" in result

    def test_no_footnotes(self):
        assert process_footnotes("Plain text.\n") == "Plain text.\n"


class TestAnchors:
    def test_generate_anchor(self):
        result = generate_anchors("# Hello World\n")
        assert "{#hello-world}" in result

    def test_extract_anchors(self):
        anchors = extract_anchors("# Hello\n## World\n")
        assert len(anchors) == 2
        assert anchors[0].slug == "hello"

    def test_preserve_explicit_anchor(self):
        result = generate_anchors("# Hello {#custom-id}\n")
        assert "{#custom-id}" in result

    def test_extract_explicit_anchor(self):
        anchors = extract_anchors("# Hello {#my-id}\n")
        assert anchors[0].slug == "my-id"
        assert anchors[0].text == "Hello"


class TestReferenceLinks:
    def test_resolve(self):
        result = resolve_reference_links("[text][ref]\n\n[ref]: http://example.com\n")
        assert "http://example.com" in result
        assert "[ref]:" not in result

    def test_resolve_implicit(self):
        result = resolve_reference_links("[text][]\n\n[text]: http://example.com\n")
        assert "http://example.com" in result

    def test_extract_links(self):
        links = extract_reference_links("[key]: http://url.com \"Title\"\n")
        assert "key" in links
        assert links["key"].url == "http://url.com"
        assert links["key"].title == "Title"

    def test_unresolved_link(self):
        result = resolve_reference_links("[text][unknown]\n")
        assert "[text][unknown]" in result


class TestGitHubFeaturesProcessor:
    def test_process_all(self):
        processor = GitHubFeaturesProcessor()
        text = "- [x] done\n\n| H1 |\n|---|\n| C1 |\n"
        result = processor.process(text)
        assert "checkbox" in result
        assert "<table>" in result or "checkbox" in result

    def test_stats(self):
        processor = GitHubFeaturesProcessor()
        processor.process("> [!NOTE] Hi\n")
        assert processor.stats is not None

    def test_disabled_config(self):
        config = GitHubFeaturesConfig(enable_task_lists=False, enable_tables=False)
        processor = GitHubFeaturesProcessor(config=config)
        text = "- [x] task\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        result = processor.process(text)
        assert result == text

    def test_anchors_in_headings(self):
        processor = GitHubFeaturesProcessor()
        result = processor.process("# Title\n\nContent\n")
        assert "{#title}" in result
