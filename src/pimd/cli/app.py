"""PiMD Typer application — all CLI commands."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import typer
from rich.table import Table
from typer.core import TyperGroup

from pimd import __version__
from pimd.cli.config import load_config, write_default_config
from pimd.cli.display import (
    StepDisplay,
    console,
    display_error,
    doctor_table,
    info_table,
    show_banner,
    show_sub_banner,
)
from pimd.exceptions import PiMDError

# ------------------------------------------------------------------
# Logger
# ------------------------------------------------------------------

logger = logging.getLogger("pimd")


# ------------------------------------------------------------------
# Custom group that shows the banner on no-args
# ------------------------------------------------------------------


class BannerGroup(TyperGroup):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._banner_shown = False

    def list_commands(self, ctx: typer.Context) -> list[str]:
        if not self._banner_shown:
            show_banner()
            self._banner_shown = True
        return super().list_commands(ctx)


# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------

app = typer.Typer(
    name="pimd",
    cls=BannerGroup,
    help="Professional Markdown and HTML to DOCX conversion framework",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=False,
)


# ======================================================================
# Global callback
# ======================================================================


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose / debug output",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit",
    ),
) -> None:
    # --version flag
    if version:
        console.print(f"PiMD v{__version__}")
        raise typer.Exit()

    # Verbose mode
    if verbose:
        logging.getLogger("pimd").setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")


# ======================================================================
# Helper — run a conversion with steps display
# ======================================================================


def _run_conversion(
    input_path: Path,
    output_path: Path,
    input_format: str,
    **kwargs: object,
) -> None:
    steps = StepDisplay()
    steps.add("Reading file")
    steps.add("Parsing")
    steps.add("Rendering")
    steps.add("Writing DOCX")

    start = time.monotonic()
    try:
        steps.start("Reading file")
        from pimd import PiMD

        engine = PiMD(enable_cache=False)
        steps.succeed("Reading file")

        config = load_config()

        steps.start("Parsing")
        steps.succeed("Parsing")

        steps.start("Rendering")

        # Build options dict, merging CLI args with config defaults
        gen_opts = {
            "generate_toc": kwargs.get("generate_toc", False),
            "page_numbers": kwargs.get("page_numbers", False),
            "header_text": kwargs.get("header_text"),
            "footer_text": kwargs.get("footer_text"),
            "cover_page": kwargs.get("cover_page", False),
            "title": kwargs.get("title"),
            "author": kwargs.get("author"),
            "company": kwargs.get("company") or config.get("defaults", {}).get("company", ""),
            "subject": kwargs.get("subject"),
            "keywords": kwargs.get("keywords"),
            "doc_version": kwargs.get("doc_version"),
        }
        # Merge author from config if not provided
        if not gen_opts["author"]:
            gen_opts["author"] = config.get("defaults", {}).get("author", "")

        if input_format == "markdown":
            engine.md_to_docx(input_path, output_path, **gen_opts)
        else:
            engine.html_to_docx(input_path, output_path, **gen_opts)

        steps.succeed("Rendering")

        steps.start("Writing DOCX")
        steps.succeed("Writing DOCX")

        elapsed = time.monotonic() - start
        steps.complete(str(output_path), elapsed)

    except PiMDError as exc:
        steps.fail("Rendering")
        display_error(
            "Conversion Error",
            str(exc),
            hint="Check the input file and ensure all dependencies are installed.",
        )
        raise typer.Exit(code=1) from exc
    except FileNotFoundError as exc:
        display_error("File Not Found", str(exc))
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        steps.fail("Rendering")
        logger.exception("Unhandled error")
        display_error("Unexpected Error", str(exc))
        raise typer.Exit(code=1) from exc


# ======================================================================
# pimd md
# ======================================================================


@app.command()
def md(
    input: Path = typer.Argument(
        ...,
        help="Path to input .md file",
        exists=True,
        dir_okay=False,
    ),
    output: Path = typer.Argument(
        ...,
        help="Path to output .docx file",
    ),
    toc: bool = typer.Option(False, "--toc", help="Generate table of contents"),
    page_numbers: bool = typer.Option(
        False,
        "--page-numbers",
        help="Add page numbers",
    ),
    cover: bool = typer.Option(False, "--cover", help="Add cover page"),
    title: str | None = typer.Option(None, "--title", help="Document title"),
    author: str | None = typer.Option(None, "--author", help="Document author"),
    company: str | None = typer.Option(None, "--company", help="Company name"),
    subject: str | None = typer.Option(None, "--subject", help="Document subject"),
    keywords: str | None = typer.Option(
        None,
        "--keywords",
        help="Comma-separated keywords",
    ),
    doc_version: str | None = typer.Option(
        None,
        "--version",
        help="Document version",
    ),
    header: str | None = typer.Option(None, "--header", help="Header text"),
    footer: str | None = typer.Option(None, "--footer", help="Footer text"),
) -> None:
    """Convert a Markdown file to DOCX."""
    show_sub_banner("md")

    kw: list[str] | None = None
    if keywords:
        kw = [k.strip() for k in keywords.split(",") if k.strip()]

    _run_conversion(
        input,
        output,
        input_format="markdown",
        generate_toc=toc,
        page_numbers=page_numbers,
        header_text=header,
        footer_text=footer,
        cover_page=cover,
        title=title,
        author=author,
        company=company,
        subject=subject,
        keywords=kw,
        doc_version=doc_version,
    )


# ======================================================================
# pimd html
# ======================================================================


@app.command()
def html(
    input: Path = typer.Argument(
        ...,
        help="Path to input .html file",
        exists=True,
        dir_okay=False,
    ),
    output: Path = typer.Argument(
        ...,
        help="Path to output .docx file",
    ),
    toc: bool = typer.Option(False, "--toc", help="Generate table of contents"),
    page_numbers: bool = typer.Option(
        False,
        "--page-numbers",
        help="Add page numbers",
    ),
    cover: bool = typer.Option(False, "--cover", help="Add cover page"),
    title: str | None = typer.Option(None, "--title", help="Document title"),
    author: str | None = typer.Option(None, "--author", help="Document author"),
    company: str | None = typer.Option(None, "--company", help="Company name"),
    subject: str | None = typer.Option(None, "--subject", help="Document subject"),
    keywords: str | None = typer.Option(
        None,
        "--keywords",
        help="Comma-separated keywords",
    ),
    doc_version: str | None = typer.Option(
        None,
        "--version",
        help="Document version",
    ),
    header: str | None = typer.Option(None, "--header", help="Header text"),
    footer: str | None = typer.Option(None, "--footer", help="Footer text"),
) -> None:
    """Convert an HTML file to DOCX."""
    show_sub_banner("html")

    kw: list[str] | None = None
    if keywords:
        kw = [k.strip() for k in keywords.split(",") if k.strip()]

    _run_conversion(
        input,
        output,
        input_format="html",
        generate_toc=toc,
        page_numbers=page_numbers,
        header_text=header,
        footer_text=footer,
        cover_page=cover,
        title=title,
        author=author,
        company=company,
        subject=subject,
        keywords=kw,
        doc_version=doc_version,
    )


# ======================================================================
# pimd info
# ======================================================================


@app.command()
def info() -> None:
    """Display PiMD version, themes, and supported formats."""
    show_sub_banner("info")

    from pimd.themes import ProfessionalTheme

    data = {
        "Version": __version__,
        "Python": sys.version.split()[0],
        "Platform": sys.platform,
        "Supported formats": "DOCX, PDF, PDF/A, EPUB, LaTeX, HTML, MD, RTF, ODT, TXT",
        "Installed templates": "professional, academic, technical, business, book, proposal, invoice, resume, manual, api",
        "Report types": "executive, technical, audit, project, research, compliance, architecture",
        "Citation styles": "APA, IEEE, MLA, Chicago, Harvard",
        "Default theme": ProfessionalTheme().name,
        "EPUB": "Supported (v2.1.0)",
        "LaTeX": "Supported (v2.1.0)",
        "PDF/A": "Supported (v2.1.0)",
        "i18n": "RTL, CJK, Unicode (v2.1.0)",
        "Collaborative editing": "Revisions, comments, annotations (v2.1.0)",
        "Config location": str(import_path("pimd.cli.config").get_config_path()),
    }

    info_table(data)


# ======================================================================
# pimd doctor
# ======================================================================


@app.command()
def doctor() -> None:
    """Run system diagnostics."""
    show_sub_banner("doctor")

    results: list[dict[str, str]] = []

    # -- Python version --
    py_ver = sys.version_info
    if py_ver >= (3, 10):
        results.append(
            {
                "check": "Python version",
                "status": "ok",
                "detail": f"Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}",
            }
        )
    else:
        results.append(
            {
                "check": "Python version",
                "status": "error",
                "detail": f"Python {py_ver.major}.{py_ver.minor} — need >= 3.10",
            }
        )

    # -- Dependencies --
    deps = [
        ("python-docx", "docx"),
        ("markdown-it-py", "markdown_it"),
        ("beautifulsoup4", "bs4"),
        ("lxml", "lxml"),
        ("typer", "typer"),
        ("rich", "rich"),
    ]
    for display_name, import_name in deps:
        try:
            mod = __import__(import_name)
            ver = getattr(mod, "__version__", "installed")
            results.append(
                {
                    "check": display_name,
                    "status": "ok",
                    "detail": str(ver),
                }
            )
        except ImportError:
            results.append(
                {
                    "check": display_name,
                    "status": "error",
                    "detail": "Not installed",
                }
            )

    # -- Config directory --
    from pimd.cli.config import get_config_path

    cfg = get_config_path()
    if cfg.exists():
        results.append(
            {
                "check": "Config file",
                "status": "ok",
                "detail": str(cfg),
            }
        )
    else:
        write_default_config()
        results.append(
            {
                "check": "Config file",
                "status": "warning",
                "detail": "Created default config at " + str(cfg),
            }
        )

    # -- Output directory writable --
    cwd = Path.cwd()
    try:
        test_file = cwd / ".pimd_write_test"
        test_file.write_text("test")
        test_file.unlink()
        results.append(
            {
                "check": "Output directory",
                "status": "ok",
                "detail": str(cwd),
            }
        )
    except OSError:
        results.append(
            {
                "check": "Output directory",
                "status": "error",
                "detail": f"Cannot write to {cwd}",
            }
        )

    doctor_table(results)


# ======================================================================
# pimd version
# ======================================================================


@app.command(name="version")
def version_cmd() -> None:
    """Show PiMD version and system information."""
    import platform

    from pimd import __version__

    console.print(f"PiMD v{__version__}")
    console.print(f"  Python: {platform.python_version()} ({platform.architecture()[0]})")
    console.print(f"  Platform: {platform.system()} {platform.release()}")
    console.print("  License: MIT")


# ======================================================================
# pimd diagrams
# ======================================================================

diagrams_app = typer.Typer(
    name="diagrams",
    help="Diagram rendering tools (Mermaid, PlantUML, Graphviz, D2, BlockDiag, Vega, BPMN, ASCII)",
    no_args_is_help=True,
)
app.add_typer(diagrams_app, name="diagrams")


@diagrams_app.command(name="list")
def diagrams_list() -> None:
    """List available diagram renderers and their status."""
    from pimd.diagrams.renderers import (
        ActDiagRenderer,
        AsciiRenderer,
        BlockDiagRenderer,
        D2Renderer,
        GraphvizRenderer,
        MermaidRenderer,
        NwDiagRenderer,
        PacketDiagRenderer,
        PlantUMLRenderer,
        SeqDiagRenderer,
        SvgRenderer,
    )

    show_sub_banner("diagrams list")

    renderers = [
        MermaidRenderer(),
        PlantUMLRenderer(),
        GraphvizRenderer(),
        D2Renderer(),
        AsciiRenderer(),
        SvgRenderer(),
        BlockDiagRenderer(),
        SeqDiagRenderer(),
        ActDiagRenderer(),
        NwDiagRenderer(),
        PacketDiagRenderer(),
    ]

    rows: list[dict[str, str]] = []
    for r in renderers:
        avail = r.is_available()
        rows.append(
            {
                "language": r.language,
                "renderer": r.name,
                "available": "yes" if avail else "no",
                "description": r.description,
            }
        )

    from rich.table import Table

    from pimd.cli.display import console as csl

    table = Table(title="Diagram Renderers")
    table.add_column("Language", style="cyan")
    table.add_column("Renderer", style="green")
    table.add_column("Available", style="bold")
    table.add_column("Description")
    for row in rows:
        table.add_row(
            row["language"],
            row["renderer"],
            "[green]Y[/]" if row["available"] == "yes" else "[red]X[/]",
            row["description"],
        )
    csl.print(table)


@diagrams_app.command(name="test")
def diagrams_test(
    language: str = typer.Argument(
        ...,
        help="Diagram language to test (mermaid, plantuml, dot, d2, ascii, svg)",
    ),
) -> None:
    """Render a test diagram to verify a renderer works."""
    from pimd.diagrams import DiagramEngine, DiagramRegistry

    show_sub_banner(f"diagrams test [cyan]{language}[/]")

    registry = DiagramRegistry()
    try:
        renderer = _load_renderer(language)
    except ValueError as exc:
        display_error("Unknown renderer", str(exc))
        raise typer.Exit(code=1) from exc

    registry.register(renderer)
    engine = DiagramEngine(registry=registry)

    test_source = _test_source_for(language)
    result = engine.render(test_source, language)

    if result.error:
        display_error("Render failed", result.error)
        raise typer.Exit(code=1)

    console.print(f"[green]Y[/] {language} diagram rendered successfully")
    if result.png:
        console.print(f"  PNG: {len(result.png)} bytes")
    if result.svg:
        svg_len = len(result.svg)
        console.print(f"  SVG: {svg_len} bytes")


@diagrams_app.command(name="cache-clear")
def diagrams_cache_clear() -> None:
    """Clear the diagram cache (memory and filesystem)."""

    show_sub_banner("diagrams cache-clear")
    console.print("Diagram cache clearing is handled by the engine instance.")


@diagrams_app.command(name="doctor")
def diagrams_doctor() -> None:
    """Diagnose diagram rendering tools on the system."""
    from pimd.cli.display import doctor_table
    from pimd.diagrams.renderers import (
        ActDiagRenderer,
        AsciiRenderer,
        BlockDiagRenderer,
        D2Renderer,
        GraphvizRenderer,
        MermaidRenderer,
        NwDiagRenderer,
        PacketDiagRenderer,
        PlantUMLRenderer,
        SeqDiagRenderer,
        SvgRenderer,
    )

    show_sub_banner("diagrams doctor")

    results: list[dict[str, str]] = []
    renderers = [
        MermaidRenderer(),
        PlantUMLRenderer(),
        GraphvizRenderer(),
        D2Renderer(),
        AsciiRenderer(),
        SvgRenderer(),
        BlockDiagRenderer(),
        SeqDiagRenderer(),
        ActDiagRenderer(),
        NwDiagRenderer(),
        PacketDiagRenderer(),
    ]

    for r in renderers:
        avail = r.is_available()
        results.append(
            {
                "check": f"{r.name} (language: {r.language})",
                "status": "ok" if avail else "warning",
                "detail": "Available" if avail else "Not installed — see docs",
            }
        )

    # Check Pillow availability for ASCII
    try:
        __import__("PIL")
        results.append(
            {
                "check": "Pillow (ASCII diagrams)",
                "status": "ok",
                "detail": "installed",
            }
        )
    except ImportError:
        results.append(
            {
                "check": "Pillow (ASCII diagrams)",
                "status": "warning",
                "detail": "Not installed — pip install Pillow",
            }
        )

    doctor_table(results)


def _load_renderer(language: str):  # noqa: ANN202
    from pimd.diagrams.renderers import (
        ActDiagRenderer,
        AsciiRenderer,
        BlockDiagRenderer,
        D2Renderer,
        GraphvizRenderer,
        MermaidRenderer,
        NwDiagRenderer,
        PacketDiagRenderer,
        PlantUMLRenderer,
        SeqDiagRenderer,
        SvgRenderer,
    )

    mapping = {
        "mermaid": MermaidRenderer,
        "plantuml": PlantUMLRenderer,
        "dot": GraphvizRenderer,
        "d2": D2Renderer,
        "ascii": AsciiRenderer,
        "svg": SvgRenderer,
        "blockdiag": BlockDiagRenderer,
        "seqdiag": SeqDiagRenderer,
        "actdiag": ActDiagRenderer,
        "nwdiag": NwDiagRenderer,
        "packetdiag": PacketDiagRenderer,
    }
    cls = mapping.get(language.lower())
    if not cls:
        raise ValueError(f"Unknown language '{language}'. Supported: {', '.join(sorted(mapping))}")
    return cls()


def _test_source_for(language: str) -> str:
    sources = {
        "mermaid": "graph TD\n    A[Start] --> B[End]\n",
        "plantuml": "@startuml\nAlice -> Bob: Hello\n@enduml\n",
        "dot": "digraph G { A -> B }\n",
        "d2": "a -> b\n",
        "ascii": "+-------+     +-------+\n| Hello | --> | World |\n+-------+     +-------+",
        "svg": '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
        '<rect width="100" height="50" fill="blue"/></svg>',
        "blockdiag": 'blockdiag {\n  A -> B;\n}',
        "seqdiag": 'seqdiag {\n  A -> B;\n}',
        "actdiag": 'actdiag {\n  A -> B;\n}',
        "nwdiag": 'nwdiag {\n  A -> B;\n}',
        "packetdiag": 'packetdiag {\n  A -> B;\n}',
    }
    return sources.get(language.lower(), "")


# ======================================================================
# pimd equations
# ======================================================================

equations_app = typer.Typer(
    name="equations",
    help="Equation rendering tools (LaTeX, OMML, MathJax, KaTeX)",
    no_args_is_help=True,
)
app.add_typer(equations_app, name="equations")


@equations_app.command(name="list")
def equations_list() -> None:
    """List supported equation formats and rendering backends."""
    show_sub_banner("equations list")

    from rich.table import Table

    from pimd.cli.display import console as csl

    table = Table(title="Equation Support")
    table.add_column("Format", style="cyan")
    table.add_column("Support", style="green")
    table.add_column("Notes")

    table.add_row("LaTeX $...$", "Full", "Inline math")
    table.add_row("LaTeX $$...$$", "Full", "Display math")
    table.add_row(r"LaTeX \(...\)", "Full", "Inline (parens)")
    table.add_row(r"LaTeX \[...\]", "Full", "Display (brackets)")
    table.add_row(r"\begin{equation}", "Full", "Numbered equation")
    table.add_row(r"\begin{align}", "Full", "Multi-line aligned")
    table.add_row("MathJax", "Auto-detect", "Same delimiters as LaTeX")
    table.add_row("KaTeX", "Auto-detect", "Same delimiters as LaTeX")
    table.add_row("OMML (native)", "Built-in", "Editable in Word")
    table.add_row("SVG fallback", "Optional", "matplotlib required")
    table.add_row("Chemical formulas", "Full", r"H_2O, CO_2, CH_4, etc.")

    csl.print(table)


@equations_app.command(name="test")
def equations_test(
    latex: str = typer.Argument(..., help="LaTeX equation to test"),
    display: bool = typer.Option(False, "--display", "-d", help="Render as display equation"),
) -> None:
    """Test equation rendering with a LaTeX expression."""
    show_sub_banner("equations test")

    from pimd.equations import EquationEngine
    from pimd.equations.models import EquationConfig

    engine = EquationEngine(config=EquationConfig())
    result = engine.render(latex, display=display)

    if result.error:
        display_error("Render failed", result.error)
        raise typer.Exit(code=1)

    console.print("[green]Y[/] Equation rendered successfully")
    console.print(f"  OMML: {'yes' if result.has_omml else 'no'}")
    console.print(f"  SVG:  {'yes (' + str(len(result.svg)) + ' bytes)' if result.svg else 'no'}")
    console.print(f"  Time: {result.render_time:.4f}s")
    if result.number is not None:
        console.print(f"  Number: ({result.number})")


@equations_app.command(name="doctor")
def equations_doctor() -> None:
    """Diagnose equation rendering capabilities on the system."""
    from pimd.cli.display import doctor_table

    show_sub_banner("equations doctor")

    from pimd.equations import EquationEngine

    engine = EquationEngine()
    results = engine.doctor()

    # Additional checks
    try:
        __import__("matplotlib")
        results.append(
            {
                "check": "matplotlib (SVG rendering)",
                "status": "ok",
                "detail": "Available",
            }
        )
    except ImportError:
        results.append(
            {
                "check": "matplotlib (SVG rendering)",
                "status": "warning",
                "detail": "Not installed — pip install matplotlib",
            }
        )

    doctor_table(results)


# ======================================================================
# pimd template
# ======================================================================

templates_app = typer.Typer(
    name="template",
    help="Template management (list, info, validate)",
    no_args_is_help=True,
)
app.add_typer(templates_app, name="template")


@templates_app.command(name="list")
def template_list() -> None:
    """List available document templates."""
    show_sub_banner("template list")
    from pimd.templates import TemplateManager

    mgr = TemplateManager()
    templates = mgr.list_templates()
    if not templates:
        console.print("[yellow]No templates found[/]")
        return
    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Version")
    table.add_column("Description")
    for t in templates:
        table.add_row(t.name, t.type.value, t.metadata.version, t.metadata.description[:60])
    console.print(table)


@templates_app.command(name="info")
def template_info(
    name: str = typer.Argument(..., help="Template name"),
) -> None:
    """Show details for a specific template."""
    show_sub_banner(f"template info [cyan]{name}[/]")
    from pimd.templates import TemplateManager

    mgr = TemplateManager()
    tpl = mgr.get(name)
    if tpl is None:
        display_error("Not found", f"Template '{name}' not found")
        raise typer.Exit(code=1)
    data = {
        "Name": tpl.name,
        "Type": tpl.type.value,
        "Version": tpl.metadata.version,
        "Description": tpl.metadata.description,
        "Author": tpl.metadata.author,
        "Page Size": tpl.config.page_size,
        "Font": f"{tpl.config.default_font} {tpl.config.default_font_size}pt",
        "Line Spacing": str(tpl.config.line_spacing),
        "TOC": "Yes" if tpl.config.generate_toc else "No",
        "Cover Page": "Yes" if tpl.config.cover_page else "No",
        "Page Numbers": "Yes" if tpl.config.page_numbers else "No",
    }
    info_table(data)


@templates_app.command(name="validate")
def template_validate(
    name: str = typer.Argument(..., help="Template name to validate"),
) -> None:
    """Validate a template's configuration."""
    show_sub_banner(f"template validate [cyan]{name}[/]")
    from pimd.templates import TemplateManager

    mgr = TemplateManager()
    result = mgr.validate(name)
    if result.valid:
        console.print(f"[green]Y[/] Template '{name}' is valid")
    for w in result.warnings:
        console.print(f"[yellow]![/] {w}")
    for e in result.errors:
        console.print(f"[red]X[/] {e}")


