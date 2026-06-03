# PiMD — Professional Markdown & HTML to DOCX Framework

> **PiMD** transforms Markdown and HTML into beautifully formatted DOCX documents — with native diagrams, editable equations, themes, templates, branding, and enterprise-scale pipelines.

```ascii
  Markdown ──┐
              ├──► PiMD ──► Professional .docx
  HTML ───────┘              ├── Diagrams (Mermaid, PlantUML, Graphviz, BlockDiag, Vega…)
                             ├── Equations (LaTeX → editable OMML)
                             ├── Themes & Templates
                             ├── Brand identity
                             ├── PDF export
                             └── 100+ CLI options
```

---

## Features

### Core Conversion
- **Markdown → DOCX** — Full CommonMark + GitHub-Flavored Markdown
- **HTML → DOCX** — via BeautifulSoup with structure preservation
- **In-memory mode** — convert to bytes, no filesystem writes (ideal for web frameworks)
- **Async API** — all methods available as `async_` variants
- **Streaming** — handle multi-gigabyte files with chunked processing

### Diagrams
Render diagrams directly from code blocks — no screenshots, no manual exports:

```ascii
  ┌─────────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────┐
  │ Mermaid     │    │ PlantUML     │    │ Graphviz │    │ BlockDiag │
  │ graph/seq/  │    │ sequence/    │    │ DOT lang │    │ family   │
  │ gantt/etc.  │    │ use case/    │    │          │    │ (5 tools)│
  └──────┬──────┘    └──────┬───────┘    └────┬─────┘    └────┬─────┘
         │                  │                  │              │
         └──────────────────┼──────────────────┼──────────────┘
                            ▼
              ┌─────────────────────────────────┐
              │  DiagramEngine                  │
              │  • Auto-detection (no tags)     │
              │  • SHA256 content-hash caching  │
              │  • Parallel rendering           │
              │  • SVG preferred / PNG fallback │
              └────────────┬────────────────────┘
                           ▼
              ┌─────────────────────────────────┐
              │   DOCX embedding                │
              │   • Center-aligned              │
              │   • Figure numbering            │
              │   • Captions                    │
              │   • Error placeholders          │
              └─────────────────────────────────┘
```

Supported diagram languages:

| Language | Code Block Tag | Renderer | External Tool | Pure Python |
|----------|---------------|----------|---------------|-------------|
| Mermaid | ```` ```mermaid ```` | MermaidRenderer | `mmdc` | ❌ |
| PlantUML | ```` ```plantuml ```` | PlantUMLRenderer | `plantuml` | ❌ |
| Graphviz / DOT | ```` ```dot ```` | GraphvizRenderer | `dot` | ❌ |
| D2 | ```` ```d2 ```` | D2Renderer | `d2` | ❌ |
| ASCII art | ```` ```ascii ```` | AsciiRenderer | None | ✅ (Pillow) |
| SVG | ```` ```svg ```` | SvgRenderer | cairosvg / rsvg-convert / inkscape | ✅ (partial) |
| BlockDiag | ```` ```blockdiag ```` | BlockDiagRenderer | `blockdiag` | ❌ |
| SeqDiag | ```` ```seqdiag ```` | SeqDiagRenderer | `seqdiag` | ❌ |
| ActDiag | ```` ```actdiag ```` | ActDiagRenderer | `actdiag` | ❌ |
| NwDiag | ```` ```nwdiag ```` | NwDiagRenderer | `nwdiag` | ❌ |
| PacketDiag | ```` ```packetdiag ```` | PacketDiagRenderer | `packetdiag` | ❌ |
| BPMN | ```` ```bpmn ```` | BPMNRenderer | `bpmn-to-svg` (Node.js) | ❌ |
| Vega | ```` ```vega ```` | VegaRenderer | `vg2svg` (Node.js) | ❌ |
| Vega-Lite | ```` ```vega-lite ```` | VegaLiteRenderer | `vl2svg` (Node.js) | ❌ |

**Auto-detection**: Diagram language is detected automatically from content. No language tag required for supported formats:

```
graph TD                    → automatically detected as Mermaid
A --> B

@startuml                   → automatically detected as PlantUML
Alice -> Bob: Hello
@enduml

digraph G {                 → automatically detected as Graphviz
  A -> B
}

a -> b                      → automatically detected as D2

+-------+                   → automatically detected as ASCII
| Hello |
+-------+
```

