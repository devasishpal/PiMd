# AGENTS.md — Lessons Learned

## CLI & Encoding
- Windows cp1252 terminals cannot render `\u2713` (✓) or `\u2717` (✗). Use `[green]Y[/]` / `[red]X[/]` with Rich markup for safety.
- Rich's `Table.add_row()` crashes on non-string values; always convert lists to comma-separated strings before passing.

## Validation & Accessibility
- `DocumentValidator.validate_file()` and `AccessibilityEngine.validate_file()` were calling `MarkdownConverter().parse_text()` which does not exist. Use `MarkdownParser().parse(content)` to get a `Document` model directly.

## Batch Processing
- `BatchResult` had no `summary()` method. Add it as a dataclass method for CLI convenience.

## Markdown Parsing
- `markdown-it-py`'s `^text^` superscript and `~text~` subscript require `mdit-py-plugins`. Add to core dependencies, not optional, if the feature is part of the default parser.
- Wrap optional dependency imports in `try/except ImportError` and degrade gracefully — this applies to all plugins (diagrams, equations, redis, etc.).

## Build & Packaging
- `pyproject.toml` `dependencies` must list every third-party package unconditionally imported. Audit with: scan `import`/`from` statements across `src/`, skip stdlib, `TYPE_CHECKING`, and `try/except`-guarded imports.
- `mdit-py-plugins` was missing from core deps — superscript/subscript silently failed without it.
- Python 3.10 lacks `tomllib` (stdlib in 3.11+). Use `try/except ImportError` fallback to `tomli` for any `tomllib` import in CLI or library code.

## DOCX Rendering
- `python-docx` `Run.font` has no `superscript`/`subscript` attribute. Use raw XML: `OxmlElement("w:vertAlign")` with `w:val="superscript"` or `w:val="subscript"`.
- `w:vertAlign` element must be appended to `rPr` (run properties) via `run._r.get_or_add_rPr()`.

## Class Methods vs Static Methods
- `@staticmethod` prevents Python from auto-binding `self` — the first parameter receives whatever is passed explicitly, not the instance. If a method needs to call `self.other_method()`, it must be a regular instance method (no `@staticmethod`), not a static method with `self` as a parameter name.
- When refactoring a `@staticmethod` to call other instance methods, always remove `@staticmethod` — otherwise `TypeError: missing 1 required positional argument` occurs because the instance isn't bound.

## Git
- Do not commit or push unless explicitly asked. Stage only intended files; never commit secrets.
- On Windows, `*.md` globs in PowerShell get expanded by the shell — quote them or use the default pattern.
