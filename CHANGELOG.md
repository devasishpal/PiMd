# Changelog

All notable changes to PiMD are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-06-05

### Major New Features

- **EPUB 3.2 Renderer** (`pimd.export.formats.epub`): Full EPUB package generation with XHTML content, CSS styling, NCX + nav.xhtml table of contents, cover pages, OPF metadata, embedded images/diagrams, reflowable layout, and built-in EPUB validation
- **LaTeX Renderer** (`pimd.export.formats.latex`): Full Markdown-to-LaTeX pipeline supporting headings (section/ subsection), tables (tabular with booktabs), code blocks (listings), citations (biblatex), images (graphicx), footnotes, math expressions (amsmath), and cross-references (hyperref). Supports article, report, and book document classes.
- **PDF/A Archival Output** (`pimd.export.pdf`): PDF/A-1b and PDF/A-2b generation via LibreOffice PDF/A export filter or native fpdf2 with font embedding, metadata preservation, and automatic fallback chain
- **Internationalization (i18n)** (`pimd.i18n`): Unicode script detection (LTR, RTL, CJK, neutral), RTL language support (Arabic, Persian, Urdu, Hebrew) with `bidi` and `arabic_reshaper`, CJK support (Chinese, Japanese, Korean) with language-aware typography, DOCX/EPUB/LaTeX i18n configuration helpers
- **Collaborative Editing** (`pimd.revisions`): Document revision model with RevisionTracker managing insertions/deletions/replacements/formatting changes, Comment/annotation system with threading and resolution, ReviewMetadata for session management, review summary export APIs

### New Features

- **CLI `pimd epub`**: Convert Markdown to EPUB 3.2 with optional EPUB validation
- **CLI `pimd latex`**: Convert Markdown to LaTeX with configurable document class
- **CLI `pimd language`**: Detect script direction (LTR/RTL/CJK) of any document
- **CLI `pimd revision`**: Initialize, add, and list tracked document revisions
- **CLI `pimd export epub`**: Export to EPUB via unified export system
- **CLI `pimd export latex`**: Export to LaTeX via unified export system
- **CLI `pimd export pdfa`**: Export to PDF/A archival format
- **Auto-format detection**: CLI commands accept format based on file extension
- **Extended `ExportFormat` enum**: EPUB, LATEX, PDFA added to supported formats
- **EpubRenderer**: Validates generated EPUB packages with structural checks
- **LatexRenderer**: Produces clean, readable LaTeX with proper escaping

### Improvements

- **Modular renderer architecture**: EPUB and LaTeX renderers follow same Document model pattern as DOCX/HTML renderers
- **Optional dependency handling**: EPUB uses lxml (already core dep), LaTeX has zero runtime deps, i18n uses optional bidi/arabic_reshaper
- **Dependency extras**: New extras groups: `epub`, `latex`, `pdfa`, `i18n`, `collaboration`
- **ExportConverter**: Handles EPUB, LaTeX, PDF/A in unified `convert()` method
- **CLI info**: Shows new formats and v2.1.0 features
- **Export doctor**: Checks EPUB, LaTeX, PDF/A, i18n engine availability
- **Logo/badge**: Added pepy.tech total downloads badge to README
- **Version**: 2.1.0, Python 3.10-3.13 compatibility maintained

### Internal

- New `pimd.i18n` package: script detection, language configs, RTL reshaping helpers
- New `pimd.revisions` package: RevisionTracker, Comment, ReviewMetadata models
- Strong type hints across all new modules
- All new modules have 100% offline capability
- Cross-platform support (Windows, macOS, Linux) maintained

### Backward Compatibility

- All existing v2.0.0 APIs remain unchanged
- New formats (EPUB, LaTeX, PDF/A) are additive — no breaking changes
- `ExportFormat` enum gains new members but existing members unchanged
- `ExportOptions` gains new fields with defaults — existing code unaffected
- CLI gains new commands but existing commands unmodified
- Plugin API unchanged

## [2.0.0] - 2026-06-03

### Major Changes

- Version bump to 2.0.0 (breaking changes)
- Plugin ecosystem overhaul with dedicated Extension SDK (`pimd.sdk`)
- Cache framework abstraction with filesystem backend (`pimd.caching.filesystem.FileSystemCache`)
- Configuration system with schema validation and environment variable support (`pimd.config.Config`)
- Observability consolidation: `pimd.observability` absorbs `pimd.profiling`
- New accessibility validation engine (`pimd.accessibility`)
- Remote asset management with SHA256 caching and offline mode (`pimd.remote_assets`)
- Template inheritance system (`pimd.templates.inheritance`)
- Watch mode for automatic rebuilds on file changes (`pimd.export.watch`)
- Multi-file project builds from YAML/JSON/TOML config (`pimd build`)
- New CLI commands: `plugin`, `cache info`, `config init`, `config validate`, `accessibility`, `build`, `watch`

### New Features