**Rendering is automatic** during `pimd md input.md output.docx` — no separate command needed.

**DOCX output features per diagram**:
- Center-aligned embedding
- Auto-incrementing figure numbering (Figure 1, Figure 2, ...)
- Caption support
- Proper scaling with DPI awareness
- SVG preferred, PNG fallback for Word compatibility
- Error placeholder on render failure

### Equations
Write LaTeX math — it becomes **native Word equations** (editable OMML, not images):

```
  $$E = mc^2$$  ──►  Native Word equation (editable!)
  $H_2O$        ──►  Chemical formula detection
  \begin{align} ──►  Multi-line aligned equations with numbering
```

- **Inline**: `$...$`, `\(...\)`
- **Display**: `$$...$$`, `\[...\]`, `\begin{equation}`, `\begin{align}`
- **OMML output** — editable in Microsoft Word equation editor
- **SVG fallback** — if OMML conversion fails
- **Chemical formulas** — auto-detection of `H_2O`, `CO_2`, `CH_4`, `NH_3`
- **Equation numbering** — automatic `(1)`, `(2)` for display math
- **Caching** — in-memory and Redis-backed

### Themes
```
  ┌──────────────┐
  │  Theme (ABC) │  ◄── Extend this for custom themes
  ├──────────────┤
  │  configure_  │
  │  styles(doc) │
  └──────────────┘
         ▲
  ┌──────┴──────┐
  │ Professional│
  │ Theme       │
  ├─────────────┤
  │ • Calibri   │
  │ • #1A1A2E   │
  │   headings  │
  │ • Shaded    │
  │   code      │
  │ • Blockquote│
  │   styling   │
  └─────────────┘
```

### Templates
JSON-based preset templates control every document aspect:

| Template | Use Case |
|----------|----------|
| `professional` | Business reports, proposals |
| `academic` | Papers, theses, dissertations |
| `book` | Chapters, parts, full books |
| `business` | Letters, memos, invoices |
| `technical` | API docs, manuals, specs |

Each template defines: page size, margins, fonts, heading styles, line spacing, TOC, cover page, headers/footers, watermarks.

### Branding
Load brand identity from JSON/TOML and apply across all documents:
- Primary/secondary colors
- Font family
- Logo reference
- Metadata (author, company, subject, version)

### Caching
```
  ┌──────────────┐    ┌──────────────────┐
  │ CacheBackend │◄───│   MemoryCache    │
  │   (ABC)      │    │  (dict + TTL)   │
  └──────┬───────┘    └──────────────────┘
         │
         ├────────────────┐
         ▼                ▼
  ┌──────────────┐  ┌──────────────────┐
  │  RedisCache  │  │ Specialized      │
  │  Backend     │  │ caches for       │
  │  (pooling,   │  │ diagrams &       │
  │   health)    │  │ equations        │
  └──────────────┘  └──────────────────┘
```

Diagram caching uses SHA256 content hashing:

```
cache_key = SHA256(language + source)
```

If the diagram source has not changed, the cached SVG/PNG is reused and re-rendering is skipped entirely.

### Safety & Enterprise
- Configurable limits: file size, text size, nesting depth, block count, image dimensions
- Path traversal protection
- URL scheme whitelisting
- Null byte detection
- Strict and permissive presets

### Ecosystem Support
- **Obsidian** vault export
- **MkDocs** project conversion
- **Docusaurus** project conversion
- **Sphinx** / RST conversion
- **GitHub Flavored Markdown** (task lists, emoji, mentions)
- Flavor auto-detection

---

## Installation

```bash
# Minimal install (Markdown/HTML → DOCX only)
pip install pimd

# With all extras (recommended)
pip install "pimd[all] @ git+https://github.com/devasishpal/PiMd.git"

# Or from local clone
git clone https://github.com/devasishpal/PiMd.git
cd PiMd
pip install -e ".[all]"
```

### Extra Dependencies

