"""Branding system — logos, corporate colors, metadata, and visual identity."""

from pimd.branding.manager import BrandingManager
from pimd.branding.models import Brand, BrandConfig, BrandMetadata

__all__ = [
    "BrandingManager",
    "Brand",
    "BrandConfig",
    "BrandMetadata",
]
