"""Custom exceptions used throughout the PiMD framework."""


class PiMDError(Exception):
    """Base exception for all PiMD errors."""


class ConversionError(PiMDError):
    """Raised when a document conversion operation fails."""


class ParserError(PiMDError):
    """Raised when parsing of input content (Markdown, HTML) fails."""


class RendererError(PiMDError):
    """Raised when rendering output content (DOCX) fails."""