| Extra | Packages | Purpose |
|-------|----------|---------|
| `diagrams` | Pillow | ASCII diagram rendering |
| `equations` | matplotlib | LaTeX → SVG fallback |
| `export` | docx2pdf / weasyprint | PDF export |
| `citations` | bibtexparser | BibTeX citation support |
| `redis` | redis | Redis caching backend |
| `profiling` | psutil | Performance profiling |
| `dev` | pytest, ruff, typer-cli | Development tools |
| `all` | Everything above | Full install |

External CLI tools for diagram rendering (install separately when needed):

| Diagram Tool | Installation |
|-------------|-------------|
| Mermaid | `npm install -g @mermaid-js/mermaid-cli` |
| PlantUML | `java -jar plantuml.jar` or `apt install plantuml` |
| Graphviz | `apt install graphviz` or `choco install graphviz` |
| D2 | `curl -fsSL https://d2lang.com/install.sh \| sh -s --` |
| BlockDiag family | `pip install blockdiag seqdiag actdiag nwdiag packetdiag` (provides CLI) |
| BPMN | `npm install -g bpmn-to-svg` |
| Vega / Vega-Lite | `npm install -g vega-cli` (provides vg2svg, vl2svg) |

---

## Quick Start

### CLI

```bash
# Basic conversion — diagrams are automatically detected and rendered
pimd md input.md output.docx

# With table of contents, cover page, and page numbers
pimd md input.md output.docx \
  --toc \
  --cover \
  --page-numbers \
  --title "Annual Report" \
  --author "Jane Doe" \
  --company "ACME Corp" \
  --version "2.0" \
  --header "Confidential" \
  --footer "Page"

# HTML conversion
pimd html input.html output.docx

# Batch convert all .md files in a directory
pimd batch ./docs ./output --pattern "*.md" --workers 4

# Convert an entire documentation project
pimd project ./docs ./output

# Merge multiple documents
pimd merge chapter1.md chapter2.md chapter3.md output.docx --toc

# Export to PDF
pimd export pdf input.md output.pdf

# Generate a report
pimd report generate executive report.docx --title "Q4 Review"

# Compile a book from config
pimd book compile book.json book.docx

# Check system health
pimd doctor
pimd diagrams doctor
pimd equations doctor
pimd export doctor

# List diagram renderers
pimd diagrams list

# Test a diagram renderer
pimd diagrams test ascii
pimd diagrams test mermaid

# List templates
pimd template list

# View configuration
pimd config show
```

### Python Library

```python
from pimd import PiMD

engine = PiMD()

# File to file — diagrams are automatically detected and rendered
engine.md_to_docx("report.md", "report.docx",
                  title="Annual Report",
                  author="Jane Doe",
                  generate_toc=True,
                  cover_page=True,
                  page_numbers=True)

# Text to bytes (in-memory — no filesystem writes)
docx_bytes = engine.md_text_to_docx_bytes("# Hello\nWorld")

# HTML
engine.html_text_to_docx("<h1>Hello</h1>", "hello.docx")

# Async
result = await engine.async_md_to_docx("input.md", "output.docx")
```

### Web Frameworks

```python
# FastAPI
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response
from pimd import PiMD

app = FastAPI()
engine = PiMD()

@app.post("/convert")
async def convert(file: UploadFile = File(...)) -> Response:
    content = await file.read()
    docx_bytes = engine.md_text_to_docx_bytes(content.decode())
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{file.filename}.docx"'},
    )
```

---

## Architecture

### Conversion Pipeline

```
  ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌──────────┐
  │  Source  │    │  Parser  │    │ Transform │    │ Renderer │    │ Output   │
  │  Text    │───►│          │───►│           │───►│          │───►│ .docx    │
  │ (MD/HTML)│    │ md-it / │    │ Diagrams │    │ python-  │    │ (file or │
  │          │    │ BS4     │    │ Equations │    │ docx     │    │ bytes)   │
  └──────────┘    └──────────┘    └───────────┘    └──────────┘    └──────────┘
                                                
                       Plugin Hooks ▲            ▲  Safety Check
                                    │            │
                   before_parse ────┤            │
                   after_parse  ────┼────────────┘
                   before_render ───┘
                   after_render
```

### Diagram Pipeline

