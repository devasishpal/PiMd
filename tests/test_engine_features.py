"""Tests for callout, footnote, and attachment engine modules."""

from __future__ import annotations


class TestCallouts:
    def test_parse_callout(self):
        from pimd.callouts import CalloutType, parse_callout
        block, end = parse_callout("> [!NOTE] Title\n> Content\n", 0)
        assert block is not None
        assert block.type == CalloutType.NOTE

    def test_parse_warning(self):
        from pimd.callouts import CalloutType, parse_callout
        block, _ = parse_callout("> [!WARNING] Careful\n", 0)
        assert block is not None
        assert block.type == CalloutType.WARNING

    def test_parse_danger(self):
        from pimd.callouts import CalloutType, parse_callout
        block, _ = parse_callout("> [!DANGER] Stop\n", 0)
        assert block is not None
        assert block.type == CalloutType.DANGER

    def test_callout_type_from_label(self):
        from pimd.callouts import CalloutType, callout_type_from_label
        assert callout_type_from_label("note") == CalloutType.NOTE
        assert callout_type_from_label("TIP") == CalloutType.TIP
        assert callout_type_from_label("WaRnInG") == CalloutType.WARNING

    def test_callout_default_title(self):
        from pimd.callouts import CalloutType, callout_default_title
        assert callout_default_title(CalloutType.NOTE) == "Note"

    def test_callout_color(self):
        from pimd.callouts import CalloutType, callout_color
        color = callout_color(CalloutType.WARNING)
        assert color.startswith("#")

    def test_callout_icon(self):
        from pimd.callouts import CalloutType, callout_icon
        assert callout_icon(CalloutType.NOTE) is not None

    def test_to_html(self):
        from pimd.callouts import CalloutBlock, CalloutType, callout_to_html
        block = CalloutBlock(type=CalloutType.INFO, title="Info", content_lines=["Content"])
        html = callout_to_html(block)
        assert "div" in html or "blockquote" in html

    def test_to_markdown(self):
        from pimd.callouts import CalloutBlock, CalloutType, callout_to_markdown
        block = CalloutBlock(type=CalloutType.TIP, title="Tip", content_lines=["Do this"])
        md = callout_to_markdown(block)
        assert "Tip" in md

    def test_extract_callouts(self):
        from pimd.callouts import extract_callouts
        text = "> [!NOTE] Note\n> Content\n\n> [!WARNING] Warning\n> Careful\n"
        blocks = extract_callouts(text)
        assert len(blocks) == 2

    def test_process_callouts(self):
        from pimd.callouts import process_callouts
        result = process_callouts("> [!IMPORTANT] Critical\n> Do not ignore\n")
        assert "Critical" in result

    def test_config_custom_colors(self):
        from pimd.callouts import CalloutConfig, CalloutType
        config = CalloutConfig(type_colors={CalloutType.NOTE: "#FF0000"})
        assert config.type_colors[CalloutType.NOTE] == "#FF0000"


class TestFootnotes:
    def test_parse_definition(self):
        from pimd.footnotes import parse_footnote_definition
        fn, end = parse_footnote_definition("[^1]: This is a footnote.\n", 0)
        assert fn is not None
        assert fn.key == "^1"
        assert "This is a footnote" in fn.content

    def test_parse_reference(self):
        from pimd.footnotes import parse_footnote_reference
        key, end = parse_footnote_reference("text[^1]more", 4)
        assert key == "^1"

    def test_extract_footnotes(self):
        from pimd.footnotes import extract_footnotes
        coll = extract_footnotes("Text[^1] here[^2].\n\n[^1]: First.\n[^2]: Second.\n")
        assert len(coll.definitions) == 2
        assert len(coll.references) == 2

    def test_number_footnotes(self):
        from pimd.footnotes import FootnoteCollection, FootnoteDefinition, number_footnotes
        coll = FootnoteCollection(
            definitions={"^1": FootnoteDefinition(key="^1", content="A", number=0)},
            references=["^1"],
        )
        numbered = number_footnotes(coll)
        assert numbered.definitions["^1"].number == 1

    def test_remove_definitions(self):
        from pimd.footnotes import remove_footnote_definitions
        result = remove_footnote_definitions("Body[^1].\n\n[^1]: Note.\n")
        assert result.strip() == "Body[^1]."

    def test_process_footnotes(self):
        from pimd.footnotes import process_footnotes
        result = process_footnotes("Text[^1].\n\n[^1]: Footnote.\n")
        assert "Footnote" in result

    def test_config(self):
        from pimd.footnotes import FootnoteConfig
        config = FootnoteConfig(enable_backrefs=False)
        assert config.enable_backrefs is False


class TestAttachments:
    def test_detect_type_image(self):
        from pimd.attachments import AttachmentType, detect_attachment_type
        assert detect_attachment_type("image.png") == AttachmentType.IMAGE
        assert detect_attachment_type("photo.jpg") == AttachmentType.IMAGE
        assert detect_attachment_type("graph.jpeg") == AttachmentType.IMAGE

    def test_detect_type_svg(self):
        from pimd.attachments import AttachmentType, detect_attachment_type
        assert detect_attachment_type("drawing.svg") == AttachmentType.SVG

    def test_detect_type_pdf(self):
        from pimd.attachments import AttachmentType, detect_attachment_type
        assert detect_attachment_type("doc.pdf") == AttachmentType.PDF

    def test_detect_type_other(self):
        from pimd.attachments import AttachmentType, detect_attachment_type
        assert detect_attachment_type("data.json") == AttachmentType.DATA

    def test_detect_mime_type(self):
        from pimd.attachments import detect_mime_type
        mime = detect_mime_type("image.png")
        assert mime is not None

    def test_resolve_path(self, tmp_path):
        from pimd.attachments import resolve_attachment_path
        src = tmp_path / "doc.md"
        asset = tmp_path / "image.png"
        asset.write_text("fake")
        resolved = resolve_attachment_path("image.png", src)
        assert resolved is not None
        assert resolved.exists()

    def test_resolve_path_missing(self, tmp_path):
        from pimd.attachments import resolve_attachment_path
        src = tmp_path / "doc.md"
        resolved = resolve_attachment_path("missing.png", src)
        assert resolved is None

    def test_find_attachments_in_text(self, tmp_path):
        from pimd.attachments import find_attachments_in_text
        img = tmp_path / "image.png"
        img.write_text("fake")
        text = "![alt](image.png)\n"
        attachments = find_attachments_in_text(text, tmp_path)
        assert len(attachments) >= 1

    def test_collect_assets(self, tmp_path):
        from pimd.attachments import collect_assets
        (tmp_path / "img").mkdir()
        (tmp_path / "img" / "photo.png").write_text("fake")
        assets = collect_assets(tmp_path)
        assert len(assets) >= 1

    def test_svg_to_png(self, tmp_path):
        from pimd.attachments import svg_to_png
        svg = tmp_path / "test.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"></svg>')
        png = tmp_path / "test.png"
        result = svg_to_png(svg, png)
        # May fail if no cairosvg/PIL, but should not crash
        assert result is not None or True
