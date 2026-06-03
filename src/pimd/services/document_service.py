"""Document model operations — merge, split, transform."""

from __future__ import annotations

from typing import Any

from pimd.models import Document, Heading, Paragraph, Span


class DocumentService:
    """Operations on PiMD's internal document model.

    Useful for programmatic manipulation of documents before rendering.
    """

    @staticmethod
    def merge(documents: list[Document]) -> Document:
        """Merge multiple documents into one, preserving block order."""
        blocks: list[Any] = []
        for doc in documents:
            blocks.extend(doc.blocks)
        return Document(blocks=blocks)

    @staticmethod
    def add_heading(doc: Document, text: str, level: int = 1) -> Document:
        """Append a heading to the document."""
        doc.blocks.append(Heading(level=level, spans=[Span(text=text)]))
        return doc

    @staticmethod
    def add_paragraph(doc: Document, text: str) -> Document:
        """Append a paragraph to the document."""
        doc.blocks.append(Paragraph(spans=[Span(text=text)]))
        return doc

    @staticmethod
    def wrap_in_blockquote(doc: Document) -> Document:
        """Wrap all blocks in a single blockquote."""
        from pimd.models import Blockquote

        quoted = Blockquote(children=list(doc.blocks))
        doc.blocks = [quoted]
        return doc

    @staticmethod
    def block_count(doc: Document) -> int:
        """Return the total number of blocks recursively."""
        return len(doc.blocks)

    @staticmethod
    def find_headings(doc: Document, level: int | None = None) -> list[Heading]:
        """Return all headings, optionally filtered by level."""
        return [
            b for b in doc.blocks if isinstance(b, Heading) and (level is None or b.level == level)
        ]