```
  Markdown
     │
     ▼
  Parse (markdown-it-py)
     │
     ▼
  Detect diagram blocks
     ├── Known language tag? → use tagged renderer
     ├── No tag → auto-detect from content (patterns + heuristics)
     └── Not a diagram → pass through
     │
     ▼
  DiagramRegistry.lookup(language)
     │
     ▼
  Cache check (SHA256(language + source))
     ├── Hit → return cached result
     └── Miss → render via external tool
     │
     ▼
  Render → SVG (preferred) + PNG (fallback)
     │
     ▼
  Cache result
     │
     ▼
  Insert into DOCX (center-aligned, with caption + figure number)
```

### Document Model

```
  Document
  ├── Heading (level 1-6)
  ├── Paragraph
  │   └── Span (bold, italic, code, link, math, underline)
  ├── CodeBlock (language-tagged)
  ├── Diagram (PNG bytes, SVG bytes, source, language, caption, error)
  ├── EquationBlock (LaTeX, OMML XML, SVG, number)
  ├── Blockquote (nested)
  ├── BulletList / OrderedList
  │   └── ListItem → children
  ├── Table (headers + rows)
  ├── Image (path, alt, dimensions)
  └── HorizontalRule
```

### Service Architecture

```
  ┌─────────────────────────────────────────────────────────┐
  │                     PiMD (API)                          │
  │  md_to_docx()  md_text_to_docx_bytes()  async_*()      │
  └────────────────────────┬────────────────────────────────┘
                           │
  ┌────────────────────────▼────────────────────────────────┐
  │               ConversionService                         │
  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
  │  │ Markdown │  │ Diagram  │  │       Plugin         │  │
  │  │ Parser   │  │ Engine   │  │       Manager        │  │
  │  └──────────┘  └──────────┘  └──────────────────────┘  │
  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
  │  │ Equation │  │  Safety  │  │   Cache (mem/Redis)  │  │
  │  │ Engine   │  │  Guard   │  │                      │  │
  │  └──────────┘  └──────────┘  └──────────────────────┘  │
  │  ┌──────────────────────────────────────────────────┐  │
  │  │              DocxRenderer                        │  │
  │  │  Cover pages  TOC fields  Headers  Footers       │  │
  │  │  All blocks   Hyperlinks  OMML  Images  Diagrams │  │
  │  └──────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────┘
```

---

## CLI Commands

### Conversion
| Command | Description |
|---------|-------------|
| `pimd md <INPUT> <OUTPUT>` | Convert Markdown file to DOCX (auto-renders diagrams) |
| `pimd html <INPUT> <OUTPUT>` | Convert HTML file to DOCX |
| `pimd merge <FILES>... <OUTPUT>` | Merge multiple documents |
| `pimd batch <DIR> <DIR>` | Batch convert directory |
| `pimd project <DIR> <DIR>` | Convert doc project tree |
| `pimd repo <DIR> <OUTPUT>` | Convert documentation repository |

### Diagrams
| Command | Description |
|---------|-------------|
| `pimd diagrams list` | List available renderers |
| `pimd diagrams test <LANG>` | Test a diagram renderer |
| `pimd diagrams doctor` | Diagnose renderer setup |
| `pimd diagrams cache-clear` | Clear diagram cache |

### Equations
| Command | Description |
|---------|-------------|
| `pimd equations list` | List supported formats |
| `pimd equations test <LATEX>` | Test equation rendering |
| `pimd equations doctor` | Diagnose equation setup |

### Templates & Branding
| Command | Description |
|---------|-------------|
| `pimd template list` | List templates |
| `pimd template info <NAME>` | Show template details |
| `pimd template validate <NAME>` | Validate template config |
| `pimd brand set <FILE>` | Load brand identity |
| `pimd brand show` | Display current brand |

### Export
| Command | Description |
|---------|-------------|
| `pimd export docx <INPUT> <OUTPUT>` | Export to DOCX |
| `pimd export pdf <INPUT> <OUTPUT>` | Export to PDF |
| `pimd export html <INPUT> <OUTPUT>` | Export to HTML |
| `pimd export txt <INPUT> <OUTPUT>` | Export to text |
| `pimd export doctor` | Diagnose export engines |

### Reports & Books
| Command | Description |
|---------|-------------|
| `pimd report generate <TYPE> <OUTPUT>` | Generate structured report |
| `pimd report list-types` | List report types |
| `pimd book compile <CONFIG> <OUTPUT>` | Compile a book |

