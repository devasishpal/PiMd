"""Style mapping — map Markdown elements to DOCX style names.

Provides a default mapping, merges with user overrides, and safely
resolves style names with graceful fallback.
"""

from __future__ import annotations

from typing import Any

# Default mapping of Markdown elements to DOCX style names.
# These are the standard Word styles that most templates include.
DEFAULT_STYLE_MAP: dict[str, str] = {
    "h1": "Heading 1",
    "h2": "Heading 2",
    "h3": "Heading 3",
    "h4": "Heading 4",
    "h5": "Heading 5",
    "h6": "Heading 6",
    "paragraph": "Normal",
    "blockquote": "Blockquote",
    "code": "Code Block",
    "table": "Table Grid",
    "caption": "Caption",
    "title": "Title",
    "subtitle": "Subtitle",
}

# Elements whose style maps to "Normal" by default
_NORMAL_ALIASES = {"paragraph", "list_item", "footnote", "caption"}


def get_available_styles(doc: Any) -> list[str]:
    """Return all available style names from a python-docx Document.

    Parameters
    ----------
    doc : docx.Document
        An opened python-docx document.

    Returns
    -------
    list[str]
        Sorted list of style names.
    """
    try:
        return sorted([s.name for s in doc.styles if s.name is not None])
    except Exception:
        return []


def style_exists(doc: Any, style_name: str) -> bool:
    """Check if a named style exists in the document.

    Parameters
    ----------
    doc : docx.Document
        An opened python-docx document.
    style_name : str
        The style name to check.

    Returns
    -------
    bool
        ``True`` if the style exists.
    """
    try:
        _ = doc.styles[style_name]
        return True
    except (KeyError, AttributeError):
        return False


class StyleMapper:
    """Map Markdown element types to DOCX style names with safe fallback.

    Parameters
    ----------
    overrides : dict[str, str] | None, optional
        Custom mappings that override the defaults (e.g.
        ``{"h1": "CorporateHeading1"}``).
    doc : Any, optional
        A python-docx ``Document`` to validate styles against.
        If provided, missing styles will be silently ignored.
    """

    def __init__(
        self,
        overrides: dict[str, str] | None = None,
        doc: Any = None,
    ) -> None:
        self._map: dict[str, str] = dict(DEFAULT_STYLE_MAP)
        if overrides:
            self._map.update(overrides)
        self._doc = doc
        self._cache: dict[str, str | None] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, element: str) -> str | None:
        """Return the DOCX style name for a Markdown element.

        Checks the style exists in the document if one was provided.
        Falls back to ``None`` if the style cannot be found.

        Parameters
        ----------
        element : str
            The Markdown element name (e.g. ``"h1"``, ``"paragraph"``).

        Returns
        -------
        str or None
            The resolved style name, or ``None`` for safe fallback.
        """
        if element in self._cache:
            return self._cache[element]

        style_name = self._map.get(element)
        if style_name is None:
            self._cache[element] = None
            return None

        if self._doc is not None and not style_exists(self._doc, style_name):
            self._cache[element] = None
            return None

        self._cache[element] = style_name
        return style_name

    def get_with_fallback(self, element: str, default: str = "Normal") -> str:
        """Like :meth:`get`, but returns *default* instead of ``None``.

        Parameters
        ----------
        element : str
            The Markdown element name.
        default : str, optional
            Fallback style name (default ``"Normal"``).

        Returns
        -------
        str
            A style name that is guaranteed to exist (or the default).
        """
        result = self.get(element)
        return result if result is not None else default

    def heading_level(self, level: int) -> str | None:
        """Return the style for a heading level.

        Parameters
        ----------
        level : int
            Heading level (1-6).

        Returns
        -------
        str or None
            The style name, or ``None``.
        """
        return self.get(f"h{min(max(level, 1), 6)}")

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    @property
    def mapping(self) -> dict[str, str]:
        """Return the full effective mapping."""
        return dict(self._map)

    def __repr__(self) -> str:
        return f"StyleMapper({len(self._map)} mappings)"

    def clear_cache(self) -> None:
        """Clear the internal style-existence cache."""
        self._cache.clear()
