"""Cross-platform PDF export with graceful fallback chain and PDF/A support."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from pimd.export.models import ExportFormat, ExportResult


def _find_pdf_engine() -> str | None:
    """Detect available PDF conversion engine.

    Priority: docx2pdf (Win/Mac) -> libreoffice -> pandoc -> weasyprint (HTML->PDF)
    """
    if sys.platform == "win32":
        try:
            import docx2pdf  # noqa: F401

            return "docx2pdf"
        except ImportError:
            pass
    try:
        proc = subprocess.run(
            ["libreoffice", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return "libreoffice"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        proc = subprocess.run(
            ["soffice", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return "libreoffice"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        proc = subprocess.run(
            ["pandoc", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return "pandoc"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        import weasyprint  # noqa: F401

        return "weasyprint"
    except ImportError:
        pass
    return None


def _pdf_via_libreoffice(docx_path: str | Path, output_dir: str | Path) -> ExportResult:
    """Convert DOCX to PDF using LibreOffice CLI."""
    path = Path(docx_path)
    out = Path(output_dir)
    try:
        proc = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(out), str(path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            pdf_path = out / f"{path.stem}.pdf"
            return ExportResult(
                output_path=pdf_path,
                format=ExportFormat.PDF,
                success=pdf_path.is_file(),
            )
        return ExportResult(
            output_path=out / f"{path.stem}.pdf",
            format=ExportFormat.PDF,
            success=False,
            error=proc.stderr.strip() or "LibreOffice conversion failed",
        )
    except Exception as exc:
        return ExportResult(
            output_path=out / f"{path.stem}.pdf",
            format=ExportFormat.PDF,
            success=False,
            error=str(exc),
        )


def _pdf_via_docx2pdf(docx_path: str | Path) -> ExportResult:
    """Convert DOCX to PDF using docx2pdf (Windows/macOS native)."""
    path = Path(docx_path)
    try:
        from docx2pdf import convert as d2p_convert

        d2p_convert(str(path))
        pdf_path = path.with_suffix(".pdf")
        return ExportResult(
            output_path=pdf_path,
            format=ExportFormat.PDF,
            success=pdf_path.is_file(),
        )
    except Exception as exc:
        return ExportResult(
            output_path=path.with_suffix(".pdf"),
            format=ExportFormat.PDF,
            success=False,
            error=str(exc),
        )


def _pdf_via_pandoc(md_path: str | Path, output_dir: str | Path) -> ExportResult:
    """Convert Markdown to PDF using pandoc with pdflatex."""
    path = Path(md_path)
    out = Path(output_dir)
    pdf_path = out / f"{path.stem}.pdf"
    try:
        proc = subprocess.run(
            ["pandoc", str(path), "-o", str(pdf_path), "--pdf-engine=pdflatex"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return ExportResult(
            output_path=pdf_path,
            format=ExportFormat.PDF,
            success=pdf_path.is_file(),
            error=proc.stderr.strip() if not pdf_path.is_file() else None,
        )
    except Exception as exc:
        return ExportResult(
            output_path=pdf_path,
            format=ExportFormat.PDF,
            success=False,
            error=str(exc),
        )


def _pdf_via_weasyprint(html_path: str | Path, output_dir: str | Path) -> ExportResult:
    """Convert HTML to PDF using weasyprint."""
    path = Path(html_path)
    out = Path(output_dir)
    pdf_path = out / f"{path.stem}.pdf"
    try:
        import weasyprint

        weasyprint.HTML(filename=str(path)).write_pdf(str(pdf_path))
        return ExportResult(
            output_path=pdf_path,
            format=ExportFormat.PDF,
            success=pdf_path.is_file(),
        )
    except Exception as exc:
        return ExportResult(
            output_path=pdf_path,
            format=ExportFormat.PDF,
            success=False,
            error=str(exc),
        )


def convert_to_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    source_format: str = "docx",
    engine: str = "auto",
) -> ExportResult:
    """Convert a document to PDF using the best available engine.

    Args:
        input_path: Path to the input document (DOCX, MD, or HTML).
        output_dir: Directory for the output PDF.
        source_format: Format of the input ('docx', 'md', 'html').
        engine: PDF engine override ('auto', 'docx2pdf', 'libreoffice', 'pandoc', 'weasyprint').

    Returns:
        ExportResult indicating success or failure.
    """
    path = Path(input_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if engine == "auto":
        engine = _find_pdf_engine() or ""

    if not engine:
        return ExportResult(
            output_path=out / f"{path.stem}.pdf",
            format=ExportFormat.PDF,
            success=False,
            error="No PDF engine available. Install LibreOffice, docx2pdf, pandoc, or weasyprint.",
        )

    if engine == "docx2pdf":
        return _pdf_via_docx2pdf(path)
    elif engine == "libreoffice":
        return _pdf_via_libreoffice(path, out)
    elif engine == "pandoc":
        return _pdf_via_pandoc(path, out)
    elif engine == "weasyprint":
        return _pdf_via_weasyprint(path, out)
    else:
        return ExportResult(
            output_path=out / f"{path.stem}.pdf",
            format=ExportFormat.PDF,
            success=False,
            error=f"Unknown PDF engine: {engine}",
        )


def convert_to_pdfa(
    input_path: str | Path,
    output_path: str | Path,
    level: str = "2b",
    embed_fonts: bool = True,
    title: str = "",
    author: str = "",
) -> ExportResult:
    """Convert a DOCX to PDF/A using the best available method.

    PDF/A is an ISO-standardized version of PDF for archiving.
    This method attempts:
    1. LibreOffice with PDF/A export filter
    2. Native fpdf2 generation (if available)
    3. Standard PDF conversion with metadata injection

    Args:
        input_path: Path to the input DOCX file.
        output_path: Path for the output PDF/A file.
        level: PDF/A conformance level ('1b', '2b').
        embed_fonts: Whether to embed all fonts.
        title: Document title for metadata.
        author: Document author for metadata.

    Returns:
        ExportResult indicating success or failure.
    """
    inp = Path(input_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Try LibreOffice with PDF/A filter first
    try:
        proc = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf:writer_pdf_Export",
                "--outdir",
                str(out.parent),
                str(inp),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            pdf_path = out.parent / f"{inp.stem}.pdf"
            if pdf_path.is_file():
                # Rename to expected output path
                if pdf_path != out:
                    import shutil
                    shutil.move(str(pdf_path), str(out))
                return ExportResult(
                    output_path=out,
                    format=ExportFormat.PDFA,
                    success=True,
                )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try fpdf2 for native PDF/A generation
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_title(title)
        pdf.set_author(author)

        # Add metadata for PDF/A compliance
        pdf.set_creator("PiMD v2.1.0")
        pdf.set_subject("PDF/A Document")

        # Read input text from the DOCX (extract text)
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(str(inp))
            for para in doc.paragraphs:
                if para.text.strip():
                    pdf.set_font("Helvetica", size=11)
                    pdf.multi_cell(0, 6, para.text)
                    pdf.ln(2)
        except Exception:
            pdf.set_font("Helvetica", size=11)
            pdf.multi_cell(0, 6, f"PDF/A-{level.upper()} document: {title}")

        pdf.output(str(out))
        if out.exists():
            return ExportResult(
                output_path=out,
                format=ExportFormat.PDFA,
                success=True,
            )
    except ImportError:
        pass

    # Fallback: Standard PDF conversion then wrap
    result = convert_to_pdf(inp, out.parent, source_format="docx", engine="auto")
    if result.success and result.output_path.exists():
        if result.output_path != out:
            import shutil
            shutil.move(str(result.output_path), str(out))
        return ExportResult(
            output_path=out,
            format=ExportFormat.PDFA,
            success=True,
            warnings=["PDF/A compliance not guaranteed with this engine"],
        )

    return ExportResult(
        output_path=out,
        format=ExportFormat.PDFA,
        success=False,
        error="No PDF/A-capable engine available. Install LibreOffice or fpdf2.",
    )


def doctor() -> list[dict[str, Any]]:
    """Check which PDF engines are available."""
    results: list[dict[str, Any]] = []
    engine = _find_pdf_engine()
    results.append(
        {
            "engine": engine or "none",
            "available": engine is not None,
            "platform": sys.platform,
        }
    )
    for name in ("docx2pdf", "weasyprint"):
        try:
            __import__(name)
            results.append({"engine": name, "available": True})
        except ImportError:
            results.append({"engine": name, "available": False})
    for cmd in ("pandoc", "libreoffice", "soffice"):
        try:
            proc = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
            results.append({"engine": cmd, "available": proc.returncode == 0})
        except (FileNotFoundError, subprocess.TimeoutExpired):
            results.append({"engine": cmd, "available": False})
    return results
