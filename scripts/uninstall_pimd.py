"""Uninstall PiMD and optionally remove configuration files.

Usage:
    py scripts/uninstall_pimd.py              # Uninstall only
    py scripts/uninstall_pimd.py --all         # Uninstall + remove config
"""

import subprocess
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".pimd"


def _run_pip_uninstall() -> bool:
    """Run pip uninstall for pimd. Returns True if successful."""
    print("Uninstalling PiMD...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "pimd", "-y"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("  PiMD uninstalled successfully.")
        return True

    if "not installed" in result.stdout.lower():
        print("  PiMD is not installed.")
        return True

    print(f"  Failed to uninstall: {result.stderr.strip()}")
    return False


def _remove_config() -> None:
    """Remove PiMD configuration directory."""
    if CONFIG_DIR.exists():
        import shutil

        shutil.rmtree(CONFIG_DIR, ignore_errors=True)
        print(f"  Removed config directory: {CONFIG_DIR}")
    else:
        print("  No config directory found.")


def main() -> None:
    remove_all = "--all" in sys.argv

    success = _run_pip_uninstall()

    if remove_all and success:
        _remove_config()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
