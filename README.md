# PiMD — Professional Markdown & HTML to DOCX Framework

> **PiMD** transforms Markdown and HTML into beautifully formatted DOCX documents — with native diagrams, editable equations, themes, templates, branding, and enterprise-scale pipelines.

```ascii
  Markdown ──┐
              ├──► PiMD ──► Professional .docx
  HTML ───────┘              ├── Diagrams (Mermaid, PlantUML, Graphviz, ASCII…)
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
  ┌─────────────┐    ┌──────────────┐    ┌──────────┐
  │ Mermaid     │    │ PlantUML     │    │ Graphviz │
  │ graph/seq/  │    │ sequence/    │    │ DOT lang │
  │ gantt/etc.  │    │ use case/    │    │          │
  └──────┬──────┘    └──────┬───────┘    └────┬─────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
              ┌─────────────────────────┐
              │  DiagramEngine          │
              │  • Caching (mem/Redis)  │
              │  • Parallel rendering   │
              │  • Fallback to code     │
              └────────────┬────────────┘
                           ▼
              ┌─────────────────────────┐
              │   Embedded PNG in DOCX  │
              └─────────────────────────┘
```

Supported diagram languages:

| Language | Tag | Renderer | CLI Tool | Pure Python |
|----------|-----|----------|----------|-------------|
| Mermaid | ```` ```mermaid ```` | MermaidRenderer | `mmdc` | ❌ |
| PlantUML | ```` ```plantuml ```` | PlantUMLRenderer | `plantuml` | ❌ |
| Graphviz | ```` ```dot ```` | GraphvizRenderer | `dot` | ❌ |
| D2 | ```` ```d2 ```` | D2Renderer | `d2` | ❌ |
| ASCII art | ```` ```ascii ```` | AsciiRenderer | None | ✅ (Pillow) |
| SVG | ```` ```svg ```` | SvgRenderer | None | ✅ |

**Auto-detection**: Untagged code blocks containing box-drawing characters (`┌─┐│└┘`) or classic ASCII art patterns (`+--+`, `|  |`) are automatically rendered as ASCII diagrams.

### Equations
Write LaTeX math — it becomes **native Word equations** (editable OMML, not images):

```ascii
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
```ascii
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
```ascii
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

External CLI tools for diagram rendering (install separately):
- **Mermaid**: `npm install -g @mermaid-js/mermaid-cli`
- **PlantUML**: `java -jar plantuml.jar` or `apt install plantuml`
- **Graphviz**: `apt install graphviz` or `choco install graphviz`
- **D2**: `curl -fsSL https://d2lang.com/install.sh | sh -s --`

---

## Quick Start

### CLI

```bash
# Basic conversion
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

# File to file
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

```ascii
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

### Document Model

```ascii
  Document
  ├── Heading (level 1-6)
  ├── Paragraph
  │   └── Span (bold, italic, code, link, math, underline)
  ├── CodeBlock (language-tagged)
  ├── Diagram (PNG bytes, source, language, caption)
  ├── EquationBlock (LaTeX, OMML XML, SVG, number)
  ├── Blockquote (nested)
  ├── BulletList / OrderedList
  │   └── ListItem → children
  ├── Table (headers + rows)
  ├── Image (path, alt, dimensions)
  └── HorizontalRule
```

### Service Architecture

```ascii
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
| `pimd md <INPUT> <OUTPUT>` | Convert Markdown file to DOCX |
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
├── API              ├── Diagrams          ├── Equations
├── Renderer         ├── Themes            ├── CLI
├── Config           ├── Frontmatter       ├── GitHub Features
├── Compatibility    ├── HTML              ├── Markdown
├── Engine Features  ├── Project Level     ├── Publishing
└── Stress/Performance
```

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Why PiMD?

```ascii
  ┌────────────────────────────────────────────────────────────┐
  │                    Why Not Just Pandoc?                     │
  ├────────────────────────────────────────────────────────────┤
  │                                                            │
  │  Pandoc                          PiMD                     │
  │  ──────                          ────                      │
  │  • Diagrams as images            • Diagrams rendered from  │
  │  • Equations as images             code blocks             │
  │  • Basic templates               • Equations as editable   │
  │  • No plugin system                OMML                    │
  │  • No caching                    • Themes + templates      │
  │  • No safety layer               • Branding system         │
  │  • No project-level tools        • Plugin hooks            │
  │  • No book compilation           • Redis + memory caching  │
  │  • Single-format output          • SafetyGuard security    │
  │                                  • Book compiler           │
  │                                  • Batch/project converter │
  │                                  • Pipeline framework      │
  │                                  • Async + in-memory API   │
  │                                  • Web framework examples  │
  └────────────────────────────────────────────────────────────┘
```
