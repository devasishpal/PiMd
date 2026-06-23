"""Template engine for reusable document templates."""

from pimd.templates.docx_reference import ReferenceDoc, ReferenceDocError, validate_reference_doc
from pimd.templates.manager import TemplateManager
from pimd.templates.models import (
    Template,
    TemplateConfig,
    TemplateMetadata,
    TemplateType,
)
from pimd.templates.style_mapper import DEFAULT_STYLE_MAP, StyleMapper, get_available_styles

__all__ = [
    "TemplateManager",
    "Template",
    "TemplateConfig",
    "TemplateMetadata",
    "TemplateType",
    "ReferenceDoc",
    "ReferenceDocError",
    "validate_reference_doc",
    "StyleMapper",
    "DEFAULT_STYLE_MAP",
    "get_available_styles",
]