### System
| Command | Description |
|---------|-------------|
| `pimd info` | Version, themes, formats |
| `pimd doctor` | System diagnostics |
| `pimd version` | Show version |
| `pimd config show` | Show resolved config |
| `pimd config path` | Show config file locations |
| `pimd cache clear` | Clear all caches |
| `pimd cache status` | Show cache status |
| `pimd validate <INPUT>` | Validate a document |
| `pimd flavor <INPUT>` | Detect Markdown flavor |
| `pimd analyze <DIR>` | Analyze documentation project |
| `pimd frontmatter extract <INPUT>` | Extract frontmatter |
| `pimd frontmatter strip <INPUT> <OUTPUT>` | Strip frontmatter |
| `pimd pipeline list` | List pipeline stages |
| `pimd job run <INPUT> <OUTPUT>` | Run tracked conversion job |
| `pimd job list` | List recent jobs |
| `pimd profile run <INPUT>` | Profile a conversion |

---

## Configuration

PiMD uses hierarchical config resolution:

```
  1. Built-in defaults
  2. ~/.pimd/config.toml    (user global)
  3. ./.pimdconfig           (project-local)
  4. CLI arguments           (highest priority)
```

Example `.pimdconfig`:

```toml
[defaults]
author = "Jane Doe"
company = "ACME Corp"

[conversion]
generate_toc = true
page_numbers = true

[diagram]
cache = true
svg_preferred = true
max_width = 6.5
figure_captions = true
auto_number = true
detect_diagrams = true
default_dpi = 150

[layout]
page_size = "A4"
orientation = "portrait"
margin_top = 1.0
margin_bottom = 1.0
margin_left = 1.25
margin_right = 1.25
default_font = "Calibri"
default_font_size = 11

[security]
max_file_size_mb = 50
max_text_size_chars = 1000000
max_block_count = 10000

[cache]
backend = "memory"
default_ttl = 300
```

---

## Plugin System

### Conversion Plugins

```python
from pimd.plugins import Plugin, ConversionHook, PluginManager

class LoggingPlugin(Plugin):
    name = "logger"
    version = "1.0.0"

    def attach(self, manager):
        manager.register(self, ConversionHook.BEFORE_CONVERT, self.on_start)
        manager.register(self, ConversionHook.AFTER_CONVERT, self.on_end)

    def on_start(self, context):
        print(f"Starting: {context.get('source')}")
        return context

    def on_end(self, context):
        print("Done!")
        return context

manager = PluginManager()
LoggingPlugin().attach(manager)
engine = PiMD(plugins=manager)
```

### Diagram Renderer Plugins

Register third-party diagram renderers without modifying PiMD core:

```python
from pimd import register_diagram_renderer
from pimd.diagrams.renderers import DiagramRenderer
from pimd.diagrams.models import DiagramResult

class CustomDSLRenderer(DiagramRenderer):
    language = "customdsl"
    name = "Custom DSL"
    version = "1.0.0"
    description = "My custom diagram language"

    def is_available(self) -> bool:
        return True  # or check for a CLI tool

    def render(self, source: str, **options) -> DiagramResult:
        # Convert source to SVG or PNG
        svg = convert_custom_dsl_to_svg(source)
        return DiagramResult(
            source=source,
            language=self.language,
            svg=svg,
        )

# Register globally — works with pimd md input.md output.docx
register_diagram_renderer("customdsl", CustomDSLRenderer())
```

### All Renderers Must Implement

```python
class DiagramRenderer:
    language: str = ""
    name: str = ""
    version: str = "1.0.0"
    description: str = ""

    def render(self, source: str, **options) -> DiagramResult:
        """Return DiagramResult with svg (preferred) and/or png."""

    def is_available(self) -> bool:
        """Check if external tools are installed."""
        return True
```

---

## Composable Pipeline

```python
from pimd.pipeline import (
    Pipeline, PipelineContext, PipelineManager,
    ParseStage, TransformStage, RenderStage
)

# Build custom pipeline
pipeline = Pipeline("custom")
pipeline.add_stage(ParseStage("parse"))
pipeline.add_stage(TransformStage("diagrams"))
pipeline.add_stage(RenderStage("render"))

ctx = PipelineContext(
    source_text="# Hello",
    output_path="output.docx"
)
ctx, results = pipeline.run(ctx)

# Or use defaults
pm = PipelineManager()
pipeline = pm.default_md_pipeline()
```

