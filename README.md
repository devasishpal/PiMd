<p align="center">
  <img src="examples/rounded-corners.png" alt="PiMD" width="200">
</p>

<h1 align="center">PiMD</h1>

<p align="center">
  <em>Publish documents from Markdown. Professional output. Zero config.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/pimd/"><img src="https://img.shields.io/pypi/v/pimd" alt="PyPI"></a>
  <a href="https://pypi.org/project/pimd/"><img src="https://img.shields.io/pypi/pyversions/pimd" alt="Python Versions"></a>
  <a href="https://pypi.org/project/pimd/"><img src="https://img.shields.io/pypi/dm/pimd" alt="Downloads"></a>
  <a href="https://github.com/devasishpal/PiMd/actions"><img src="https://img.shields.io/github/actions/workflow/status/devasishpal/PiMd/ci.yml?branch=main" alt="Build"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"></a>
</p>

---

**PiMD** (Python Markdown Publisher) converts Markdown and HTML into professional DOCX, EPUB, PDF/A, and LaTeX documents — books, reports, technical manuals, research papers, and more. It runs entirely offline with zero cloud dependencies.

---

## Comparison with Alternatives

PiMD fills a unique niche — it is the only Markdown-to-DOCX engine with built-in diagram rendering, equation-to-OMML conversion, and Python-native plugin system. Here's how it stacks up:

| Feature | PiMD | Pandoc | MkDocs | Sphinx | Quarto | Typst |
|---------|------|--------|--------|--------|--------|-------|
| **DOCX output** | ✅ Professional typography, TOC, cross-refs, page numbers, watermarks | ✅ Basic (pandoc-crossref for references) | ❌ | ❌ | ❌ | ⚠️ Experimental |
| **DOCX templates** | ✅ 10 presets + inheritance + custom + reference-docx | ✅ Custom reference-docx | ❌ | ❌ | ❌ | ❌ |
| **EPUB 3.2** | ✅ Full support, TOC, MathML, SVG | ✅ EPUB 2/3 | ❌ | ❌ | ✅ | ❌ |
| **PDF/A archival** | ✅ Native (fpdf2) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **LaTeX output** | ✅ Clean, compilable .tex | ✅ Native LaTeX | ❌ | ✅ Native | ✅ | ❌ |
| **HTML output** | ✅ Responsive, standalone or site | ✅ | ✅ Static site | ✅ Static site | ✅ Static site | ❌ |
| **Diagrams** (Mermaid/PlantUML/Graphviz/D2/BlockDiag/Vega) | ✅ **Built-in** via PiDraw | ❌ Manual pre-render | ⚠️ Plugin-only | ⚠️ Extension-only | ❌ Manual | ❌ |
| **Equations** (LaTeX → OMML/SVG/HTML) | ✅ **Native Word OMML** for DOCX, MathJax for HTML | ✅ MathML, TeX | ❌ | ✅ MathJax/Sphinx | ✅ MathJax/Katex | ✅ Native |
| **Zero config** | ✅ `pip install pimd` → `pimd md file.md file.docx` | ✅ `pandoc file.md -o file.docx` | ❌ Requires mkdocs.yml | ❌ conf.py required | ❌ _quarto.yml required | ❌ Typst file required |
| **Python API** | ✅ First-class importable library | ⚠️ Via subprocess/haskell-bindings | ⚠️ Via plugins | ✅ sphinx-build programmatic | ❌ CLI only | ❌ CLI only |
| **Plugin system** | ✅ 9 typed hook types + SDK + event bus | ⚠️ Lua filters (typed? no) | ⚠️ Theme/plugin | ✅ Extension API | ❌ | ❌ |
| **WCAG validation** | ✅ **Built-in accessibility engine** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **i18n / RTL** | ✅ Arabic/Persian/Urdu reshaping, CJK, 15+ locales | ✅ via `--pdf-engine` options | ⚠️ Theme-dependent | ⚠️ Babel/Intl | ✅ locale support | ✅ Native |
| **BibTeX citations** | ✅ Built-in | ✅ citeproc | ❌ | ✅ built-in | ✅ | ❌ |
| **Incremental build** | ✅ Skip unchanged files | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Caching** (memory/fs/Redis) | ✅ **Three backends** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **CLI watch mode** | ✅ File watching | ❌ | ✅ auto-reload | ✅ auto-reload | ✅ auto-reload | ❌ |
| **Batch processing** | ✅ Directory batch + output mapping | ⚠️ Shell scripts | ✅ | ✅ | ✅ | ❌ |
| **Safety guards** | ✅ Loop detection, path traversal protection, timeout enforcement | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Offline** | ✅ **100% offline**, zero cloud | ✅ | ⚠️ Search requires online | ✅ | ⚠️ Some features online | ✅ |
| **Language** | Python 3.10+ | Haskell | Python | Python | Python/R | Rust |

**When to use PiMD:**
- You need **professional DOCX** with diagrams, equations, and templates from Markdown
- You want a **Python API** to integrate with FastAPI/Django/Flask
- You need **WCAG-compliant accessible documents**
- You're building **scientific papers, technical manuals, or books** with diagrams and equations
- You want **zero-config** conversion without YAML config files