# ======================================================================
# pimd brand
# ======================================================================

brand_app = typer.Typer(
    name="brand",
    help="Brand management (set, show, apply branding)",
    no_args_is_help=True,
)
app.add_typer(brand_app, name="brand")


@brand_app.command(name="set")
def brand_set(
    source: str = typer.Argument(
        ...,
        help="Path to brand config file (JSON/TOML) or directory",
    ),
) -> None:
    """Load a brand identity from a config file."""
    show_sub_banner("brand set")
    try:
        from pimd.branding import BrandingManager

        mgr = BrandingManager()
        mgr.load(source)
        console.print(f"[green]Y[/] Brand loaded: {mgr.brand.name if mgr.brand else '?'}")
    except Exception as exc:
        display_error("Brand load failed", str(exc))
        raise typer.Exit(code=1) from exc


@brand_app.command(name="show")
def brand_show() -> None:
    """Display current brand identity."""
    show_sub_banner("brand show")
    from pimd.branding import BrandingManager

    mgr = BrandingManager()
    brand = mgr.brand
    if brand is None:
        console.print("[yellow]No brand loaded. Use 'pimd brand set <path>'[/]")
        return
    data = {
        "Name": brand.name,
        "Company": brand.metadata.company,
        "Author": brand.metadata.author,
        "Primary Color": f"#{brand.config.primary_color}",
        "Secondary Color": f"#{brand.config.secondary_color}",
        "Font": brand.config.font_family,
        "Logo": brand.config.logo_path or "(none)",
        "Website": brand.config.website,
    }
    info_table(data)


