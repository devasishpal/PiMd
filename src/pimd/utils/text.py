"""Text sanitization utilities for XML/DOCX output."""

from __future__ import annotations

import re

# Pattern matching all XML 1.0 invalid characters (except tab, CR, LF)
_INVALID_XML_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\uFFFE\uFFFF]")


def sanitize_text(text: str) -> str:
    """Sanitize text for safe XML/DOCX output.

    Strips XML-invalid control characters and escapes XML special
    characters (``&``, ``<``, ``>``) to their entity equivalents.

    Args:
        text: The input string to sanitize.

    Returns:
        The sanitized string safe for XML text content.
    """
    text = _INVALID_XML_CHARS.sub("", text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text
