"""HTML → DOCX conversion orchestration."""

from pathlib import Path

from pimd.exceptions import ConversionError
from pimd.models import DocumentStatistics
from pimd.parsers.html_parser import HTMLParser
from pimd.renderers.docx_renderer import DocxRenderer
from pimd.themes import ProfessionalTheme
from pimd.themes.base import Theme
from pimd.utils.logging import get_logger

logger = get_logger(__name__)


class HTMLConverter:
    """Convert HTML files or strings to DOCX documents.

    Usage::

        converter = HTMLConverter()
        converter.convert("input.html", "output.docx")
        converter.convert_text("<h1>Hello</h1>", "hello.docx")

    Parameters
    ----------
    theme : Theme, optional
        Visual theme for the generated DOCX. Defaults to ProfessionalTheme.
    """

    def __init__(self, theme: Theme | None = None) -> None:
        self._parser = HTMLParser()
        self._renderer = DocxRenderer(theme or ProfessionalTheme())
        self._statistics: DocumentStatistics = DocumentStatistics()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(
        self,
        input_file: str | Path,
        output_file: str | Path,
        *,
        generate_toc: bool = False,
        page_numbers: bool = False,
        header_text: str | None = None,
        footer_text: str | None = None,
        cover_page: bool = False,
        title: str | None = None,
        author: str | None = None,
        company: str | None = None,
        subject: str | None = None,
        keywords: list[str] | None = None,
        doc_version: str | None = None,
    ) -> None:
        """Convert an HTML file to a DOCX document.

        Args:
            input_file: Path to the input ``.html`` file.
            output_file: Path where the output ``.docx`` will be written.
            generate_toc: Insert a Word table of contents field.
            page_numbers: Add page numbers to every page footer.
            header_text: Repeating header text for every page.
            footer_text: Repeating footer text (ignored if page_numbers=True).
            cover_page: Prepend a title page.
            title: Document title (metadata + cover page).
            author: Document author (metadata + cover page).
            company: Company / organisation name (metadata).
            subject: Document subject (metadata).
            keywords: List of keywords (metadata).
            doc_version: Version string shown on the cover page.

        Raises:
            ConversionError: If the input file does not exist or conversion fails.
        """
        src = Path(input_file)
        if not src.exists():
            raise ConversionError(f"Input file not found: {input_file}")

        logger.info("Converting: %s \u2192 %s", src, output_file)

        content = src.read_text(encoding="utf-8")
        document = self._parser.parse(content)

        self._renderer.render(
            document,
            output_file,
            generate_toc=generate_toc,
            page_numbers=page_numbers,
            header_text=header_text,
            footer_text=footer_text,
            cover_page=cover_page,
            title=title,
            author=author,
            company=company,
            subject=subject,
            keywords=keywords,
            doc_version=doc_version,
        )

    def convert_text(
        self,
        html_text: str,
        output_file: str | Path,
        *,
        generate_toc: bool = False,
        page_numbers: bool = False,
        header_text: str | None = None,
        footer_text: str | None = None,
        cover_page: bool = False,
        title: str | None = None,
        author: str | None = None,
        company: str | None = None,
        subject: str | None = None,
        keywords: list[str] | None = None,
        doc_version: str | None = None,
    ) -> None:
        """Convert an HTML string directly to a DOCX document.

        Accepts the same keyword arguments as :meth:`convert`.
        """
        logger.info("Converting text \u2192 %s", output_file)

        document = self._parser.parse(html_text)

        self._renderer.render(
            document,
            output_file,
            generate_toc=generate_toc,
            page_numbers=page_numbers,
            header_text=header_text,
            footer_text=footer_text,
            cover_page=cover_page,
            title=title,
            author=author,
            company=company,
            subject=subject,
            keywords=keywords,
            doc_version=doc_version,
        )

    def get_statistics(self) -> DocumentStatistics:
        """Return the statistics from the most recent conversion run."""
        return self._statistics


def html_to_docx(input_file: str, output_file: str) -> None:
    """Convenience function — convert an HTML file to DOCX in one call.

    Args:
        input_file: Path to the input ``.html`` file.
        output_file: Path where the output ``.docx`` will be written.
    """
    HTMLConverter().convert(input_file, output_file)
