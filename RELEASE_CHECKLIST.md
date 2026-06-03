# PiMD v1.0.0 Release Checklist

> Every item must be validated before release.

## Pre-Release

- [x] Version bumped to 1.0.0 (`__init__.py`, `pyproject.toml`)
- [x] Author metadata updated
- [x] Trove classifiers set to "Production/Stable"
- [x] All dependencies listed in `pyproject.toml` are required (no unused)
- [x] Optional dependency groups documented (dev, diagrams, equations, export, citations, redis, profiling)

## Code Quality

- [x] Ruff lint: 0 errors (36 E501 line-too-long warnings — all intentional regex/strings)
- [x] No F401 (unused import) errors
- [x] No F841 (unused variable) errors
- [x] No UP035 (deprecated typing) errors
- [x] No N806/N815 naming violations in production code (suppressed where intentional)
- [x] No bare `except:` clauses without re-raise or logging
- [x] All modules have `__all__` exports

## Testing

- [x] **548 unit/integration tests pass** (1 skipped: Redis unavailable)
- [x] `test_parallel_conversion` passes (thread-safety verified)
- [x] Large document stress tests pass
- [x] CLI tests pass
- [x] Frontmatter tests pass (YAML, TOML, JSON)
- [x] Ecosystem tests pass (GFM, GitLab, MkDocs, Sphinx, Docusaurus, Obsidian)
- [x] GitHub features tests pass (task lists, tables, alerts, footnotes, anchors)
- [x] Engine features tests pass (callouts, footnotes, attachments)
- [x] Theme tests pass
- [x] Performance benchmarks run without errors

## Security

- [x] Path traversal protection in image rendering (`SafetyGuard.check_path_traversal`)
- [x] Input size limits enforced (100 MB text, 500 MB file)
- [x] File size limits enforced
- [x] Block count limits enforced
- [x] URL scheme validation
- [x] Null byte detection
- [x] Control character detection
- [x] Blocked system paths (/etc, /proc, /sys, C:\\Windows)

## Packaging

- [x] `pyproject.toml` complete and valid
- [x] Build system: hatchling
- [x] Wheel builds successfully
- [x] Source distribution builds successfully
- [x] CLI entry point `pimd = "pimd.cli.app:main"` works
- [x] Package metadata complete (name, version, description, authors, license)
- [x] README included in package
- [x] LICENSE included in package

## Installation Verification

- [x] `pip install .` works
- [x] `pip install wheel` works
- [x] `pimd --version` prints `PiMD v1.0.0`
- [x] `pimd doctor` runs without errors
- [x] Python API import works: `from pimd import PiMD`
- [x] Basic conversion works: `md_text_to_docx_bytes("# Hello")`
- [x] HTML conversion works: `html_text_to_docx_bytes("<h1>Hello</h1>")`
- [x] Fresh install from clean state verified

## Documentation

- [x] README.md contains feature table and quick-start
- [x] Compatibility Guide (docs/compatibility-guide.md)
- [x] Repository Guide (docs/repository-guide.md)
- [x] Migration Guide (docs/migration-guide.md)
- [x] Performance Guide (docs/performance-guide.md)
- [x] Large File Guide (docs/large-file-guide.md)
- [x] Redis Guide (docs/redis-guide.md)
- [x] Scaling Guide (docs/scaling-guide.md)

## Scripts

- [x] `scripts/clean.py` — removes build artifacts
- [x] `scripts/uninstall_pimd.py` — clean uninstall
- [x] `scripts/fresh_install_test.py` — end-to-end install verification

## Release

- [ ] Create git tag `v1.0.0`
- [ ] Build wheel: `py -m build --wheel`
- [ ] Build sdist: `py -m build --sdist`
- [ ] Verify wheel contents: `py -m wheel unpack dist/pimd-1.0.0-py3-none-any.whl`
- [ ] Upload to PyPI: `py -m twine upload dist/*`
- [ ] Create GitHub release with release notes
- [ ] Update documentation URLs if needed

## Post-Release

- [ ] Monitor for issues
- [ ] Verify docs site updates
- [ ] Announce release

---

*Generated: June 2026*
*PiMD v1.0.0*
