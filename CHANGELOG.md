# Changelog

All notable changes to PiMD are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] — 2024-12-03

### Added

- Universal diagram rendering architecture with auto-detection
  - `DiagramRegistry` with module-level `register_diagram_renderer()`, `get_diagram_renderer()`, `list_diagram_renderers()`
  - 8 new renderers: BlockDiag, SeqDiag, ActDiag, NwDiag, PacketDiag, BPMN, Vega, Vega-Lite
  - Auto-diagram language detection (regex patterns + ASCII heuristics)
  - `AUTO_DETECT_PATTERNS` and `DIAGRAM_LANGUAGE_ALIASES` in diagram models
- SHA256 content-hash caching (memory + filesystem backends)
- Professional DOCX embedding for diagrams: centered OOXML drawing XML, auto-incrementing figure counter, captions, error placeholders, SVG→PNG fallback
- Plugin registration API: third-party renderers via `register_diagram_renderer()`
- 105 new tests covering diagram subsystem (models, registry, engine, auto-detection, caching, renderers, plugins, DOCX integration, doctor)
- Support for 16 diagram languages with language aliases

### Changed

- Extended `Diagram` model with `svg_bytes` and `error` fields
- `ConversionService._process_diagrams()` uses auto-detection when no language specified
- `DocxRenderer._render_diagram()` enhanced with raw OOXML drawing XML
- Added `diagram` config section to built-in defaults

## [1.0.0] — 2024-11-15

### Added

- Initial production release
- Core document model with dataclass-based elements (Heading, Paragraph, CodeBlock, Table, List, Image, etc.)
- Markdown parser based on markdown-it-py with full GFM support
- HTML parser based on BeautifulSoup4
- World-class DOCX renderer with:
  - A4 page size, narrow margins (0.5 inch)
  - Professional styles and typography
  - Custom headers, footers, page numbers
  - Cover pages with metadata
  - Watermarks (Draft, Confidential, etc.)
  - Section breaks and multi-section documents
  - Multi-column layouts
  - Table of Contents
  - Figure and table numbering
  - Cross references
  - Footnotes and endnotes
  - Hyperlinks and internal references
  - Native equations (LaTeX → OMML)
- Diagram support: Mermaid, PlantUML, Graphviz, D2, ASCII, SVG
- Equation engine: LaTeX → OMML compiler with SVG fallback
- Template system with 5 built-in templates (Professional, Technical, Academic, Business, Book)
- Plugin system with lifecycle hooks (BEFORE_PARSE, AFTER_PARSE, etc.)
- Theme system with Theme ABC and ProfessionalTheme
- Branding: cover pages, watermarks, brand management
- Citation engine with BibTeX support and APA/MLA/Chicago styles
- Report engine with table of figures
- Book compiler for multi-document books
- Document merger
- Batch processor
- Pipeline engine with composable stages
- Caching: memory and Redis backends
- Safety limits and validation
- Streaming support for large files
- Parallel execution (thread + process pools)
- Incremental builds
- Profiling and observability
- Ecosystem importers:
  - Sphinx (RST → Markdown, conf.py parser, project converter)
  - MkDocs (mkdocs.yml parser, nav parser, project converter)
  - Docusaurus (sidebar parser, versioned docs, JS/TS support)
  - Obsidian (WikiLink parsing, callouts, graph builder, vault exporter)
- CLI with 50+ commands using Typer + Rich
  - `pimd md` — convert Markdown to DOCX
  - `pimd html` — convert HTML to DOCX
  - `pimd info` — system information
  - `pimd doctor` — dependency check
  - `pimd diagrams doctor` — diagram tool check
  - `pimd equations doctor` — equation tool check
  - `pimd repo` — repository-level conversion
  - `pimd batch` — batch conversion
  - `pimd init` — project initialization
  - Shell completion
- Public API: `PiMD` class with sync/async methods
  - `engine.md_to_docx()`, `engine.html_to_docx()`
  - `engine.md_text_to_docx()`, `engine.html_text_to_docx()`
  - `engine.md_text_to_docx_bytes()`, `engine.html_text_to_docx_bytes()`
  - Async variants of all methods
- Comprehensive test suite: 600+ tests
- Documentation: migration guide, performance guide, scaling guide, etc.
- Support for Python 3.10, 3.11, 3.12, 3.13

[1.1.0]: https://github.com/devasishpal/PiMd/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/devasishpal/PiMd/releases/tag/v1.0.0
