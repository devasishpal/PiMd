"""Cross-platform PDF export with graceful fallback chain."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from pimd.export.models import ExportFormat, ExportResult


def _find_pdf_engine() -> str | None:
    """Detect available PDF conversion engine.

    Priority: docx2pdf (Win/Mac) → libreoffice → pandoc → weasyprint (HTML→PDF)
    """
    # Check docx2pdf (Windows/macOS native)
    if sys.platform == "win32":
        try:
            import docx2pdf  # noqa: F401

            return "docx2pdf"
        except ImportError:
            pass
    # Check LibreOffice
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
    # Check soffice (LibreOffice alternative name on some systems)
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
    # Check pandoc
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
    # Check weasyprint
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
        # For MD/HTML, convert to DOCX first (handled externally), then to PDF
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
    # Check individual engines
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
