"""Accessibility engine — validate documents for accessibility compliance."""

from pimd.accessibility.engine import (
    AccessibilityEngine,
    AccessibilityIssue,
    AccessibilityReport,
    HeadingHierarchyIssue,
    ImageAltIssue,
    ReadingOrderIssue,
    StructureIssue,
    TableAccessibilityIssue,
)

__all__ = [
    "AccessibilityEngine",
    "AccessibilityReport",
    "AccessibilityIssue",
    "HeadingHierarchyIssue",
    "ImageAltIssue",
    "ReadingOrderIssue",
    "TableAccessibilityIssue",
    "StructureIssue",
]
