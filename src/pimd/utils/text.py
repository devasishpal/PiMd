"""Text sanitization utilities for XML/DOCX output."""

from __future__ import annotations

import re

# Pattern matching all XML 1.0 invalid characters (except tab, CR, LF)
_INVALID_XML_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\uFFFE\uFFFF]")


def sanitize_text(text: str) -> str:
    """Strip XML-invalid control characters from text.

    Removes characters that are not valid in XML 1.0 documents,
    such as null bytes, form feeds, and other control characters
    (except tab ``\\t``, carriage return ``\\r``, and newline ``\\n``).

    Args:
        text: The input string to sanitize.

    Returns:
        The sanitized string with invalid characters removed.
    """
    return _INVALID_XML_CHARS.sub("", text)