# ======================================================================
# pimd export
# ======================================================================

export_app = typer.Typer(
    name="export",
    help="Export documents to multiple formats (PDF, DOCX, HTML, MD, RTF, ODT, TXT)",
    no_args_is_help=True,
)
app.add_typer(export_app, name="export")


@export_app.command(name="docx")
def export_docx(
    input: Path = typer.Argument(..., help="Input file (.md or .html)", exists=True),
    output: Path = typer.Argument(..., help="Output .docx path"),
    template: str = typer.Option("", "--template", help="Template name"),
    cover: bool = typer.Option(False, "--cover", help="Add cover page"),
    toc: bool = typer.Option(False, "--toc", help="Generate table of contents"),
) -> None:
    """Export to DOCX."""
    from pimd.export import ExportConverter

    result = ExportConverter().convert(
        input, "docx", output, template=template, cover_page=cover, generate_toc=toc
    )
    if result.success:
        console.print(f"[green]Y[/] Exported to {result.output_path}")
    else:
        display_error("Export failed", result.error or "")
        raise typer.Exit(code=1)


@export_app.command(name="pdf")
def export_pdf(
    input: Path = typer.Argument(..., help="Input file (.md, .html, or .docx)", exists=True),
    output: Path = typer.Argument(..., help="Output .pdf path"),
    engine: str = typer.Option(
        "auto", "--engine", help="PDF engine (auto, docx2pdf, libreoffice, pandoc, weasyprint)"
    ),
) -> None:
    """Export to PDF using the best available engine."""
    from pimd.export import ExportConverter

    result = ExportConverter().convert(input, "pdf", output, pdf_engine=engine)
    if result.success:
        console.print(f"[green]Y[/] Exported to {result.output_path}")
    else:
        display_error("PDF export failed", result.error or "")
        raise typer.Exit(code=1)


