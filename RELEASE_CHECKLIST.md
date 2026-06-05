# PiMD Release Checklist

> Release is fully automated via `.github/workflows/release.yml` — just push a `v*` tag.

## Automated (no manual steps)

| Step | Handled by |
|------|------------|
| Build sdist + wheel | `release.yml` — `python -m build` |
| Upload to PyPI | `pypa/gh-action-pypi-publish` with `PYPI_API_TOKEN` secret |
| Create GitHub Release | `softprops/action-gh-release` with changelog from `CHANGELOG.md` |
| Attach build artifacts | `release.yml` — attaches `dist/*.whl` and `dist/*.tar.gz` to release |

## Pre-release checks (manual)

- [ ] Version bumped in `src/pimd/__init__.py` and `pyproject.toml`
- [ ] `CHANGELOG.md` updated with new version section
- [ ] Ruff lint passes: `ruff check src/ tests/ benchmarks/`
- [ ] Full test suite passes: `pytest tests/ -v`
- [ ] README.md badges and version references updated
- [ ] New features documented in README.md (CLI examples, Python API)
- [ ] Optional: run benchmarks via `python benchmarks/run_all.py`

## Trigger release

```bash
git tag -a v<version> -m "v<version>: <short description>"
git push origin v<version>
```

The workflow will build, publish to PyPI, and create a GitHub Release automatically.

## Post-release

- [ ] Verify PyPI page: https://pypi.org/project/pimd/
- [ ] Verify GitHub Release: https://github.com/devasishpal/PiMd/releases
- [ ] Confirm CI shows all green checks
