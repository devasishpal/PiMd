# PiMD

**Professional Markdown and HTML to DOCX conversion framework.**

PiMD converts Markdown and HTML documents into polished, publication-quality DOCX files. Supports the widest range of documentation ecosystems — GFM, GitLab, MkDocs, Sphinx, Docusaurus, Obsidian, Quartz — with automatic flavor detection, frontmatter parsing (YAML/TOML/JSON), callouts, footnotes, diagrams, equations, citations, and enterprise publishing (branding, templates, reports, books, PDF export).

## Installation

```bash
pip install pimd
```

## Quick Start

### CLI

```bash
# Basic conversion
pimd md input.md output.docx

# With table of contents and page numbers
pimd md guide.md guide.docx --toc --page-numbers

# With cover page and metadata
pimd md report.md report.docx --cover --title "Annual Report" --author "Alice"

# Analyze a documentation project
pimd analyze docs/

# Convert an entire repository
pimd repo docs/ output/

# Detect Markdown flavor
pimd flavor input.md

# Validate document
pimd validate input.md
```

### Python API

```python
from pimd import PiMD

# High-level convenience
engine = PiMD()
engine.md_to_docx("input.md", "output.docx")

# Ecosystem conversion
from pimd.obsidian import VaultExporter, VaultConfig
from pimd.sphinx import SphinxProjectConverter
from pimd.repository import RepositoryConverter
```

## Features

### Core
| Feature                   | Status  |
|---------------------------|---------|
| H1–H6 headings            | Done |
| Paragraphs                | Done |
| Bold / Italic / Code      | Done |
| Fenced & indented code    | Done |
| Ordered / unordered lists | Done |
| Nested lists              | Done |
| Blockquotes               | Done |
| Links (clickable)         | Done |
| Images (with fallback)    | Done |
| Tables (styled)           | Done |
| Horizontal rules          | Done |
| Document metadata         | Done |
| Table of contents         | Done |
| Page numbers              | Done |
| Headers / footers         | Done |
| Cover page                | Done |
| Document statistics       | Done |
| Professional styles       | Done |
| Theme system              | Done |
| HTML → DOCX               | Done |

### Advanced Markdown
| Feature                          | Status  |
|----------------------------------|---------|
| GitHub Flavored Markdown (GFM)   | Done |
| GitLab Markdown                  | Done |
| MkDocs Markdown                  | Done |
| Sphinx Markdown / RST            | Done |
| Docusaurus Markdown (MDX)        | Done |
| Obsidian Markdown                | Done |
| Quartz Markdown                  | Done |
| Automatic flavor detection       | Done |
| Compatibility layer              | Done |

### Frontmatter
| Feature        | Status  |
|----------------|---------|
| YAML           | Done |
| TOML           | Done |
| JSON           | Done |
| Auto-detect    | Done |
| Extract/strip  | Done |

### GitHub Features
| Feature           | Status  |
|-------------------|---------|
| Task lists        | Done |
| Tables            | Done |
| Alerts            | Done |
| Footnotes         | Done |
| Anchors           | Done |
| Reference links   | Done |

### Ecosystem Support
| Feature            | Status  |
|--------------------|---------|
| MkDocs (mkdocs.yml, nav) | Done |
| Docusaurus (sidebars, versions) | Done |
| Obsidian (wikilinks, embeds, vaults) | Done |
| Sphinx (RST directives, conf.py)    | Done |

### Callout Engine
| Type            | Status  |
|-----------------|---------|
| NOTE            | Done |
| TIP             | Done |
| WARNING         | Done |
| DANGER          | Done |
| INFO            | Done |
| SUCCESS         | Done |
| QUESTION        | Done |
| IMPORTANT       | Done |
| ABSTRACT        | Done |
| TODO / FAILURE / BUG / EXAMPLE / QUOTE | Done |

### Footnotes
| Feature                        | Status  |
|--------------------------------|---------|
| Markdown footnotes             | Done |
| DOCX footnotes (XML)           | Done |
| Cross references               | Done |
| Back-references                | Done |

### Attachments
| Feature           | Status  |
|-------------------|---------|
| Images            | Done |
| SVG               | Done |
| PDF               | Done |
| Archives / Fonts  | Done |
| Embedded assets   | Done |

### Repository Mode
| Feature                 | Status  |
|-------------------------|---------|
| Repository type detection | Done |
| Bulk conversion         | Done |
| docs/ / wiki/ / kb/     | Done |
| Incremental builds      | Done |
| Parallel processing     | Done |

### Project Analyzer
| Feature             | Status  |
|---------------------|---------|
| Broken links        | Done |
| Missing assets      | Done |
| Missing references  | Done |
| Duplicate pages     | Done |
| Unused files        | Done |
| Orphaned assets     | Done |

### Export Profiles
| Profile     | Status  |
|-------------|---------|
| GitHub      | Done |
| Academic    | Done |
| Corporate   | Done |
| Book        | Done |
| Technical   | Done |

### Enterprise
| Feature             | Status  |
|---------------------|---------|
| Branding system     | Done |
| Template system     | Done |
| Report generation   | Done |
| Book compilation    | Done |
| Citations (BibTeX)  | Done |
| PDF export          | Done |
| Pipeline stages     | Done |
| Background jobs     | Done |
| Document merging    | Done |
| Document validation | Done |
| Safety guard        | Done |
| Recovery mode       | Done |
| Caching (memory/Redis) | Done |
| Streaming (large files) | Done |
| Incremental builds  | Done |
| Performance profiling | Done |

### Diagrams
| Language   | Status  |
|------------|---------|
| Mermaid    | Done |
| PlantUML   | Done |
| Graphviz   | Done |
| D2         | Done |
| ASCII art  | Done |
| SVG inline | Done |

### Equations
| Feature            | Status  |
|--------------------|---------|
| LaTeX → OMML       | Done |
| LaTeX → SVG        | Done |
| Inline / display   | Done |
| Chemical formulas  | Done |
| Equation numbering | Done |
| Validation         | Done |

## CLI Reference

```
pimd md          — Convert Markdown file to DOCX
pimd html        — Convert HTML file to DOCX
pimd batch       — Batch-convert files in a directory
pimd merge       — Merge multiple documents
pimd analyze     — Analyze documentation project
pimd repo        — Convert entire repository
pimd validate    — Validate document for common issues
pimd flavor      — Detect Markdown flavor
pimd info        — Display version, themes, formats
pimd doctor      — Run system diagnostics
pimd diagrams    — Diagram rendering tools
pimd equations   — Equation rendering tools
pimd export      — Multi-format export (docx, pdf, html, txt)
pimd template    — Template management
pimd brand       — Brand management
pimd report      — Report generation
pimd book        — Book compilation
pimd citations   — Citation management
pimd project     — Project conversion
pimd config      — Configuration management
pimd pipeline    — Pipeline management
pimd cache       — Cache management
pimd job         — Background job system
pimd profile     — Performance profiling
pimd frontmatter — Frontmatter management
pimd assets      — Asset management
pimd completion  — Generate shell completion
```

## Development

```bash
git clone https://github.com/yourname/pimd.git
cd pimd
py -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check src/ tests/
```

## License

MIT