---

## Composing a Book

```json
{
  "title": "The Great Book",
  "author": "Jane Doe",
  "parts": [
    {
      "title": "Part I: Foundations",
      "chapters": [
        { "source": "chapters/intro.md" },
        { "source": "chapters/setup.md" }
      ]
    },
    {
      "title": "Part II: Advanced",
      "chapters": [
        { "source": "chapters/deep-dive.md" }
      ]
    }
  ],
  "appendices": [
    { "source": "appendices/api.md", "title": "API Reference" }
  ]
}
```

```bash
pimd book compile book.json my-book.docx
```

---

## Project Support

### Obsidian Vault Export

```python
from pimd import PiMD

engine = PiMD()
engine.md_text_to_docx("Obsidian note content", "output.docx")
```

### MkDocs Project

```bash
pimd project ./my-mkdocs-site/docs ./output-docs --format docx
```

### Docusaurus

```bash
pimd project ./docusaurus/docs ./output --format docx
```

### Sphinx / RST

```bash
pimd project ./sphinx-docs/source ./output --format docx
```

---

## Advanced Usage

### With Redis Caching

```python
from pimd import PiMD
from pimd.caching.redis_cache import RedisCacheBackend

engine = PiMD(cache=RedisCacheBackend(
    host="localhost",
    port=6379,
    db=0,
    default_ttl=3600
))
```

### Strict Safety Limits

```python
from pimd import PiMD
from pimd.safety import SafetyLimits

engine = PiMD(limits=SafetyLimits.strict())
```

### Performance Profiling

```python
engine = PiMD()
result = engine.md_to_docx("input.md", "output.docx")
report = result.report
print(f"Parse time: {report.metrics.parse_time:.2f}s")
print(f"Render time: {report.metrics.render_time:.2f}s")
print(f"Total time: {report.metrics.total_time:.2f}s")
```

---

## Comparison

Evidence-based comparison of PiMD against other document conversion tools. Each feature is verified against source code, tests, and documentation.

### Feature Comparison

| Feature | PiMD | Pandoc | Quarto | Sphinx | MkDocs | python-docx |
|---------|------|--------|--------|--------|--------|-------------|
| Markdown → DOCX | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| HTML → DOCX | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Python library API | ✅ | ⚠️ Limited | ⚠️ Limited | ✅ | ⚠️ Limited | ✅ |
| CLI | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Automatic diagram rendering | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Mermaid | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| PlantUML | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| Graphviz / DOT | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| D2 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| BlockDiag family (5 formats) | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| BPMN | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Vega / Vega-Lite | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| ASCII art diagrams | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Auto diagram detection | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| SHA256 diagram caching | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Figure numbering | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| LaTeX → OMML (editable Word eq) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| LaTeX → SVG fallback | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Equation numbering | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Template system | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Brand identity | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Cover page | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Table of Contents | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Page numbers | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Header / Footer | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Multi-format export | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| PDF export | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Batch conversion | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Book compilation | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Report generation | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Citation / BibTeX | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Document merging | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Plugin system | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| Plugin renderers | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Obsidian compatibility | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| MkDocs compatibility | ✅ | ❌ | ❌ | ❌ | N/A | ❌ |
| Docusaurus compatibility | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Sphinx compatibility | ✅ | ❌ | ❌ | N/A | ❌ | ❌ |
| Frontmatter | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Callouts / Admonitions | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Footnotes | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Large file streaming | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Incremental builds | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Parallel processing | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Memory caching | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Redis caching | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Safety limits | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Profiling | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Composable pipeline | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| In-memory (bytes) mode | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Async API | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Web framework examples | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |

Legend:
- ✅ = Supported natively
- ❌ = Not supported
- ⚠️ = Limited / requires external tool or scripting
- N/A = Not applicable

### Evidence Sources

