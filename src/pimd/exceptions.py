"""Custom exceptions used throughout the PiMD framework."""


class PiMDError(Exception):
    """Base exception for all PiMD errors."""


class ConversionError(PiMDError):
    """Raised when a document conversion operation fails."""


class ParserError(PiMDError):
    """Raised when parsing of input content (Markdown, HTML) fails."""


class RendererError(PiMDError):
    """Raised when rendering output content (DOCX) fails."""


class DiagramError(PiMDError):
    """Raised when diagram rendering fails (internal, not user-facing)."""


class PluginError(PiMDError):
    """Raised by plugin system during registration, dispatch, or lifecycle."""


class ConfigError(PiMDError):
    """Raised for invalid configuration."""


class SecurityError(PiMDError):
    """Raised when a security check fails."""


class CacheError(PiMDError):
    """Raised on cache backend failures."""
