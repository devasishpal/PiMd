"""PiMD public API — library-first interface for all conversions."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from pimd.caching import CacheBackend, MemoryCache
from pimd.exceptions import ConversionError
from pimd.observability import ConversionReport
from pimd.plugins import PluginManager
from pimd.safety import SafetyLimits
from pimd.services import ConversionResult, ConversionService
from pimd.themes.base import Theme


class PiMD:
    """Primary public API for PiMD.

    Library-first design. CLI and future REST APIs both delegate to this class.

    Usage::

        from pimd import PiMD

        engine = PiMD()

        # File -> File
        engine.md_to_docx("guide.md", "guide.docx")

        # Text -> File
        engine.md_text_to_docx("# Hello", "hello.docx")

        # Text -> Bytes (memory mode, no filesystem writes)
        docx_bytes = engine.md_text_to_docx_bytes("# Hello")

        # Async
        await engine.async_md_to_docx("guide.md", "guide.docx")
    """

    def __init__(
        self,
        theme: Theme | None = None,
        cache: CacheBackend | None = None,
        limits: SafetyLimits | None = None,
        plugins: PluginManager | None = None,
        enable_cache: bool = True,
    ) -> None:
        self._cache: CacheBackend | None
        if cache is not None:
            self._cache = cache
        elif enable_cache:
            self._cache = MemoryCache(default_ttl=300)
        else:
            self._cache = None

        self._service = ConversionService(
            theme=theme,
            cache=self._cache,
            limits=limits,
            plugins=plugins,
        )

    # ======================================================================
    # Sync — file input
    # ======================================================================

    def md_to_docx(
        self,
        input_file: str | Path,
        output_file: str | Path,
        **options: Any,
    ) -> ConversionResult:
        """Convert a Markdown file to a DOCX file.

        Args:
            input_file: Path to the input ``.md`` file.
            output_file: Path where the output ``.docx`` will be written.
            **options: Rendering options passed to the renderer.

        Returns:
            A :class:`ConversionResult` with path and report.
        """
        return self._service.convert_markdown(
            Path(input_file), output_path=Path(output_file), **options
        )

    def html_to_docx(
        self,
        input_file: str | Path,
        output_file: str | Path,
        **options: Any,
    ) -> ConversionResult:
        """Convert an HTML file to a DOCX file.

        Args:
            input_file: Path to the input ``.html`` file.
            output_file: Path where the output ``.docx`` will be written.
            **options: Rendering options passed to the renderer.

        Returns:
            A :class:`ConversionResult` with path and report.
        """
        return self._service.convert_html(
            Path(input_file), output_path=Path(output_file), **options
        )

    # ======================================================================
    # Sync — text input → file
    # ======================================================================

    def md_text_to_docx(
        self,
        markdown_text: str,
        output_file: str | Path,
        **options: Any,
    ) -> ConversionResult:
        """Convert a Markdown string to a DOCX file.

        Args:
            markdown_text: Raw Markdown text.
            output_file: Path where the output ``.docx`` will be written.
            **options: Rendering options passed to the renderer.

        Returns:
            A :class:`ConversionResult` with path and report.
        """
        return self._service.convert_markdown(
            markdown_text, output_path=Path(output_file), **options
        )

    def html_text_to_docx(
        self,
        html_text: str,
        output_file: str | Path,
        **options: Any,
    ) -> ConversionResult:
        """Convert an HTML string to a DOCX file.

        Args:
            html_text: Raw HTML text.
            output_file: Path where the output ``.docx`` will be written.
            **options: Rendering options passed to the renderer.

        Returns:
            A :class:`ConversionResult` with path and report.
        """
        return self._service.convert_html(html_text, output_path=Path(output_file), **options)

    # ======================================================================
    # Sync — text input → bytes (memory mode)
    # ======================================================================

    def md_text_to_docx_bytes(
        self,
        markdown_text: str,
        **options: Any,
    ) -> bytes:
        """Convert a Markdown string to DOCX bytes.

        No filesystem writes. Ideal for web frameworks.

        Args:
            markdown_text: Raw Markdown text.
            **options: Rendering options passed to the renderer.

        Returns:
            The DOCX file contents as ``bytes``.
        """
        result = self._service.convert_markdown(markdown_text, **options)
        if result.output_bytes is None:
            raise ConversionError("Memory mode conversion returned no bytes")
        return result.output_bytes

    def html_text_to_docx_bytes(
        self,
        html_text: str,
        **options: Any,
    ) -> bytes:
        """Convert an HTML string to DOCX bytes.

        No filesystem writes. Ideal for web frameworks.

        Args:
            html_text: Raw HTML text.
            **options: Rendering options passed to the renderer.

        Returns:
            The DOCX file contents as ``bytes``.
        """
        result = self._service.convert_html(html_text, **options)
        if result.output_bytes is None:
            raise ConversionError("Memory mode conversion returned no bytes")
        return result.output_bytes

    # ======================================================================
    # Async — wrappers around sync methods
    # ======================================================================

    async def async_md_to_docx(
        self,
        input_file: str | Path,
        output_file: str | Path,
        **options: Any,
    ) -> ConversionResult:
        """Async version of :meth:`md_to_docx`."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.md_to_docx, input_file, output_file, **options)

    async def async_html_to_docx(
        self,
        input_file: str | Path,
        output_file: str | Path,
        **options: Any,
    ) -> ConversionResult:
        """Async version of :meth:`html_to_docx`."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.html_to_docx, input_file, output_file, **options
        )

    async def async_md_text_to_docx(
        self,
        markdown_text: str,
        output_file: str | Path,
        **options: Any,
    ) -> ConversionResult:
        """Async version of :meth:`md_text_to_docx`."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.md_text_to_docx, markdown_text, output_file, **options
        )

    async def async_html_text_to_docx(
        self,
        html_text: str,
        output_file: str | Path,
        **options: Any,
    ) -> ConversionResult:
        """Async version of :meth:`html_text_to_docx`."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.html_text_to_docx, html_text, output_file, **options
        )

    async def async_md_text_to_docx_bytes(
        self,
        markdown_text: str,
        **options: Any,
    ) -> bytes:
        """Async version of :meth:`md_text_to_docx_bytes`."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.md_text_to_docx_bytes, markdown_text, **options
        )

    async def async_html_text_to_docx_bytes(
        self,
        html_text: str,
        **options: Any,
    ) -> bytes:
        """Async version of :meth:`html_text_to_docx_bytes`."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.html_text_to_docx_bytes, html_text, **options)

    # ======================================================================
    # Utilities
    # ======================================================================

    @property
    def last_report(self) -> ConversionReport | None:
        """Return the report from the most recent conversion."""
        return self._service.last_report

    def get_report(self) -> ConversionReport | None:
        """Alias for :attr:`last_report`."""
        return self.last_report

    def clear_cache(self) -> None:
        """Clear the internal cache (if enabled)."""
        if self._cache:
            self._cache.clear()

    @property
    def service(self) -> ConversionService:
        """Direct access to the underlying conversion service."""
        return self._service
