"""Multi-format export converter — convert to DOCX, PDF, HTML, MD, RTF, ODT, TXT."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pimd.export.models import ExportFormat, ExportOptions, ExportResult
from pimd.export.pdf import convert_to_pdf


class ExportConverter:
    """Central converter for multi-format output.

    Converts input documents (Markdown/HTML) to any supported format.
    """

    def __init__(self, options: ExportOptions | None = None) -> None:
        self.options = options or ExportOptions()
        self._warnings: list[str] = []

    @property
    def warnings(self) -> list[str]:
        return list(self._warnings)

    def convert(
        self,
        input_path: str | Path,
        output_format: str | ExportFormat,
        output_path: str | Path | None = None,
        **overrides: Any,
    ) -> ExportResult:
        """Convert a document to the specified output format.

        Args:
            input_path: Path to the input file (MD or HTML).
            output_format: Target format (docx, pdf, html, md, rtf, odt, txt).
            output_path: Optional explicit output path. Auto-derived if omitted.
            **overrides: Additional export options (template, brand, cover_page, etc.).

        Returns:
            ExportResult with output path and status.
        """
        from pimd.api import PiMD

        fmt = ExportFormat(output_format) if isinstance(output_format, str) else output_format
        inp = Path(input_path)
        out_dir = Path(output_path).parent if output_path else inp.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        opts = ExportOptions(**(self.options.__dict__ | overrides))

        engine = PiMD()
        input_ext = inp.suffix.lower()

        # Special handling for PDF → produce DOCX first, then convert
        if fmt == ExportFormat.PDF:
            docx_path = out_dir / f"{inp.stem}_temp.docx"
            result = self._convert_to_docx(engine, inp, docx_path, input_ext, opts)
            if not result.success:
                return result
            return convert_to_pdf(
                docx_path,
                out_dir,
                source_format="docx",
                engine=opts.pdf_engine,
            )

        # Direct formats
        fmt_map: dict[ExportFormat, str] = {
            ExportFormat.DOCX: ".docx",
            ExportFormat.HTML: ".html",
            ExportFormat.MD: ".md",
            ExportFormat.TXT: ".txt",
        }
        ext = fmt_map.get(fmt, ".docx")
        out_path = Path(output_path) if output_path else (out_dir / f"{inp.stem}{ext}")

        if fmt == ExportFormat.DOCX:
            result = self._convert_to_docx(engine, inp, out_path, input_ext, opts)
        elif fmt == ExportFormat.HTML:
            result = self._convert_to_html(engine, inp, out_path, input_ext)
        elif fmt == ExportFormat.MD:
            result = self._convert_to_markdown(inp, out_path)
        elif fmt == ExportFormat.TXT:
            result = self._convert_to_text(inp, out_path)
        elif fmt in (ExportFormat.RTF, ExportFormat.ODT):
            # Produce DOCX first, then convert externally
            docx_path = out_dir / f"{inp.stem}_temp.docx"
            dresult = self._convert_to_docx(engine, inp, docx_path, input_ext, opts)
            if not dresult.success:
                return dresult
            result = self._convert_via_libreoffice(docx_path, out_path, fmt)
        else:
            result = ExportResult(
                output_path=out_path,
                format=fmt,
                success=False,
                error=f"Unsupported format: {fmt}",
            )

        return result

    def _convert_to_docx(
        self,
        engine: Any,
        inp: Path,
        out_path: Path,
        ext: str,
        opts: ExportOptions,
    ) -> ExportResult:
        """Convert input to DOCX."""
        try:
            if ext in (".md", ".markdown"):
                engine.md_to_docx(str(inp), str(out_path))
            elif ext in (".html", ".htm"):
                engine.html_to_docx(str(inp), str(out_path))
            else:
                return ExportResult(
                    output_path=out_path,
                    format=ExportFormat.DOCX,
                    success=False,
                    error=f"Unsupported input format: {ext}",
                )
            return ExportResult(
                output_path=out_path,
                format=ExportFormat.DOCX,
                success=True,
            )
        except Exception as exc:
            return ExportResult(
                output_path=out_path,
                format=ExportFormat.DOCX,
                success=False,
                error=str(exc),
            )

    def _convert_to_html(self, engine: Any, inp: Path, out_path: Path, ext: str) -> ExportResult:
        """Convert a DOCX or MD file back to HTML."""
        try:
            from pimd.converters.markdown import MarkdownConverter
            from pimd.renderers.html_renderer import HtmlRenderer

            if ext in (".md", ".markdown"):
                converter = MarkdownConverter()
                doc = converter.parse_text(inp.read_text(encoding="utf-8"))
            elif ext in (".html", ".htm"):
                out_path.write_text(inp.read_text(encoding="utf-8"), encoding="utf-8")
                return ExportResult(output_path=out_path, format=ExportFormat.HTML, success=True)
            else:
                return ExportResult(
                    output_path=out_path,
                    format=ExportFormat.HTML,
                    success=False,
                    error=f"Cannot convert {ext} to HTML",
                )
            renderer = HtmlRenderer()
            html = renderer.render(doc)
            out_path.write_text(html, encoding="utf-8")
            return ExportResult(output_path=out_path, format=ExportFormat.HTML, success=True)
        except Exception as exc:
            return ExportResult(
                output_path=out_path,
                format=ExportFormat.HTML,
                success=False,
                error=str(exc),
            )

    def _convert_to_markdown(self, inp: Path, out_path: Path) -> ExportResult:
        """Passthrough or convert to Markdown."""
        try:
            if inp.suffix.lower() in (".md", ".markdown"):
                out_path.write_text(inp.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                # Remove HTML tags for plain text → basic md
                from pimd.converters.markdown import MarkdownConverter

                converter = MarkdownConverter()
                doc = converter.parse_text(inp.read_text(encoding="utf-8"))
                md_lines: list[str] = []
                for block in doc.blocks:
                    md_lines.append(block.plain_text() + "\n")
                out_path.write_text("\n".join(md_lines), encoding="utf-8")
            return ExportResult(output_path=out_path, format=ExportFormat.MD, success=True)
        except Exception as exc:
            return ExportResult(
                output_path=out_path,
                format=ExportFormat.MD,
                success=False,
                error=str(exc),
            )

    def _convert_to_text(self, inp: Path, out_path: Path) -> ExportResult:
        """Strip all formatting and output plain text."""
        try:
            from pimd.converters.markdown import MarkdownConverter

            converter = MarkdownConverter()
            doc = converter.parse_text(inp.read_text(encoding="utf-8"))
            text_lines: list[str] = []
            for block in doc.blocks:
                text_lines.append(block.plain_text())
            out_path.write_text("\n".join(text_lines), encoding="utf-8")
            return ExportResult(output_path=out_path, format=ExportFormat.TXT, success=True)
        except Exception as exc:
            return ExportResult(
                output_path=out_path,
                format=ExportFormat.TXT,
                success=False,
                error=str(exc),
            )

    def _convert_via_libreoffice(
        self,
        docx_path: Path,
        out_path: Path,
        fmt: ExportFormat,
    ) -> ExportResult:
        """Use LibreOffice to convert DOCX to RTF or ODT."""
        import subprocess

        target_ext = fmt.value
        try:
            proc = subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to",
                    target_ext,
                    "--outdir",
                    str(out_path.parent),
                    str(docx_path),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            expected = out_path.parent / f"{docx_path.stem}.{target_ext}"
            return ExportResult(
                output_path=out_path if out_path.exists() else expected,
                format=fmt,
                success=expected.is_file() or out_path.exists(),
                error=proc.stderr.strip() if not expected.is_file() else None,
            )
        except Exception as exc:
            return ExportResult(
                output_path=out_path,
                format=fmt,
                success=False,
                error=str(exc),
            )