@export_app.command(name="html")
def export_html(
    input: Path = typer.Argument(..., help="Input file (.md)", exists=True),
    output: Path = typer.Argument(..., help="Output .html path"),
) -> None:
    """Export to HTML."""
    from pimd.export import ExportConverter

    result = ExportConverter().convert(input, "html", output)
    if result.success:
        console.print(f"[green]Y[/] Exported to {result.output_path}")
    else:
        display_error("Export failed", result.error or "")
        raise typer.Exit(code=1)


@export_app.command(name="txt")
def export_txt(
    input: Path = typer.Argument(..., help="Input file (.md)", exists=True),
    output: Path = typer.Argument(..., help="Output .txt path"),
) -> None:
    """Export to plain text."""
    from pimd.export import ExportConverter

    result = ExportConverter().convert(input, "txt", output)
    if result.success:
        console.print(f"[green]Y[/] Exported to {result.output_path}")
    else:
        display_error("Export failed", result.error or "")
        raise typer.Exit(code=1)


@export_app.command(name="doctor")
def export_doctor() -> None:
    """Diagnose available export engines."""
    from pimd.cli.display import doctor_table
    from pimd.export.pdf import doctor as pdf_doctor

    show_sub_banner("export doctor")

    # PDF engines
    results = pdf_doctor()
    rows = [
        {
            "check": r["engine"],
            "status": "ok" if r.get("available", False) else "warning",
            "detail": "Available" if r.get("available", False) else "Not installed",
        }
        for r in results
    ]

    # EPUB
    try:
        from pimd.export.formats.epub import EpubRenderer
        er = EpubRenderer()
        rows.append({
            "check": "EPUB renderer",
            "status": "ok" if er.is_available else "warning",
            "detail": "Available" if er.is_available else f"Missing: {', '.join(er.missing_dependencies)}",
        })
    except Exception:
        rows.append({"check": "EPUB renderer", "status": "warning", "detail": "Not available"})

    # LaTeX
    try:
        from pimd.export.formats.latex import LatexRenderer
        lr = LatexRenderer()
        rows.append({
            "check": "LaTeX renderer",
            "status": "ok" if lr.is_available else "warning",
            "detail": "Available" if lr.is_available else "Not available",
        })
    except Exception:
        rows.append({"check": "LaTeX renderer", "status": "warning", "detail": "Not available"})

    # PDF/A
    try:
        import fpdf2  # noqa: F401
        rows.append({"check": "PDF/A (fpdf2)", "status": "ok", "detail": "Available"})
    except ImportError:
        rows.append({"check": "PDF/A (fpdf2)", "status": "warning", "detail": "Not installed — use LibreOffice as fallback"})

    # i18n
    for mod_name in ("bidi", "arabic_reshaper"):
        try:
            __import__(mod_name)
            rows.append({"check": f"i18n ({mod_name})", "status": "ok", "detail": "Available"})
        except ImportError:
            rows.append({"check": f"i18n ({mod_name})", "status": "info", "detail": "Optional — install for RTL support"})

    doctor_table(rows)


# ======================================================================
# pimd report
# ======================================================================

report_app = typer.Typer(
    name="report",
    help="Generate professional reports (executive, technical, audit, project, research)",
    no_args_is_help=True,
)
app.add_typer(report_app, name="report")


@report_app.command(name="generate")
def report_generate(
    type: str = typer.Argument(
        ..., help="Report type (executive, technical, audit, project, research)"
    ),
    output: Path = typer.Argument(..., help="Output path (.docx)"),
    title: str = typer.Option("Report", "--title", help="Report title"),
    author: str = typer.Option("", "--author", help="Author name"),
    company: str = typer.Option("", "--company", help="Company name"),
    template: str = typer.Option("professional", "--template", help="Template name"),
) -> None:
    """Generate a structured report from a template."""
    show_sub_banner(f"report generate [cyan]{type}[/]")
    from pimd.reports import ReportConfig, ReportEngine, ReportType

    config = ReportConfig(
        type=ReportType(type),
        title=title,
        author=author,
        company=company,
        template=template,
        cover_page=True,
        generate_toc=True,
    )
    engine = ReportEngine(config=config)
    try:
        out = engine.generate(output)
        console.print(f"[green]Y[/] Report generated: {out}")
    except Exception as exc:
        display_error("Report generation failed", str(exc))
        raise typer.Exit(code=1) from exc


@report_app.command(name="list-types")
def report_list_types() -> None:
    """List available report types."""
    from pimd.reports import ReportEngine

    engine = ReportEngine()
    table = Table(title="Report Types")
    table.add_column("Type", style="cyan")
    table.add_column("Description")
    for rt in engine.list_types():
        table.add_row(rt["type"], rt["description"])
    console.print(table)


# ======================================================================
# pimd book
# ======================================================================

book_app = typer.Typer(
    name="book",
    help="Book compilation (chapters, parts, appendices)",
    no_args_is_help=True,
)
app.add_typer(book_app, name="book")


@book_app.command(name="compile")
def book_compile(
    config: Path = typer.Argument(
        ...,
        help="Path to book config file (JSON/TOML)",
        exists=True,
    ),
    output: Path = typer.Argument(..., help="Output .docx path"),
) -> None:
    """Compile a book from a configuration file."""
    show_sub_banner("book compile")
    import json

    import tomllib

    raw = config.read_text(encoding="utf-8")
    data = json.loads(raw) if config.suffix == ".json" else tomllib.loads(raw)
    from pimd.books import BookCompiler, BookConfig

    bk_cfg = BookConfig(**{k: v for k, v in data.items() if hasattr(BookConfig, k)})
    compiler = BookCompiler(config=bk_cfg)
    try:
        out = compiler.compile(output)
        console.print(f"[green]Y[/] Book compiled: {out}")
    except Exception as exc:
        display_error("Book compilation failed", str(exc))
        raise typer.Exit(code=1) from exc


# ======================================================================
# pimd citations
# ======================================================================

citations_app = typer.Typer(
    name="citations",
    help="Citation management (BibTeX, formatting, bibliography)",
    no_args_is_help=True,
)
app.add_typer(citations_app, name="citations")


@citations_app.command(name="load")
def citations_load(
    bibtex: Path = typer.Argument(..., help="Path to .bib file", exists=True),
    style: str = typer.Option("apa", "--style", help="Citation style (apa, ieee, mla, chicago)"),
) -> None:
    """Load a BibTeX file and preview formatted entries."""
    from pimd.citations import CitationEngine, CitationStyle

    engine = CitationEngine()
    engine.load_bibtex(bibtex)
    entries = engine.all_entries()
    console.print(f"[green]Y[/] Loaded {len(entries)} entries")
    for entry in entries[:5]:
        console.print(f"  [{entry.key}] {entry.format(CitationStyle(style))[:100]}")
    if len(entries) > 5:
        console.print(f"  ... and {len(entries) - 5} more")