- **PiMD features**: verified against source code at `src/pimd/`, tests at `tests/`, and CLI at `src/pimd/cli/app.py`
- **Pandoc features**: based on Pandoc 3.x documentation at https://pandoc.org
- **Quarto features**: based on Quarto 1.5 documentation at https://quarto.org
- **Sphinx features**: based on Sphinx 8.x documentation at https://www.sphinx-doc.org
- **MkDocs features**: based on MkDocs 1.6 documentation at https://www.mkdocs.org
- **python-docx features**: based on python-docx 1.1 documentation at https://python-docx.readthedocs.io

---

## Why Choose PiMD

Based on verified, implemented features:

- **Python-native API** — PiMD is a Python library first, CLI second. Import `PiMD()` and convert in one line.
- **Automatic diagram rendering** — diagrams in fenced code blocks are detected, rendered, and embedded during conversion. No separate render command needed.
- **Editable Word equations** — LaTeX math is converted to native OMML (Office Math Markup Language), editable in Microsoft Word's equation editor. Not images.
- **16 diagram renderers** — Mermaid, PlantUML, Graphviz, D2, BlockDiag family (5), ASCII, SVG, BPMN, Vega, Vega-Lite built in. Register more via plugin API.
- **SHA256 content-hash caching** — rendered diagrams are cached by `SHA256(language + source)`. Unchanged diagrams skip re-rendering.
- **Professional DOCX output** — center-aligned diagrams, auto-incrementing figure numbers, captions, proper scaling, error placeholders.
- **Composable pipeline** — `Pipeline` class with `ParseStage`, `TransformStage`, `RenderStage` for custom conversion workflows.
- **Plugin system** — lifecycle hooks (`before_parse`, `after_parse`, `before_render`, `after_render`) for custom processing.
- **Ecosystem compatibility** — imports Markdown from Obsidian, MkDocs, Docusaurus, and Sphinx projects without pre-processing.
- **In-memory conversion mode** — convert Markdown/HTML strings to DOCX `bytes` without writing to disk. Ideal for web frameworks.
- **Enterprise safety** — configurable limits on file size, text length, block count, nesting depth. Path traversal protection.

---

## When To Use PiMD

PiMD is a good choice for:

- **Python applications** that need automated DOCX generation from Markdown or HTML
- **Report generation** — structured reports (executive, technical, audit, project, research) with built-in templates
- **Documentation pipelines** — CI/CD workflows that convert Markdown documentation to DOCX for distribution
- **Web frameworks** (FastAPI, Flask, Django) — server-side document generation using the in-memory bytes API
- **Diagram-rich documents** — technical papers, architecture docs, API specs that use Mermaid, PlantUML, Graphviz, or other diagram languages
- **Scientific/technical writing** — documents with LaTeX equations that must be editable in Word
- **Enterprise document workflows** — where safety limits, branding, caching, and plugin hooks are required
- **Documentation site exports** — converting MkDocs, Docusaurus, Sphinx, or Obsidian projects to DOCX

---

## When Another Tool May Be Better

- **Pandoc** — if you need maximum format compatibility (100+ input/output formats). Pandoc supports formats like EPUB, LaTeX, Man pages, etc. that PiMD does not.
- **Quarto** — if you are doing scientific publishing with computational notebooks (Jupyter, R Markdown integration). Quarto's notebook execution and cross-format rendering is more mature.
- **MkDocs / Sphinx** — if your primary output is a documentation website (HTML). These tools have richer web theming, search, and navigation features than PiMD.
- **python-docx** — if you need fine-grained, imperative control over every XML element in a DOCX file. python-docx gives you direct access to the OOXML structure. PiMD works at a higher abstraction level.

---

## Development

```bash
git clone https://github.com/devasishpal/PiMd.git
cd PiMd
pip install -e ".[all]"
pip install hatchling build

# Run tests
python -m pytest tests/ -v

# Lint
ruff check src/ tests/

# Build package
python -m build
```

### Test Suite
```
17 test files covering:
├── API              ├── Diagrams (105 tests)  ├── Equations
├── Renderer         ├── Themes                ├── CLI
├── Config           ├── Frontmatter           ├── GitHub Features
├── Compatibility    ├── HTML                  ├── Markdown
├── Engine Features  ├── Project Level         ├── Publishing
└── Stress/Performance
```

---

## License

MIT License — see [LICENSE](LICENSE).
