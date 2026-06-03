# Contributing to PiMD

Thank you for considering contributing to PiMD! This document outlines the process and standards.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/yourname/pimd.git
cd pimd

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install in editable mode
pip install -e ".[dev]"
```

## Code Style

PiMD uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Type Checking

All code must pass strict type checking:

```bash
mypy src/
```

## Testing

Write tests for all new functionality:

```bash
pytest
```

With coverage:

```bash
pytest --cov=src/pimd
```

## Pull Request Process

1. Ensure all tests pass
2. Run Ruff and fix any issues
3. Add tests for new features
4. Update documentation if needed
5. Use conventional commit messages

## Project Architecture

- `src/pimd/converters/` - High-level conversion orchestration
- `src/pimd/parsers/` - Input format parsers (Markdown, HTML)
- `src/pimd/renderers/` - Output format renderers (DOCX)
- `src/pimd/utils/` - Shared utilities (logging, etc.)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
