"""Clean up temporary and generated artifacts from the PiMD project.

Removes:
    - __pycache__ directories
    - .pytest_cache
    - .mypy_cache
    - .ruff_cache
    - build/
    - dist/
    - temporary files (*.tmp, *.log, test_output.txt)
    - generated test artifacts

Does NOT remove:
    - Source code
    - Test files
    - Configuration files
    - Documentation
"""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DIRS_TO_REMOVE: list[str] = [
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    "*.egg-info",
]

FILES_TO_REMOVE: list[str] = [
    "test_output.txt",
    ".pimd_write_test",
]


def _rmtree(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        print(f"  Removed directory: {path}")


def _remove_file(path: Path) -> None:
    if path.is_file():
        path.unlink()
        print(f"  Removed file: {path}")


def _clean_directory(directory: Path) -> None:
    if not directory.exists():
        return

    for item in directory.iterdir():
        if item.is_dir() and item.name in DIRS_TO_REMOVE:
            _rmtree(item)
        elif item.name.startswith(".") and item.is_dir():
            if item.name in (".pytest_cache", ".mypy_cache", ".ruff_cache"):
                _rmtree(item)

    # Remove __pycache__ recursively
    for pycache in directory.rglob("__pycache__"):
        if pycache.is_dir():
            _rmtree(pycache)

    # Remove .egg-info dirs
    for egg_info in directory.glob("*.egg-info"):
        if egg_info.is_dir():
            _rmtree(egg_info)

    # Remove build/dist
    for name in ("build", "dist"):
        p = directory / name
        if p.is_dir():
            _rmtree(p)

    # Remove files
    for name in FILES_TO_REMOVE:
        f = directory / name
        _remove_file(f)


def main() -> None:
    print("Cleaning PiMD project artifacts...")
    _clean_directory(PROJECT_ROOT)

    # Also clean src/pimd __pycache__
    for pycache in (PROJECT_ROOT / "src" / "pimd").rglob("__pycache__"):
        if pycache.is_dir():
            _rmtree(pycache)

    # Clean tests __pycache__
    for pycache in (PROJECT_ROOT / "tests").rglob("__pycache__"):
        if pycache.is_dir():
            _rmtree(pycache)

    # Clean benchmarks __pycache__
    for pycache in (PROJECT_ROOT / "benchmarks").rglob("__pycache__"):
        if pycache.is_dir():
            _rmtree(pycache)

    print("Done.")


if __name__ == "__main__":
    main()