- **Extension SDK** (`pimd.sdk`): 9 typed plugin base classes (`BasePlugin`, `DiagramPlugin`, `TemplatePlugin`, `CitationPlugin`, `RendererPlugin`, `ExporterPlugin`, `AssetPlugin`, `ValidationPlugin`, `ParserPlugin`, `PublishingPlugin`) with `EventBus`, `HookRegistry`, and `HookScope`
- **FileSystemCache**: JSON-envelope filesystem cache with per-entry TTL, SHA-256 key hashing, and diagnostics
- **Config schema validation**: `Config.validate()` with typed `ConfigSchemaEntry`, `Config.write_default()`, env var support (`PIMD_*`), dotted key access, TOML serialization
- **AccessibilityEngine**: WCAG-based document validation checking image alt text (1.1.1), heading hierarchy (2.4.10), table headers (1.3.1), reading order, and document structure; CLI `pimd accessibility check` and `pimd accessibility report`
- **RemoteAssetManager**: HTTP/HTTPS asset downloads, content-addressable SHA256 caching, offline mode, domain allowlists, MIME-type detection, configurable TTL and size limits
- **Template inheritance**: `TemplateInheritance` class with chain resolution, deep merge, `create_child()` for deriving templates
- **Watch mode**: Polling-based directory watcher with optional `watchdog` library support, automatic rebuild on file change
- **Multi-file project builds**: `pimd build` command supporting YAML/JSON/TOML project configs with chapter/file lists
- **Plugin CLI**: `pimd plugin install`, `pimd plugin enable`, `pimd plugin disable`, `pimd plugin list`, `pimd plugin doctor`
- **Cache CLI**: `pimd cache info` with diagnostics and statistics
- **Config CLI**: `pimd config init` generates default `.pimdconfig`, `pimd config validate` checks against schema
- **Accessibility CLI**: `pimd accessibility check` (with JSON output and markdown report), `pimd accessibility report`
- **Assets CLI**: `pimd assets list` for inspecting document attachments and asset files
- Job system: `pimd job run` and `pimd job list` for tracked background conversions
- Profiling CLI: `pimd profile run` with `ConversionReport` summary output
- `AccessibilityReport.to_markdown()` for generating detailed accessibility reports
- `Config.find_project_root()` for locating project config from any subdirectory

### Improvements

- **Observability consolidation**: `pimd.observability` now unifies `Timer` (context manager + lap support), `Profiler`, `ConversionReport` (combined conversion metadata + profiling), `BuildMetrics`, `ExecutionReport`, `MetricsCollector`
- **Configuration overhaul**: 5-tier priority (built-in defaults < user global < project < env vars < runtime), `Config.apply_env()`, `Config.to_layout_config()`, `Config.find_config_files()`
- **Cache framework**: Abstract `CacheBackend` ABC, `CacheStats` dataclass, `MemoryCache` with thread-safe TTL, `FileSystemCache` with JSON serialization, `CacheMetricsCollector`, `diagnose_cache()` helper
- **CLI improvements**: Rich-formatted tables, step displays, doctor commands for all subsystems
- **Error handling**: `PiMDDeprecationWarning` category, graceful fallbacks for missing dependencies
- **Parallel processing**: Max worker configuration via CLI and config, per-feature parallel toggle
- **Security hardening**: Env-var configurable limits for input size, nesting depth, block count, image size, allowed/blocked paths
- **Deprecation system**: `@deprecated` decorator and `@deprecate_parameter` decorator for API migration
- **Export formats**: EPUB, LaTeX, PPTX export support added
- **Project structure**: Clear separation of concerns with 56 subpackages under `src/pimd/`

### Bug Fixes

- Robust TOML loading with `tomllib`/`tomli` fallback
- Graceful handling of missing config files
- `MemoryCache` TTL expiry uses `time.monotonic()` for correctness
- Config merge does not overwrite existing files on `write_default()`
- File system cache directory auto-creation with `mkdir(parents=True, exist_ok=True)`
- Remote asset cache accounts for file age in TTL checking
- Watch mode handles `KeyboardInterrupt` cleanly

### Deprecations

- `pimd.profiling` is deprecated — use `pimd.observability` instead. The `profiling` module now re-exports from `observability` and will be removed in 3.0.0
- Legacy project config names `pimd.toml` and `.pimd/config.toml` are deprecated in favor of `.pimdconfig`
- `profiling` extra in `pyproject.toml` is deprecated — observability metrics are now included in the core package

### Breaking Changes

- Minimum Python version: 3.10 (dropped 3.9 support)
- `profiling` module renamed to `observability`; imports from `pimd.profiling` still work via re-exports
- Configuration priority order changed: project-local config now takes priority over user global config
- `CacheBackend` is now an abstract base class — custom backends must implement `get()`, `set()`, `delete()`, `clear()`
- `.pimdconfig` is the canonical project config filename; `pimd.toml` and `.pimd/config.toml` are still supported but deprecated
- `SafetyLimits` interface updated to use env-var-driven configuration
- `ExportConverter` API revised with unified `convert()` method
- CLI subcommand reorganization: `diagrams`, `equations`, `template`, `brand`, `report`, `book`, `export` moved to sub-typers

### Internal

- Full type hint coverage across all modules (Python 3.10+ syntax)
- Ruff linting configured with E, F, I, N, W, UP rule sets
- Pytest-asyncio with auto mode for async test support
- Hatchling build backend migration
- Comprehensive `__all__` exports in all public modules
- Modular architecture: 56 subpackages, clear separation between API, CLI, services, and engines
- All diagram renderers consolidated under `pimd.diagrams.renderers`
- Plugin system separated into `pimd.plugins` (foundation) and `pimd.sdk` (extension API)
- Template engine extracted to `pimd.templates` with models, manager, loader, and inheritance
- Branding, layout, and citation engines refactored as standalone services

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
- Public API: `PiMD` class with sync/async methods
- Comprehensive test suite: 600+ tests
- Documentation: migration guide, performance guide, scaling guide, etc.
- Support for Python 3.10, 3.11, 3.12, 3.13

[2.0.0]: https://github.com/devasishpal/PiMd/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/devasishpal/PiMd/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/devasishpal/PiMd/releases/tag/v1.0.0