@citations_app.command(name="bibliography")
def citations_bibliography(
    bibtex: Path = typer.Argument(..., help="Path to .bib file", exists=True),
    style: str = typer.Option("apa", "--style", help="Citation style"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file"),
) -> None:
    """Generate a formatted bibliography from a BibTeX file."""
    from pimd.citations import CitationEngine, CitationStyle

    engine = CitationEngine()
    engine.load_bibtex(bibtex)
    bibliography = engine.bibliography(CitationStyle(style))
    if output:
        Path(output).write_text(bibliography, encoding="utf-8")
        console.print(f"[green]Y[/] Bibliography written to {output}")
    else:
        console.print(bibliography)


# ======================================================================
# pimd merge
# ======================================================================


@app.command()
def merge(
    input_files: list[Path] = typer.Argument(
        ...,
        help="Input files to merge (.md or .html)",
    ),
    output: Path = typer.Argument(..., help="Output file (.docx)"),
    toc: bool = typer.Option(False, "--toc", help="Generate table of contents"),
    cover: bool = typer.Option(False, "--cover", help="Add cover page"),
) -> None:
    """Merge multiple documents into one."""
    show_sub_banner("merge")
    from pimd.merge import DocumentMerger

    merger = DocumentMerger()
    try:
        out = merger.merge(input_files, output, generate_toc=toc, cover_page=cover)
        console.print(f"[green]Y[/] Merged {len(input_files)} files into {out}")
    except Exception as exc:
        display_error("Merge failed", str(exc))
        raise typer.Exit(code=1) from exc


# ======================================================================
# pimd batch
# ======================================================================


@app.command()
def batch(
    input_dir: Path = typer.Argument(
        ...,
        help="Directory containing input files",
        exists=True,
    ),
    output_dir: Path = typer.Argument(..., help="Directory for output files"),
    pattern: str = typer.Option("*.md", "--pattern", help="File glob pattern"),
    format: str = typer.Option("docx", "--format", help="Output format"),
    workers: int = typer.Option(4, "--workers", help="Parallel workers"),
) -> None:
    """Batch-convert files in a directory (parallel)."""
    show_sub_banner("batch")
    from pimd.batch import BatchProcessor

    processor = BatchProcessor(max_workers=workers)
    result = processor.process_directory(
        input_dir, output_dir, pattern=pattern, output_format=format
    )
    console.print(result.summary())
    if result.failed > 0:
        raise typer.Exit(code=1)


# ======================================================================
# pimd validate
# ======================================================================


@app.command()
def validate(
    input: Path = typer.Argument(
        ...,
        help="Input file to validate (.md)",
        exists=True,
    ),
) -> None:
    """Validate a document for common issues."""
    show_sub_banner("validate")
    from pimd.validation import DocumentValidator

    validator = DocumentValidator()
    report = validator.validate_file(input)
    table = Table(title=f"Validation Report: {input.name}")
    table.add_column("Severity", style="bold")
    table.add_column("Type")
    table.add_column("Message")
    for issue in report.issues:
        severity_str = "[red]ERROR[/]" if issue.severity == "error" else "[yellow]WARN[/]"
        table.add_row(severity_str, issue.type, issue.message)
    if not report.issues:
        console.print(f"[green]Y[/] No issues found in {input}")
    else:
        console.print(table)
        console.print(report.summary())
    if not report.valid:
        raise typer.Exit(code=1)


# ======================================================================
# pimd project
# ======================================================================

project_app = typer.Typer(help="Convert entire documentation projects")
app.add_typer(project_app, name="project")


@project_app.command(name="convert")
def project_convert(
    input_dir: Path = typer.Argument(..., help="Input directory", exists=True),
    output_dir: Path = typer.Argument(..., help="Output directory"),
    format: str = typer.Option("docx", "--format", help="Output format"),
    merge: bool = typer.Option(False, "--merge", help="Merge all files into one"),
    pattern: str = typer.Option("*.md", "--pattern", help="File glob pattern"),
    workers: int = typer.Option(4, "--workers", help="Parallel workers"),
) -> None:
    """Convert all markdown files in a directory tree."""
    show_sub_banner("project convert")
    from pimd.project import ProjectConverter

    pc = ProjectConverter(incremental=True)
    result = pc.convert_project(
        input_dir,
        output_dir,
        merge=merge,
        output_format=format,
        pattern=pattern,
    )
    console.print("[green]Y[/] Project converted")
    console.print(
        f"  Total: {result.total_files}, Converted: {result.converted}, "
        f"Skipped: {result.skipped}, Failed: {result.failed}"
    )
    if result.errors:
        for path, err in result.errors[:10]:
            console.print(f"  [red]X[/] {path}: {err}")


# ======================================================================
# pimd config
# ======================================================================

config_app = typer.Typer(help="Manage configuration")
app.add_typer(config_app, name="config")


@config_app.command(name="show")
def config_show() -> None:
    """Show resolved configuration."""
    show_sub_banner("config show")
    from pimd.config import Config

    cfg = Config()
    cfg.load_global()
    cfg.load_project()
    resolved = cfg.resolve()
    data: dict[str, str] = {}
    for section, values in resolved.items():
        if isinstance(values, dict):
            for key, val in values.items():
                data[f"{section}.{key}"] = str(val)
        else:
            data[section] = str(values)
    info_table(data)


@config_app.command(name="path")
def config_path() -> None:
    """Show config file locations."""
    show_sub_banner("config path")
    from pimd.config import Config

    cfg = Config()
    files = cfg.find_config_files()
    if not files:
        console.print("[yellow]No config files found[/]")
    for f in files:
        console.print(f"  {f}")


@config_app.command(name="init")
def config_init(
    path: Path = typer.Argument(
        None,
        help="Output path (default: .pimdconfig in current directory)",
    ),
) -> None:
    """Generate a default configuration file."""
    show_sub_banner("config init")
    from pimd.config import Config

    if path is None:
        path = Path.cwd() / ".pimdconfig"
    Config.write_default(path)
    console.print(f"[green]Y[/] Default config written to {path}")


@config_app.command(name="validate")
def config_validate() -> None:
    """Validate the resolved configuration against the schema."""
    show_sub_banner("config validate")
    from pimd.config import Config

    cfg = Config()
    cfg.load_global()
    cfg.load_project()
    errors = cfg.validate()
    if not errors:
        console.print("[green]Y[/] Configuration is valid")
    else:
        console.print(f"[red]X[/] Found {len(errors)} configuration error(s):")
        for err in errors:
            console.print(f"  [red]-[/] {err}")


# ======================================================================
# pimd pipeline
# ======================================================================

pipeline_app = typer.Typer(help="Pipeline management")
app.add_typer(pipeline_app, name="pipeline")


@pipeline_app.command(name="list")
def pipeline_list() -> None:
    """List available pipeline stages."""
    show_sub_banner("pipeline list")
    from pimd.pipeline import StageType

    table = Table(title="Pipeline Stage Types")
    table.add_column("Type", style="cyan")
    table.add_column("Description")
    for st in StageType:
        table.add_row(st.value, st.value.replace("_", " ").title())
    console.print(table)


# ======================================================================
# pimd cache
# ======================================================================

cache_app = typer.Typer(help="Cache management")
app.add_typer(cache_app, name="cache")


@cache_app.command(name="clear")
def cache_clear() -> None:
    """Clear all caches."""
    show_sub_banner("cache clear")
    from pimd.caching.memory import MemoryCache

    MemoryCache().clear()
    try:
        from pimd.caching.redis_cache import RedisCacheBackend

        redis_cache = RedisCacheBackend()
        if redis_cache.is_available():
            redis_cache.clear()
            console.print("[green]Y[/] Redis cache cleared")
    except Exception:
        pass
    console.print("[green]Y[/] Memory cache cleared")


@cache_app.command(name="status")
def cache_status() -> None:
    """Show cache backend status."""
    show_sub_banner("cache status")
    from pimd.caching.redis_cache import RedisCacheBackend

    cache = RedisCacheBackend()
    status = cache.health_check()
    if status.get("available"):
        console.print("[green]Y[/] Redis: Connected")
    else:
        console.print("[yellow]X[/] Redis: Not available (using memory)")


@cache_app.command(name="info")
def cache_info() -> None:
    """Show cache statistics and diagnostics."""
    show_sub_banner("cache info")
    from pimd.caching.diagnostics import diagnose_cache, format_cache_info
    from pimd.caching.memory import MemoryCache

    cache = MemoryCache()
    info = diagnose_cache(cache)
    console.print(format_cache_info(info))


# ======================================================================
# pimd job
# ======================================================================

job_app = typer.Typer(help="Job system for background conversions")
app.add_typer(job_app, name="job")


@job_app.command(name="run")
def job_run(
    input: Path = typer.Argument(..., help="Input file", exists=True),
    output: Path = typer.Argument(..., help="Output path"),
) -> None:
    """Run a conversion as a tracked job."""
    show_sub_banner("job run")
    from pimd.jobs import JobManager

    jm = JobManager()
    job_id = jm.create_job(
        source_path=str(input),
        output_path=str(output),
    )
    result = jm.run_job(job_id)
    console.print(f"Job [cyan]{job_id}[/] completed: {result.status.value}")
    console.print(f"  Duration: {result.duration:.2f}s")
    if result.error:
        console.print(f"  [red]Error:[/] {result.error}")


@job_app.command(name="list")
def job_list() -> None:
    """List recent jobs."""
    show_sub_banner("job list")
    from pimd.jobs import JobManager

    jm = JobManager()
    summary = jm.get_status_summary()
    if not summary:
        console.print("[yellow]No jobs[/]")
        return
    table = Table(title="Job Summary")
    table.add_column("Status", style="cyan")
    table.add_column("Count")
    for status, count in summary.items():
        table.add_row(status, str(count))
    console.print(table)


# ======================================================================
# pimd profile
# ======================================================================

profile_app = typer.Typer(help="Performance profiling")
app.add_typer(profile_app, name="profile")


@profile_app.command(name="run")
def profile_run(
    input: Path = typer.Argument(..., help="Input file", exists=True),
) -> None:
    """Profile a conversion."""
    show_sub_banner("profile run")
    from pimd.profiling import profile_conversion

    content = input.read_text(encoding="utf-8")
    from pimd import PiMD

    engine = PiMD()
    result, report = profile_conversion(engine.md_text_to_docx_bytes, content)
    console.print(report.summary())


# ======================================================================
# pimd flavor
# ======================================================================


@app.command()
def flavor(
    input: Path = typer.Argument(
        ...,
        help="Input file to analyze",
        exists=True,
        dir_okay=False,
    ),
) -> None:
    """Detect the Markdown flavor of a file."""
    show_sub_banner("flavor")
    from pimd.compatibility import detect_flavor_from_file

    result = detect_flavor_from_file(input)
    console.print(
        f"[cyan]Flavor:[/] {result.flavor.value}  "
        f"[dim]({result.confidence:.0%} confidence)[/]"
    )
    if result.signals:
        for s in result.signals[:10]:
            console.print(f"  [dim]{s}[/]")


# ======================================================================
# pimd frontmatter
# ======================================================================


frontmatter_cmd = typer.Typer(help="Extract and manage document frontmatter")
app.add_typer(frontmatter_cmd, name="frontmatter")


@frontmatter_cmd.command(name="extract")
def frontmatter_extract(
    input: Path = typer.Argument(
        ...,
        help="Input file",
        exists=True,
        dir_okay=False,
    ),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format (text, json)"
    ),
) -> None:
    """Extract frontmatter metadata from a file."""
    show_sub_banner("frontmatter extract")
    from pimd.frontmatter import parse_frontmatter_from_file

    meta = parse_frontmatter_from_file(input)
    if format == "json":
        import json

        console.print(json.dumps(meta.to_dict(), indent=2, default=str))
    else:
        data = meta.to_dict()
        if not data:
            console.print("[yellow]No frontmatter found[/]")
            return
        info_table(data)


