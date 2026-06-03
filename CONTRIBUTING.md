# Contributing to PiMD

Thank you for your interest in contributing to PiMD! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful, inclusive, and harassment-free environment for everyone.

## Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/PiMd.git
   cd PiMd
   ```
3. **Install in development mode**:
   ```bash
   pip install -e ".[dev,diagrams,equations,citations,export,redis,profiling]"
   ```
4. **Run the tests** to verify your setup:
   ```bash
   python -m pytest tests/ -v
   ```

## Development Workflow

### Branching

- Create a feature branch from `main`: `git checkout -b feature/your-feature-name`
- Use prefixes: `feature/`, `fix/`, `docs/`, `refactor/`, `test/`

### Code Style

- **Python**: 3.10+ with type hints everywhere
- **Linting**: We use `ruff` — run before committing:
  ```bash
  ruff check src/ tests/
  ```
- **Formatting**: `ruff format` — configure your editor to format on save

### Testing

- **All contributions must include tests**.
- Run the full test suite:
  ```bash
  python -m pytest tests/ -v --tb=short
  ```
- Run a specific test file:
  ```bash
  python -m pytest tests/test_api.py -v
  ```
- Run tests with coverage:
  ```bash
  pip install pytest-cov
  python -m pytest tests/ --cov=src/pimd
  ```

### Type Checking

While not enforced by CI, consider using `mypy` for type checking:
```bash
pip install mypy
mypy src/pimd/ --ignore-missing-imports
```

## Architecture Overview

PiMD follows a layered architecture:

```
Input (Markdown/HTML)
    ↓
Parser → Document Model (dataclasses)
    ↓
Pipeline Stages (transform, plugin hooks, safety checks)
    ↓
Renderer (DOCX / HTML)
    ↓
Output (.docx file / bytes)
```

Key design principles:

- **Library-first**: The `PiMD` class in `pimd/api/pimd.py` is the primary API
- **Parser → Model → Renderer**: All input formats convert to the shared `Document` model
- **Plugin hooks**: Lifecycle hooks at every pipeline stage via `pimd.plugins` + `pimd.sdk`
- **Dependency injection**: Caching, plugins, themes injected through constructors
- **Offline-first**: No cloud dependencies; all features work without internet

## Project Structure

```
src/pimd/
├── api/             — Public API (PiMD class)
├── cli/             — CLI commands (Typer + Rich)
├── parsers/         — Input parsers (Markdown, HTML)
├── renderers/       — Output renderers (DOCX, HTML)
├── converters/      — High-level converter wrappers
├── services/        — Business logic layer
├── models.py        — Core document model
├── diagrams/        — Diagram rendering engine
├── equations/       — Equation rendering (LaTeX → OMML)
├── templates/       — Template system with inheritance
├── plugins/         — Plugin framework foundation
├── sdk/             — Extension SDK (typed plugin base classes)
├── themes/          — Theme system
├── branding/        — Cover pages, watermarks
├── caching/         — Cache backends (memory, filesystem, Redis)
├── config/          — Configuration management with schema validation
├── observability/   — Metrics, profiling, conversion reports
├── accessibility/   — Document accessibility validation
├── remote_assets/   — Remote asset download and caching
├── safety/          — Safety limits and validation
├── pipeline/        — Composable pipeline engine
├── export/          — Multi-format export (PDF, HTML, TXT, EPUB, LaTeX)
├── deprecation/     — API deprecation utilities
├── validation/      — Document validation
├── incremental/     — Incremental build tracking
├── jobs/            — Background job system
├── streaming/       — Large file streaming
├── parallel/        — Parallel execution
├── reports/         — Report generation
├── books/           — Book compilation
├── citations/       — BibTeX citation engine
└── compatibility/   — Ecosystem importers (Obsidian, MkDocs, Docusaurus, Sphinx)
```

## Adding a New Feature

1. **Open an issue** first to discuss the feature.
2. **Add a diagram renderer**: Implement `DiagramRenderer` ABC and register with `register_diagram_renderer()`
3. **Add a parser**: Implement a parser that produces the `Document` model
4. **Add a renderer**: Implement a renderer that consumes the `Document` model
5. **Add an Extension SDK plugin**: Subclass one of the `pimd.sdk` base classes (e.g., `DiagramPlugin`, `ExporterPlugin`, `ValidationPlugin`)
6. **Add tests**: Cover success paths, error paths, and edge cases
7. **Update documentation**: If the feature changes the public API or CLI

## Plugin Development Guide

### Defining a Plugin

```python
from pimd.sdk import BasePlugin, Hook, HookScope

class MyPlugin(BasePlugin):
    name = "my-plugin"
    version = "1.0.0"
    description = "Does something useful"

    def attach(self, registry):
        registry.register(self, Hook.PARSE_START, self.on_parse_start, HookScope.DOCUMENT)

    def on_parse_start(self, context):
        # Transform context before parsing
        return context
```

### Typed Plugin Types

| Base Class | Purpose |
|---|---|
| `BasePlugin` | Generic plugin with lifecycle hooks |
| `DiagramPlugin` | Register custom diagram renderers |
| `TemplatePlugin` | Provide custom templates |
| `ExporterPlugin` | Add export format support |
| `RendererPlugin` | Add output renderers |
| `ParserPlugin` | Add input parsers |
| `CitationPlugin` | Add citation styles |
| `AssetPlugin` | Manage document assets |
| `ValidationPlugin` | Add validation rules |
| `PublishingPlugin` | Post-processing after render |

### Event System

```python
from pimd.sdk import EventBus, Event, EventPriority

bus = EventBus()

@bus.on("conversion.complete")
def on_complete(event: Event):
    print(f"Converted: {event.data['output']}")

bus.emit("conversion.complete", {"output": "report.docx"})
```

## Pull Request Process

1. Ensure all tests pass and linting is clean.
2. Update documentation if needed (README, CLI help strings).
3. Add a changelog entry in `CHANGELOG.md`.
4. Submit a PR with a clear description of the changes.
5. Reference any related issues in the PR description.

## Questions?

Open a [GitHub Discussion](https://github.com/devasishpal/PiMd/discussions) or issue.
