"""Reusable content blocks — includes, shared sections, disclaimers, and references."""

from pimd.blocks.manager import (
    BlockLibrary,
    BlockManager,
    BlockReference,
    ContentBlock,
    IncludeSyntax,
    parse_includes,
    resolve_blocks,
)

__all__ = [
    "ContentBlock",
    "BlockReference",
    "BlockLibrary",
    "BlockManager",
    "IncludeSyntax",
    "parse_includes",
    "resolve_blocks",
]