@frontmatter_cmd.command(name="strip")
def frontmatter_strip(
    input: Path = typer.Argument(
        ...,
        help="Input file",
        exists=True,
        dir_okay=False,
    ),
    output: Path = typer.Argument(..., help="Output file"),
) -> None:
    """Strip frontmatter and save the body."""
    from pimd.frontmatter import strip_frontmatter

    text = input.read_text(encoding="utf-8")
    body = strip_frontmatter(text)
    Path(output).write_text(body, encoding="utf-8")
    console.print(f"[green]Y[/] Written to {output}")


# ======================================================================
# pimd analyze
# ======================================================================


@app.command()
def analyze(
    input: Path = typer.Argument(
        ...,
        help="Directory to analyze",
        exists=True,
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output report path (JSON)",
    ),
) -> None:
    """Analyze a documentation project for issues."""
    show_sub_banner("analyze")
    from pimd.analyzer import ProjectAnalyzer

    analyzer = ProjectAnalyzer()
    report = analyzer.analyze_project(input)

    from rich.table import Table

    table = Table(title=f"Analysis Report: {input.name}")
    table.add_column("Severity", style="bold")
    table.add_column("Category")
    table.add_column("File")
    table.add_column("Message")

    for issue in report.issues[:50]:
        severity_map = {
            "error": "[red]ERROR[/]",
            "warning": "[yellow]WARN[/]",
            "info": "[cyan]INFO[/]",
        }
        sev = severity_map.get(issue.severity.value if hasattr(issue.severity, 'value') else issue.severity, "INFO")
        table.add_row(sev, issue.category, issue.file or "", issue.message[:80])
    console.print(table)
    console.print(f"\nTotal: {report.summary().get('total', len(report.issues))} issues")

    if output:
        import json

        Path(output).write_text(json.dumps({
            "issues": [i.__dict__ if hasattr(i, '__dict__') else {} for i in report.issues],
            "summary": report.summary(),
        }, indent=2, default=str), encoding="utf-8")
        console.print(f"[green]Y[/] Report written to {output}")


# ======================================================================
# pimd repo
# ======================================================================


@app.command()
def repo(
    input: Path = typer.Argument(
        ...,
        help="Documentation repository directory",
        exists=True,
    ),
    output: Path = typer.Argument(..., help="Output directory or file"),
    mode: str = typer.Option(
        "auto",
        "--mode",
        "-m",
        help="Output mode: single, multi, auto",
    ),
    workers: int = typer.Option(
        4,
        "--workers",
        "-w",
        help="Parallel workers",
    ),
) -> None:
    """Convert an entire documentation repository."""
    show_sub_banner("repo")
    from pimd.repository import RepositoryConfig, convert_repository

    config = RepositoryConfig(
        output_mode=mode,
        parallel_workers=workers,
        incremental=True,
    )
    result = convert_repository(input, output, config=config)
    console.print("[green]Y[/] Repository converted")
    console.print(
        f"  Total: {result.total_files}, "
        f"Converted: {result.converted}, "
        f"Skipped: {result.skipped}, "
        f"Failed: {result.failed}"
    )
    if result.errors:
        for path, err in result.errors[:10]:
            console.print(f"  [red]X[/] {path}: {err}")


# ======================================================================
# pimd assets
# ======================================================================


assets_cmd = typer.Typer(help="Manage document assets and attachments")
app.add_typer(assets_cmd, name="assets")


@assets_cmd.command(name="list")
def assets_list(
    input: Path = typer.Argument(
        ...,
        help="Input file or directory",
        exists=True,
    ),
) -> None:
    """List assets referenced by a document."""
    show_sub_banner("assets list")
    from pimd.attachments import find_attachments_in_text

    if input.is_file():
        text = input.read_text(encoding="utf-8", errors="replace")
        attachments = find_attachments_in_text(text, input.parent)
    else:
        from pimd.attachments import collect_assets

        attachments = collect_assets(input)

    from rich.table import Table

    table = Table(title=f"Assets ({len(attachments)} found)")
    table.add_column("Type")
    table.add_column("Path")
    table.add_column("Size")
    table.add_column("Status")

    for att in attachments[:30]:
        status = "[green]found[/]" if att.resolved_path else "[red]missing[/]"
        size = f"{att.size / 1024:.1f}KB" if att.size > 0 else "?"
        table.add_row(
            att.attachment_type.value if hasattr(att.attachment_type, 'value') else str(att.attachment_type),
            att.relative_path,
            size,
            status,
        )
    console.print(table)
    if len(attachments) > 30:
        console.print(f"... and {len(attachments) - 30} more")


# ======================================================================
# pimd watch
# ======================================================================


@app.command()
def watch(
    input_dir: Path = typer.Argument(
        ...,
        help="Directory to watch for changes",
        exists=True,
        file_okay=False,
    ),
    output_dir: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: <input>-output)",
    ),
    format: str = typer.Option(
        "docx",
        "--format",
        "-f",
        help="Output format (docx, pdf, html, md, txt)",
    ),
    poll: float = typer.Option(
        1.0,
        "--poll",
        help="Poll interval in seconds (only used without watchdog)",
    ),
    watchdog: bool = typer.Option(
        False,
        "--watchdog",
        help="Use watchdog library for efficient file monitoring",
    ),
) -> None:
    """Watch a directory and automatically rebuild changed files."""
    show_sub_banner("watch")
    from pimd.export.watch import WatchMode

    watcher = WatchMode(
        poll_interval=poll,
        output_format=format,
        output_dir=str(output_dir) if output_dir else None,
    )
    try:
        if watchdog:
            watcher.use_watchdog(input_dir)
        else:
            watcher.run(input_dir, output_dir)
    except KeyboardInterrupt:
        watcher.stop()


# ======================================================================
# pimd build
# ======================================================================


@app.command()
def build(
    config: Path = typer.Argument(
        ...,
        help="Path to project config file (YAML/JSON/TOML)",
        exists=True,
        dir_okay=False,
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path (auto-derived if omitted)",
    ),
    format: str = typer.Option(
        "docx",
        "--format",
        "-f",
        help="Output format",
    ),
    workers: int = typer.Option(
        4,
        "--workers",
        "-w",
        help="Parallel workers for batch builds",
    ),
) -> None:
    """Build a multi-file project from a YAML/JSON/TOML config file."""
    show_sub_banner("build")
    import json

    raw = config.read_text(encoding="utf-8")
    suffix = config.suffix.lower()

    if suffix in (".yaml", ".yml"):
        import yaml
        data = yaml.safe_load(raw)
    elif suffix == ".json":
        data = json.loads(raw)
    elif suffix in (".toml", ".tml"):
        import tomllib
        data = tomllib.loads(raw)
    else:
        display_error("Unsupported config", f"Format '{suffix}' not supported")
        raise typer.Exit(code=1)

    chapters: list[str] = data.get("chapters", []) or data.get("files", [])
    if not chapters:
        display_error("No files", "Config must define 'chapters' or 'files' list")
        raise typer.Exit(code=1)

    out = Path(output) if output else Path(f"{config.stem}.{format}")
    if format == "docx":
        from pimd.merge import DocumentMerger

        merger = DocumentMerger()
        try:
            merger.merge(
                [Path(c) for c in chapters],
                out,
                generate_toc=data.get("toc", True),
                cover_page=data.get("cover", False),
            )
            console.print(f"[green]Y[/] Project built: {out}")
        except Exception as exc:
            display_error("Build failed", str(exc))
            raise typer.Exit(code=1) from exc
    else:
        from pimd.project import ProjectConverter

        pc = ProjectConverter(incremental=True)
        import shutil
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp(prefix="pimd_build_"))
        try:
            pc.convert_project(
                config.parent,
                out.parent,
                merge=True,
                output_format=format,
            )
            console.print(f"[green]Y[/] Project built: {out}")
        except Exception as exc:
            display_error("Build failed", str(exc))
            raise typer.Exit(code=1) from exc
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ======================================================================
# pimd accessibility
# ======================================================================


