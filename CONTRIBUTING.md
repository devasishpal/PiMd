# Contributing to PiMD

Thank you for your interest in contributing to PiMD! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful, inclusive, and harassment-free environment for everyone.

## Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork**: `git clone https://github.com/your-username/PiMd.git`
3. **Install in development mode**:

   ```bash
   cd PiMd
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
Pipeline Stages (transform, plugin hooks)
    ↓
Renderer (DOCX/HTML)
    ↓
Output (.docx file / bytes)
```

Key design principles:

- **Library-first**: The `PiMD` class in `pimd/api/pimd.py` is the primary API
- **Parser → Model → Renderer**: All input formats convert to the shared `Document` model before rendering
- **Plugin hooks**: Lifecycle hooks at every pipeline stage
- **Dependency injection**: Caching, plugins, themes injected through constructors

## Adding a New Feature

1. **Open an issue** first to discuss the feature.
2. **Add a diagram renderer**: Implement `DiagramRenderer` ABC and register with `register_diagram_renderer()`
3. **Add a parser**: Implement a parser that produces the `Document` model
4. **Add a renderer**: Implement a renderer that consumes the `Document` model
5. **Add tests**: Cover success paths, error paths, and edge cases

## Pull Request Process

1. Ensure all tests pass and linting is clean.
2. Update documentation if needed.
3. Add a changelog entry in `CHANGELOG.md`.
4. Submit a PR with a clear description of the changes.

## Project Structure

```
src/pimd/
├── api/            — Public API (PiMD class)
├── cli/            — CLI commands (Typer + Rich)
├── parsers/        — Input parsers (Markdown, HTML)
├── renderers/      — Output renderers (DOCX, HTML)
├── converters/     — High-level converter wrappers
├── services/       — Business logic layer
├── models.py       — Core document model
├── diagrams/       — Diagram rendering engine
├── equations/      — Equation rendering (LaTeX → OMML)
├── templates/      — Template system
├── plugins/        — Plugin framework
├── themes/         — Theme system
├── branding/       — Cover pages, watermarks
├── citations/      — Citation engine
├── caching/        — Cache backends
├── pipeline/       — Pipeline engine
├── safety/         — Safety limits
├── validation/     — Document validation
└── config/         — Configuration management
```

## Questions?

Open a [GitHub Discussion](https://github.com/devasishpal/PiMd/discussions) or issue.
