"""Fresh install verification script.

Workflow:
    1. Uninstall any existing PiMD installation.
    2. Clear caches.
    3. Build and install PiMD from source.
    4. Run verification checks.
    5. Report success/failure.

Usage:
    py scripts/fresh_install_test.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], desc: str) -> bool:
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED ({result.returncode})")
        if result.stderr:
            for line in result.stderr.strip().split("\n")[-5:]:
                print(f"  stderr: {line}")
        if result.stdout:
            for line in result.stdout.strip().split("\n")[-5:]:
                print(f"  stdout: {line}")
        return False
    print("  OK")
    if result.stdout:
        for line in result.stdout.strip().split("\n")[:3]:
            print(f"  {line}")
    return True


def main() -> None:
    checks: list[tuple[list[str], str]] = [
        (
            [sys.executable, "-m", "pip", "uninstall", "pimd", "-y"],
            "Step 1: Uninstall existing PiMD",
        ),
        (
            [sys.executable, "-m", "pip", "install", "-e", str(PROJECT_ROOT)],
            "Step 2: Install PiMD from source (editable)",
        ),
        (
            [sys.executable, "-m", "pip", "install", str(PROJECT_ROOT)],
            "Step 2b: Re-install PiMD (non-editable)",
        ),
        (
            [sys.executable, "-m", "pimd", "--version"],
            "Step 3: Verify CLI works",
        ),
        (
            [sys.executable, "-m", "pimd", "doctor"],
            "Step 4: Verify 'pimd doctor' command",
        ),
        (
            [sys.executable, "-m", "pimd", "info"],
            "Step 5: Verify 'pimd info' command",
        ),
        (
            [sys.executable, "-c", "from pimd import PiMD; print('PiMD import OK')"],
            "Step 6: Verify Python API import",
        ),
        (
            [sys.executable, "-c",
             "from pimd import PiMD; "
             "engine = PiMD(); "
             "result = engine.md_text_to_docx_bytes('# Hello World'); "
             "print(f'Conversion OK: {len(result)} bytes')"],
            "Step 7: Verify basic conversion works",
        ),
        (
            [sys.executable, "-c",
             "from pimd import PiMD; "
             "engine = PiMD(); "
             "from pimd.api import PiMD; "
             "engine = PiMD(); "
             "result = engine.html_text_to_docx_bytes('<h1>Hello</h1>'); "
             "print(f'HTML conversion OK: {len(result)} bytes')"],
            "Step 8: Verify HTML conversion works",
        ),
    ]

    all_ok = True
    for cmd, desc in checks:
        if not _run(cmd, desc):
            all_ok = False
            break

    print(f"\n{'='*60}")
    if all_ok:
        print("  FRESH INSTALL VERIFICATION: PASSED")
        print("  PiMD is ready for use.")
    else:
        print("  FRESH INSTALL VERIFICATION: FAILED")
        print("  Review the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