accessibility_cmd = typer.Typer(
    name="accessibility",
    help="Document accessibility validation and reporting",
    no_args_is_help=True,
)
app.add_typer(accessibility_cmd, name="accessibility")


@accessibility_cmd.command(name="check")
def accessibility_check(
    input: Path = typer.Argument(
        ...,
        help="Input file (.md) to check",
        exists=True,
        dir_okay=False,
    ),
    report: Path = typer.Option(
        None,
        "--report",
        "-r",
        help="Write accessibility report to file",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
) -> None:
    """Check a document for accessibility issues."""
    show_sub_banner("accessibility check")
    from pimd.accessibility import AccessibilityEngine

    engine = AccessibilityEngine()
    result = engine.validate_file(input)

    from rich.table import Table

    if result.issues:
        table = Table(title=f"Accessibility Report: {input.name}")
        table.add_column("Severity", style="bold")
        table.add_column("Type")
        table.add_column("WCAG")
        table.add_column("Message")
        for issue in result.issues:
            severity_map = {
                "error": "[red]ERROR[/]",
                "warning": "[yellow]WARN[/]",
                "info": "[cyan]INFO[/]",
            }
            sev = severity_map.get(issue.severity.value, "INFO")
            wcag = issue.wcag_criterion or ""
            table.add_row(sev, issue.type, wcag, issue.message[:80])
        console.print(table)
    console.print(f"\n[bold]Score:[/] {result.score:.0f}/100")

    if report:
        report.write_text(result.to_markdown(), encoding="utf-8")
        console.print(f"[green]Y[/] Report written to {report}")

    if json_output:
        import json as _json
        data = {
            "valid": result.valid,
            "score": result.score,
            "issues": [
                {
                    "type": i.type,
                    "severity": i.severity.value,
                    "wcag": i.wcag_criterion,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in result.issues
            ],
        }
        console.print(_json.dumps(data, indent=2))


@accessibility_cmd.command(name="report")
def accessibility_report(
    input: Path = typer.Argument(
        ...,
        help="Input file (.md) to analyze",
        exists=True,
        dir_okay=False,
    ),
    output: Path = typer.Argument(
        ...,
        help="Output markdown report path",
    ),
) -> None:
    """Generate a detailed accessibility report in Markdown."""
    show_sub_banner("accessibility report")
    from pimd.accessibility import AccessibilityEngine

    engine = AccessibilityEngine()
    result = engine.validate_file(input)
    output.write_text(result.to_markdown(), encoding="utf-8")
    console.print(f"[green]Y[/] Accessibility report: {output}")
    console.print(f"  Score: {result.score:.0f}/100 — {'PASS' if result.valid else 'FAIL'}")


# ======================================================================
# pimd plugin
# ======================================================================

plugin_app = typer.Typer(
    name="plugin",
    help="Plugin management (install, enable, disable, list, doctor)",
    no_args_is_help=True,
)
app.add_typer(plugin_app, name="plugin")


@plugin_app.command(name="install")
def plugin_install(
    name: str = typer.Argument(..., help="Plugin name or path"),
) -> None:
    """Install a plugin by name (entry point) or filesystem path."""
    show_sub_banner("plugin install")
    from pimd.plugins import PluginManager

    mgr = PluginManager()
    try:
        mgr.install_plugin(name)
        console.print(f"[green]Y[/] Plugin '{name}' installed")
    except Exception as exc:
        display_error("Install failed", str(exc))


@plugin_app.command(name="enable")
def plugin_enable(
    name: str = typer.Argument(..., help="Plugin name to enable"),
) -> None:
    """Enable a plugin."""
    show_sub_banner("plugin enable")
    from pimd.plugins import PluginManager

    mgr = PluginManager()
    mgr.enable(name)
    console.print(f"[green]Y[/] Plugin '{name}' enabled")


@plugin_app.command(name="disable")
def plugin_disable(
    name: str = typer.Argument(..., help="Plugin name to disable"),
) -> None:
    """Disable a plugin."""
    show_sub_banner("plugin disable")
    from pimd.plugins import PluginManager

    mgr = PluginManager()
    mgr.disable(name)
    console.print(f"[yellow]X[/] Plugin '{name}' disabled")


@plugin_app.command(name="list")
def plugin_list() -> None:
    """List installed plugins."""
    show_sub_banner("plugin list")
    from pimd.plugins import PluginManager

    mgr = PluginManager()
    plugins = mgr.list_plugins()
    if not plugins:
        console.print("[yellow]No plugins installed[/]")
        return
    table = Table(title=f"Plugins ({len(plugins)})")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Version", style="green")
    table.add_column("Type")
    table.add_column("Enabled")
    table.add_column("Description")
    for p in plugins:
        table.add_row(
            p.get("name", "?"),
            p.get("version", "?"),
            p.get("plugin_type", ""),
            "[green]Yes[/]" if p.get("enabled") == "True" else "[red]No[/]",
            p.get("description", ""),
        )
    console.print(table)


@plugin_app.command(name="doctor")
def plugin_doctor() -> None:
    """Run diagnostics on the plugin system."""
    show_sub_banner("plugin doctor")
    from pimd.plugins import PluginManager

    mgr = PluginManager()
    results = mgr.doctor()
    for r in results:
        if r.get("status") == "ok":
            console.print(f"  [green]Y[/] {r.get('check', '?')}")
        elif r.get("status") == "warn":
            console.print(f"  [yellow]![/] {r.get('check', '?')}: {r.get('message', '')}")
        else:
            console.print(f"  [red]X[/] {r.get('check', '?')}: {r.get('message', '')}")


# ======================================================================
# Shell completion
# ======================================================================


@app.command(hidden=True)
def completion(shell: str = typer.Argument(..., help="Shell type (bash|zsh|powershell)")) -> None:
    """Generate shell completion script."""
    from typer._completion import shells

    shell_map = {
        "bash": shells.Bash,
        "zsh": shells.Zsh,
        "powershell": shells.PowerShell,
        "fish": shells.Fish,
    }
    target = shell_map.get(shell.lower())
    if target is None:
        display_error("Unknown shell", f"Supported shells: {', '.join(shell_map)}")
        raise typer.Exit(code=1)

    from typer._completion import _install_completion

    try:
        _install_completion(app, target)
    except Exception as exc:
        display_error("Completion Error", str(exc))
        raise typer.Exit(code=1) from exc


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------


def import_path(mod_name: str) -> object:
    """Lazy import helper."""
    import importlib

    return importlib.import_module(mod_name)


# ======================================================================
# pimd epub
# ======================================================================


@app.command()
def epub(
    input: Path = typer.Argument(
        ...,
        help="Path to input .md file",
        exists=True,
        dir_okay=False,
    ),
    output: Path = typer.Argument(
        ...,
        help="Path to output .epub file",
    ),
    title: str | None = typer.Option(None, "--title", help="Book title"),
    author: str | None = typer.Option(None, "--author", help="Author name"),
    language: str = typer.Option("en", "--language", "-l", help="Language code"),
    css: str | None = typer.Option(None, "--css", help="Path to custom CSS file"),
    cover: str | None = typer.Option(None, "--cover", help="Cover image path"),
    validate: bool = typer.Option(
        False, "--validate", help="Validate EPUB after generation"
    ),
) -> None:
    """Convert a Markdown file to EPUB 3.2 e-book format."""
    show_sub_banner("epub")
    from pimd.export.formats.epub import EpubRenderer, validate_epub
    from pimd.parsers.markdown_parser import MarkdownParser

    steps = StepDisplay()
    steps.add("Reading file")
    steps.add("Parsing")
    steps.add("Rendering EPUB")
    steps.add("Writing EPUB")

    try:
        steps.start("Reading file")
        text = input.read_text(encoding="utf-8")
        steps.succeed("Reading file")

        steps.start("Parsing")
        doc = MarkdownParser().parse(text)
        steps.succeed("Parsing")

        steps.start("Rendering EPUB")
        renderer = EpubRenderer(css_path=css)
        renderer.render(
            doc,
            output,
            title=title or input.stem,
            author=author or "",
            language=language,
            cover_image=cover,
        )
        steps.succeed("Rendering EPUB")

        steps.start("Writing EPUB")
        steps.succeed("Writing EPUB")
        console.print(f"[green]Y[/] EPUB generated: {output}")

        if validate:
            issues = validate_epub(output)
            if issues:
                console.print("\n[red]X[/] EPUB validation issues:")
                for issue in issues:
                    console.print(f"  [red]-[/] {issue}")
            else:
                console.print("[green]Y[/] EPUB validation passed")

    except Exception as exc:
        steps.fail("Rendering EPUB")
        display_error("EPUB Error", str(exc))
        raise typer.Exit(code=1) from exc


# ======================================================================
# pimd latex
# ======================================================================


@app.command()
def latex(
    input: Path = typer.Argument(
        ...,
        help="Path to input .md file",
        exists=True,
        dir_okay=False,
    ),
    output: Path = typer.Argument(
        ...,
        help="Path to output .tex file",
    ),
    title: str | None = typer.Option(None, "--title", help="Document title"),
    author: str | None = typer.Option(None, "--author", help="Author name"),
    doc_class: str = typer.Option(
        "article",
        "--class",
        help="Document class (article, report, book)",
    ),
    toc: bool = typer.Option(False, "--toc", help="Generate table of contents"),
) -> None:
    """Convert a Markdown file to LaTeX format."""
    show_sub_banner("latex")
    from pimd.export.formats.latex import LatexRenderer
    from pimd.parsers.markdown_parser import MarkdownParser

    steps = StepDisplay()
    steps.add("Reading file")
    steps.add("Parsing")
    steps.add("Rendering LaTeX")
    steps.add("Writing LaTeX")

    try:
        steps.start("Reading file")
        text = input.read_text(encoding="utf-8")
        steps.succeed("Reading file")

        steps.start("Parsing")
        doc = MarkdownParser().parse(text)
        steps.succeed("Parsing")

        steps.start("Rendering LaTeX")
        renderer = LatexRenderer()
        renderer.render(
            doc,
            output,
            title=title or input.stem,
            author=author or "",
            document_class=doc_class,
            generate_toc=toc,
        )
        steps.succeed("Rendering LaTeX")

        steps.start("Writing LaTeX")
        steps.succeed("Writing LaTeX")
        console.print(f"[green]Y[/] LaTeX generated: {output}")

    except Exception as exc:
        steps.fail("Rendering LaTeX")
        display_error("LaTeX Error", str(exc))
        raise typer.Exit(code=1) from exc


# ======================================================================
# pimd language (i18n)
# ======================================================================


@app.command()
def language(
    input: Path = typer.Argument(
        ...,
        help="Input file to detect language/script of",
        exists=True,
    ),
) -> None:
    """Detect script/language direction of a document."""
    show_sub_banner("language")
    from pimd.i18n import ScriptType, detect_script, is_rtl_language

    text = input.read_text(encoding="utf-8")
    script = detect_script(text)

    data = {
        "Script direction": script.value,
        "File": str(input),
        "Size": f"{len(text)} chars",
    }

    if script == ScriptType.RTL:
        data["Note"] = "Right-to-left — Arabic, Hebrew, Persian, Urdu"
        data["RTL language match"] = "Yes" if any(is_rtl_language(lang) for lang in ["ar", "he", "fa", "ur"]) else "No"
    elif script == ScriptType.CJK:
        data["Note"] = "CJK — Chinese, Japanese, Korean"
    else:
        data["Note"] = "Left-to-right — Latin-based"

    info_table(data)


# ======================================================================
# pimd revision (collaborative editing)
# ======================================================================

revision_cmd = typer.Typer(
    name="revision",
    help="Track and manage document revisions (collaborative editing)",
    no_args_is_help=True,
)
app.add_typer(revision_cmd, name="revision")


@revision_cmd.command(name="init")
def revision_init(
    document_id: str = typer.Option("", "--id", help="Document ID"),
    title: str = typer.Option("", "--title", "-t", help="Document title"),
) -> None:
    """Initialize a new revision tracker for a document."""
    show_sub_banner("revision init")
    from pimd.revisions import RevisionTracker

    tracker = RevisionTracker(document_id=document_id, title=title)
    summary = tracker.export_review_summary()
    console.print("[green]Y[/] Revision tracker initialized")
    console.print(f"  Document ID: {summary['document_id']}")
    console.print(f"  Title: {summary['title'] or '(untitled)'}")
    console.print(f"  Created: {summary['created_at']}")


@revision_cmd.command(name="add")
def revision_add(
    type: str = typer.Argument(
        ..., help="Revision type (insertion, deletion, replacement, formatting)"
    ),
    author: str = typer.Option("", "--author", "-a", help="Author name"),
    description: str = typer.Option("", "--desc", "-d", help="Description"),
) -> None:
    """Add a tracked revision (demo / placeholder)."""
    show_sub_banner("revision add")
    from pimd.revisions import RevisionTracker, RevisionType

    rev_type = RevisionType(type.lower())
    tracker = RevisionTracker()
    rev = tracker.add_revision(
        revision_type=rev_type,
        author=author or "anonymous",
        start_pos=0,
        end_pos=0,
        description=description,
    )
    console.print(f"[green]Y[/] Revision added: {rev.revision_id}")
    console.print(f"  Type: {rev.revision_type.value}")
    console.print(f"  Author: {rev.author}")
    console.print(f"  Status: {rev.status.value}")


@revision_cmd.command(name="list")
def revision_list(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
) -> None:
    """List tracked revisions."""
    show_sub_banner("revision list")
    from pimd.revisions import RevisionStatus, RevisionTracker

    tracker = RevisionTracker()
    rev_status = RevisionStatus(status.lower()) if status else None
    revisions = tracker.get_revisions(status=rev_status)

    if not revisions:
        console.print("[yellow]No revisions found[/]")
        return

    table = Table(title=f"Revisions ({len(revisions)})")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Author")
    table.add_column("Status")
    table.add_column("Description")

    for rev in revisions[:20]:
        table.add_row(
            rev.revision_id[:12],
            rev.revision_type.value,
            rev.author,
            rev.status.value,
            rev.description[:50],
        )
    console.print(table)


# ======================================================================
# Update export sub-commands with new formats
# ======================================================================


@export_app.command(name="epub")
def export_epub(
    input: Path = typer.Argument(..., help="Input file (.md)", exists=True),
    output: Path = typer.Argument(..., help="Output .epub path"),
    title: str = typer.Option("", "--title", help="Book title"),
    author: str = typer.Option("", "--author", help="Author name"),
    language: str = typer.Option("en", "--language", "-l", help="Language code"),
) -> None:
    """Export to EPUB 3.2 e-book format."""
    from pimd.export import ExportConverter

    result = ExportConverter().convert(
        input, "epub", output,
        metadata={"title": title or input.stem, "author": author},
        language=language,
    )
    if result.success:
        console.print(f"[green]Y[/] Exported to {result.output_path}")
    else:
        display_error("EPUB export failed", result.error or "")
        raise typer.Exit(code=1)


@export_app.command(name="latex")
def export_latex(
    input: Path = typer.Argument(..., help="Input file (.md)", exists=True),
    output: Path = typer.Argument(..., help="Output .tex path"),
    title: str = typer.Option("", "--title", help="Document title"),
    author: str = typer.Option("", "--author", help="Author name"),
    doc_class: str = typer.Option("article", "--class", help="Document class"),
) -> None:
    """Export to LaTeX format."""
    from pimd.export import ExportConverter

    result = ExportConverter().convert(
        input, "latex", output,
        metadata={"title": title or input.stem, "author": author},
        latex_document_class=doc_class,
    )
    if result.success:
        console.print(f"[green]Y[/] Exported to {result.output_path}")
    else:
        display_error("LaTeX export failed", result.error or "")
        raise typer.Exit(code=1)


@export_app.command(name="pdfa")
def export_pdfa(
    input: Path = typer.Argument(..., help="Input file (.md)", exists=True),
    output: Path = typer.Argument(..., help="Output .pdf path"),
    level: str = typer.Option("2b", "--level", help="PDF/A level (1b, 2b)"),
) -> None:
    """Export to PDF/A archival format."""
    from pimd.export import ExportConverter

    result = ExportConverter().convert(input, "pdfa", output, pdfa_level=level)
    if result.success:
        console.print(f"[green]Y[/] PDF/A exported to {result.output_path}")
    else:
        display_error("PDF/A export failed", result.error or "")
        raise typer.Exit(code=1)


def main() -> None:
    """CLI entry point used by ``pyproject.toml``."""
    app()