**When to use alternatives:**
- **Pandoc**: If you need the broadest format support and are comfortable with Haskell filters
- **MkDocs / Sphinx**: If you're building documentation websites (static HTML is the primary output)
- **Quarto**: If you're in the R/Python statistical computing ecosystem and want HTML-first publishing
- **Typst**: If you want a fresh typesetting language and don't need DOCX/EPUB output

---

## Key Features

- **Publish-ready DOCX** — professional typography, templates, watermarks, TOC, cross-references
- **Diagrams** — Mermaid, PlantUML, Graphviz, D2, BlockDiag, Vega, ASCII — powered by [PiDraw](https://pypi.org/project/pidraw/)
- **Equations** — LaTeX into native Word OMML, MathJax, or SVG
- **Templates** — 10 presets (academic, business, book, resume, invoice…) with inheritance, plus Pandoc-style reference DOCX support
- **Multi-format** — DOCX, EPUB 3.2, LaTeX, PDF/A, HTML, Markdown, TXT
- **Python API** — first-class library for FastAPI, Flask, Django
- **Plugin system** — 9 typed plugin types with SDK, hooks, and event bus
- **Accessibility** — built-in WCAG validation engine
- **i18n** — full Unicode, RTL (Arabic/Persian/Urdu), CJK, 15+ language configs
- **Enterprise** — incremental builds, parallel processing, caching (memory/fs/Redis), safety guards

## Installation

```bash
pip install pimd                       # Core only
pip install "pimd[all]"                # Core + all optional features
```

Optional extras:

| Extra | What it adds |
|-------|-------------|
| `[diagrams]` | Pillow — required for diagram rendering |
| `[equations]` | matplotlib — renders LaTeX equations |
| `[export]` | PDF export (docx2pdf / weasyprint) |
| `[citations]` | BibTeX citation support |
| `[redis]` | Redis cache backend |
| `[pdfa]` | PDF/A archival format (fpdf2) |
| `[i18n]` | Arabic reshaping + bidirectional text |
| `[all]` | Everything above |

## Quick Start

### Python API

```python
from pimd import PiMD

engine = PiMD()

# File to file
engine.md_to_docx("report.md", "report.docx")

# String to bytes (no disk writes)
docx_bytes = engine.md_text_to_docx_bytes("# Hello World")

# With options
engine.md_to_docx(
    "thesis.md", "thesis.docx",
    generate_toc=True,
    page_numbers=True,
    render_diagrams=True,
)

# With a reference DOCX for custom styles/headers/footers
engine.md_to_docx(
    "report.md", "report.docx",
    reference_doc="company-template.docx",
)
```

### CLI

```bash
# Convert Markdown to DOCX
pimd md guide.md guide.docx --diagrams

# Convert to EPUB / LaTeX
pimd epub book.md book.epub
pimd latex paper.md paper.tex

# Use a template
pimd md report.md report.docx --template academic

# Use a reference DOCX for custom styles/headers/footers
pimd md report.md report.docx --reference-doc company-template.docx

# Inspect styles in a reference DOCX
pimd template inspect company-template.docx

# Batch convert a directory
pimd batch ./docs --output ./build
```

## Common Examples

```python
# Convert HTML to DOCX
engine.html_to_docx("page.html", "page.docx")

# EPUB generation
engine.convert("novel.md", "epub", "novel.epub")

# PDF/A for archival
engine.convert("contract.md", "pdfa", "contract.pdf")

# Watch directory for changes (CLI)
# pimd watch ./docs --output ./build
```

## Supported Formats

| Input | Output |
|-------|--------|
| Markdown (.md) | DOCX (.docx) |
| HTML (.html) | EPUB 3.2 (.epub) |
| — | LaTeX (.tex) |
| — | PDF / PDF/A (.pdf) |
| — | HTML (.html) |
| — | Markdown (.md) |
| — | TXT (.txt) |

## PiDraw Integration

All diagram rendering is delegated to [PiDraw](https://pypi.org/project/pidraw/). PiMD auto-detects diagram type from code block language hints and renders Mermaid, PlantUML, Graphviz, D2, BlockDiag, Vega, ASCII, and more — all as high-resolution transparent PNGs embedded in DOCX or inline SVG for HTML.

```bash
# List supported diagram engines
pimd diagrams list

# Test a specific engine
pimd diagrams test mermaid
```

## Documentation

| Guide | Location |
|-------|----------|
| Full CLI reference | `pimd --help` |
| Diagram guide | `docs/diagram-guide.md` |
| Equation guide | `docs/equation-guide.md` |
| Performance guide | `docs/performance-guide.md` |
| Scientific publishing | `docs/scientific-publishing-guide.md` |
| Plugin development | `CONTRIBUTING.md` |
| Migration from v1.x | `docs/migration-guide.md` |
| Support & FAQ | `SUPPORT.md` |

## Contributing

We welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, plugin SDK docs, and pull request guidelines.

```bash
git clone https://github.com/devasishpal/PiMd.git
cd PiMd
pip install -e ".[dev,all]"
```

## License

MIT — see [LICENSE](LICENSE) for details.
