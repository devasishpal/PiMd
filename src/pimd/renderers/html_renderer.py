"""HTML renderer — converts Document model to HTML5 output."""

from __future__ import annotations

from html import escape

from pimd.models import (
    Block,
    Blockquote,
    BulletList,
    CodeBlock,
    Diagram,
    Document,
    EquationBlock,
    Heading,
    HorizontalRule,
    Image,
    ListItem,
    OrderedList,
    Paragraph,
    Span,
    Table,
)


class HtmlRenderer:
    """Render a Document model to an HTML5 string."""

    def render(self, document: Document, title: str = "") -> str:
        """Render the document to a complete HTML5 page."""
        body = self.render_blocks(document.blocks)
        title_tag = f"<title>{escape(title)}</title>" if title else ""
        css = self._css()
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{title_tag}
<style>
{css}
</style>
</head>
<body>
{body}
</body>
</html>"""

    def render_blocks(self, blocks: list[Block]) -> str:
        """Render a sequence of blocks to HTML."""
        parts: list[str] = []
        for block in blocks:
            parts.append(self.render_block(block))
        return "\n".join(parts)

    def render_block(self, block: Block) -> str:
        """Render a single block to HTML."""
        if isinstance(block, Heading):
            level = min(max(block.level, 1), 6)
            return f"<h{level}>{self._render_spans(block.spans)}</h{level}>"
        elif isinstance(block, Paragraph):
            return f"<p>{self._render_spans(block.spans)}</p>"
        elif isinstance(block, CodeBlock):
            lang = f' class="language-{escape(block.language)}"' if block.language else ""
            return f"<pre{lang}><code>{escape(block.code)}</code></pre>"
        elif isinstance(block, Blockquote):
            inner = self.render_blocks(block.children)
            return f"<blockquote>\n{inner}\n</blockquote>"
        elif isinstance(block, BulletList):
            items = "\n".join(self._render_list_item(item) for item in block.items)
            return f"<ul>\n{items}\n</ul>"
        elif isinstance(block, OrderedList):
            start = f' start="{block.start}"' if block.start != 1 else ""
            items = "\n".join(self._render_list_item(item) for item in block.items)
            return f"<ol{start}>\n{items}\n</ol>"
        elif isinstance(block, ListItem):
            inner = self.render_blocks(block.children)
            return f"<li>{inner}</li>"
        elif isinstance(block, Table):
            return self._render_table(block)
        elif isinstance(block, HorizontalRule):
            return "<hr>"
        elif isinstance(block, Image):
            alt = escape(block.alt)
            src = escape(block.url)
            title = f' title="{escape(block.title)}"' if block.title else ""
            return f'<figure><img src="{src}" alt="{alt}"{title}></figure>'
        elif isinstance(block, Diagram):
            return f'<figure class="figure"><p>[Diagram: {escape(block.language)}]</p>\
<figcaption class="figure-caption">{escape(block.caption or block.alt)}</figcaption></figure>'
        elif isinstance(block, EquationBlock):
            return f'<div class="equation">\\[{escape(block.svg or block.latex)}\\]</div>'
        return ""

    @staticmethod
    def _css() -> str:
        return (
            "  body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px; "
            "margin: 2em auto; padding: 0 1em; line-height: 1.6; color: #222; }\n"
            "  h1, h2, h3, h4, h5, h6 { color: #1F4E79; margin-top: 1.5em; }\n"
            "  code { background: #f0f0f0; padding: 2px 5px; border-radius: 3px; "
            "font-size: 0.9em; }\n"
            "  pre { background: #f5f5f5; padding: 1em; border-radius: 5px; "
            "overflow-x: auto; }\n"
            "  pre code { background: none; padding: 0; }\n"
            "  blockquote { border-left: 4px solid #1F4E79; margin: 1em 0; "
            "padding: 0.5em 1em; background: #f9f9f9; }\n"
            "  table { border-collapse: collapse; width: 100%; margin: 1em 0; }\n"
            "  th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }\n"
            "  th { background: #1F4E79; color: white; }\n"
            "  img { max-width: 100%; height: auto; }\n"
            "  .equation { text-align: center; margin: 1em 0; font-style: italic; }\n"
            "  .figure-caption { text-align: center; font-style: italic; "
            "color: #555; margin-top: 0.5em; }\n"
        )

    def _render_spans(self, spans: list[Span]) -> str:
        """Render inline spans to HTML."""
        parts: list[str] = []
        for span in spans:
            if span.math:
                text = f"\\({escape(span.math)}\\)"
            else:
                text = escape(span.text)
            if span.code:
                text = f"<code>{text}</code>"
            if span.bold:
                text = f"<strong>{text}</strong>"
            if span.italic:
                text = f"<em>{text}</em>"
            if span.underline:
                text = f"<u>{text}</u>"
            if span.link_url:
                url = escape(span.link_url)
                text = f'<a href="{url}">{text}</a>'
            parts.append(text)
        return "".join(parts)

    def _render_list_item(self, item: ListItem) -> str:
        """Render a single list item."""
        inner = self.render_blocks(item.children)
        return f"<li>{inner}</li>"

    def _render_table(self, table: Table) -> str:
        """Render a table to HTML."""
        rows: list[str] = []
        if table.headers:
            header_cells = "".join(f"<th>{escape(h)}</th>" for h in table.headers)
            rows.append(f"<thead><tr>{header_cells}</tr></thead>")
        body_rows: list[str] = []
        for row in table.rows:
            cells = "".join(f"<td>{escape(c)}</td>" for c in row)
            body_rows.append(f"<tr>{cells}</tr>")
        if body_rows:
            rows.append(f"<tbody>{''.join(body_rows)}</tbody>")
        return f"<table>\n{''.join(rows)}\n</table>"
