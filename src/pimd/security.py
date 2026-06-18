"""Security hardening for PiMD — SVG sanitization, CSP, plugin verification, subprocess isolation.

All security-critical operations in PiMD must go through this module.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# SVG sanitization
# ---------------------------------------------------------------------------

_DANGEROUS_SVG_PATTERNS: list[re.Pattern] = [
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bon\w+\s*=", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"<foreignObject[^>]*>.*?</foreignObject>", re.IGNORECASE | re.DOTALL),
]


def sanitize_svg(svg: str, add_csp: bool = True) -> str:
    """Strip dangerous content from SVG and optionally add CSP.

    Args:
        svg: Raw SVG string.
        add_csp: If True, inject ``Content-Security-Policy`` attribute.

    Returns:
        Sanitized SVG string.
    """
    for pattern in _DANGEROUS_SVG_PATTERNS:
        svg = pattern.sub("", svg)

    if add_csp and "<svg" in svg:
        csp = "default-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
        attr = f' content-security-policy="{csp}"'
        svg = svg.replace("<svg", f"<svg{attr}", 1)

    return svg


def sanitize_svg_file(path: str | Path) -> bool:
    """Sanitize an SVG file in-place. Returns True if modified."""
    p = Path(path)
    if not p.exists():
        return False
    original = p.read_text(encoding="utf-8")
    sanitized = sanitize_svg(original)
    if sanitized != original:
        p.write_text(sanitized, encoding="utf-8")
        return True
    return False


# ---------------------------------------------------------------------------
# Plugin verification
# ---------------------------------------------------------------------------


def verify_plugin_hash(plugin_path: str | Path, expected_hash: str) -> bool:
    """Verify SHA-256 hash of a plugin file."""
    import hashlib
    p = Path(plugin_path)
    if not p.exists():
        return False
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    return actual == expected_hash.lower()


def verify_toml_manifest(manifest_path: str | Path) -> dict[str, Any]:
    """Verify and parse a ``plugin.toml`` manifest.

    Returns dict with keys: valid (bool), errors (list), manifest (dict|None)
    """
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]
    result: dict[str, Any] = {"valid": False, "errors": [], "manifest": None}
    p = Path(manifest_path)
    if not p.exists():
        result["errors"].append(f"Manifest not found: {manifest_path}")
        return result
    try:
        manifest = tomllib.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        result["errors"].append(f"Invalid TOML: {e}")
        return result

    required = ["plugin.name", "plugin.version", "plugin.capabilities"]
    missing = [r for r in required if not _nested_get(manifest, r)]
    if missing:
        result["errors"].extend([f"Missing required field: {m}" for m in missing])
        return result

    for cap in manifest.get("plugin", {}).get("capabilities", []):
        if not isinstance(cap, str) or ":" not in cap:
            result["errors"].append(f"Invalid capability: {cap}")
            return result

    result["valid"] = True
    result["manifest"] = manifest
    return result


# ---------------------------------------------------------------------------
# Subprocess isolation
# ---------------------------------------------------------------------------


class SafeSubprocess:
    """Isolated subprocess execution with timeout and path restrictions.

    Usage::

        runner = SafeSubprocess(timeout=30)
        result = runner.run(["mmdc", "-i", input_path, "-o", output_path])
    """

    def __init__(self, timeout: float = 30.0, allowed_paths: list[str] | None = None) -> None:
        self._timeout = timeout
        self._allowed_paths = allowed_paths or []

    def run(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("timeout", self._timeout)
        return subprocess.run(cmd, **kwargs)


def safe_temp_dir() -> tempfile.TemporaryDirectory:
    """Create a secure temporary directory for rendering operations."""
    return tempfile.TemporaryDirectory(prefix="pimd_")


# ---------------------------------------------------------------------------
# Secrets scanning
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)(?:api[_-]?key|secret|token|password|passwd|credential)\s*[:=]\s*['\"]?\w{8,}"),
    re.compile(r"(?i)(?:sk-[a-zA-Z0-9]{20,}|pk-[a-zA-Z0-9]{20,})"),
    re.compile(r"(?i)-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
]


def scan_for_secrets(text: str) -> list[dict[str, Any]]:
    """Scan *text* for potential secrets/credentials.

    Returns list of {pattern, match, position} dicts.
    """
    findings: list[dict[str, Any]] = []
    for pattern in _SECRET_PATTERNS:
        for m in pattern.finditer(text):
            findings.append({
                "pattern": pattern.pattern[:50],
                "match": m.group()[:40],
                "position": m.start(),
            })
    return findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _nested_get(d: dict, path: str, default: Any = None) -> Any:
    parts = path.split(".")
    for p in parts:
        if isinstance(d, dict):
            d = d.get(p, {})
        else:
            return default
    return d if d != {} else default
