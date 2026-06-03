# PiMD Repository Guide

Convert entire documentation repositories to DOCX in a single command.

## Supported Repository Types

| Type | Detection | Example |
|------|-----------|---------|
| MkDocs | `mkdocs.yml` | Material for MkDocs projects |
| Docusaurus | `docusaurus.config.js` | Docusaurus 2/3 projects |
| Sphinx | `conf.py` | Read the Docs projects |
| Obsidian | `.obsidian/` directory | Obsidian vaults |
| GitHub Wiki | `wiki/` directory | GitHub wiki repositories |
| Plain Markdown | `docs/`, `wiki/`, `kb/` directories | Any docs folder |
| Unknown | Fallback | Root-level `.md` files |

## CLI Usage

```bash
# Basic repository conversion
pimd repo docs/ output/

# With specific output format
pimd repo docs/ output/ --format pdf

# Preserve directory structure
pimd repo docs/ output/ --preserve-structure

# Parallel conversion
pimd repo docs/ output/ --workers 4

# Merge all documents into one output
pimd repo docs/ output/ --merge

# Incremental (skip unchanged files)
pimd repo docs/ output/ --incremental
```

## Python API

```python
from pimd.repository import (
    discover_repository,
    RepositoryConverter,
    RepositoryConfig,
)

# Discover repository type
result = discover_repository("docs/")
print(f"Type: {result.repo_type}")
print(f"Files: {result.file_count}")

# Configure conversion
config = RepositoryConfig(
    output_mode="multi",       # "multi" or "single" or "merge"
    parallel_workers=4,
    preserve_structure=True,
    output_format="docx",
    incremental=True,
)

# Convert
converter = RepositoryConverter(config=config)
stats = converter.convert("docs/", "output/")
print(f"Converted: {stats['converted']}")
print(f"Errors: {stats['errors']}")
```

## Configuration

With `pimd.toml` in your repository root:

```toml
[repository]
output_mode = "multi"
output_format = "docx"
preserve_structure = true
parallel_workers = 2
incremental = true

[repository.include]
patterns = ["**/*.md", "**/*.mdx"]

[repository.exclude]
patterns = ["node_modules/**", ".obsidian/**"]
```

## Directory Structure Detection

PiMD searches for these directory names as documentation roots:

- `docs/`, `wiki/`, `knowledge-base/`, `kb/`
- `documentation/`, `help/`, `guide/`, `manual/`
- `content/`, `markdown/`, `pages/`, `src/`, `source/`

## Output Modes

- **multi** — One DOCX per source file, preserving structure
- **single** — Single DOCX with all content
- **merge** — Combined DOCX with chapter breaks
- **auto** — Merge for small repos, multi for large repos

## Incremental Builds

```python
from pimd.incremental import IncrementalBuildTracker

tracker = IncrementalBuildTracker()
# Only converts files that have changed since last build
tracker.build("docs/", "output/")
```

## Error Recovery

```python
from pimd.recovery import safe_convert

# Fault-tolerant conversion
result = safe_convert("input.md", "output.docx")
print(result.warnings)  # List of non-fatal issues
```
