"""Reusable content blocks — includes, shared sections, disclaimers.

Syntax::

    {{include:path/to/file.md}}

    {{include:legal/disclaimer.md}}

    {{block:my-block-name}}
    Content goes here...
    {{/block}}

    {{use:my-block-name}}

Block libraries are directories of reusable Markdown files.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_INCLUDE_PATTERN = re.compile(r"\{\{include:([^}]+)\}\}")
_BLOCK_DEF_PATTERN = re.compile(
    r"\{\{block:(\w[\w-]*)\}\}\s*(.*?)\s*\{\{/block\}\}", re.DOTALL
)
_BLOCK_USE_PATTERN = re.compile(r"\{\{use:([^}]+)\}\}")


@dataclass
class IncludeSyntax:
    raw: str
    target: str
    line: int = 0
    resolved: bool = False
    content: str = ""
    error: str | None = None


@dataclass
class ContentBlock:
    name: str
    content: str
    source_file: str | None = None
    tags: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class BlockReference:
    name: str
    resolved: bool = False
    block: ContentBlock | None = None
    error: str | None = None


class BlockLibrary:
    """A named collection of reusable content blocks."""

    def __init__(self, name: str = "default", directory: str | Path | None = None) -> None:
        self.name = name
        self._blocks: dict[str, ContentBlock] = {}
        self._directory = Path(directory) if directory else None
        if self._directory and self._directory.is_dir():
            self.load_from_directory(self._directory)

    def add(self, block: ContentBlock) -> None:
        self._blocks[block.name] = block

    def get(self, name: str) -> ContentBlock | None:
        return self._blocks.get(name)

    def remove(self, name: str) -> bool:
        return self._blocks.pop(name, None) is not None

    def list(self) -> list[ContentBlock]:
        return list(self._blocks.values())

    def load_from_directory(self, directory: Path) -> int:
        count = 0
        for md_file in sorted(directory.rglob("*.md")):
            name = md_file.stem
            content = md_file.read_text(encoding="utf-8")
            self._blocks[name] = ContentBlock(
                name=name, content=content, source_file=str(md_file)
            )
            count += 1
        return count

    def clear(self) -> None:
        self._blocks.clear()

    def __contains__(self, name: str) -> bool:
        return name in self._blocks

    def __len__(self) -> int:
        return len(self._blocks)


class BlockManager:
    """Central registry for reusable content blocks across libraries."""

    def __init__(self) -> None:
        self._libraries: dict[str, BlockLibrary] = {}

    def add_library(self, library: BlockLibrary) -> None:
        self._libraries[library.name] = library

    def remove_library(self, name: str) -> bool:
        return self._libraries.pop(name, None) is not None

    def get_library(self, name: str) -> BlockLibrary | None:
        return self._libraries.get(name)

    def get(self, name: str) -> ContentBlock | None:
        for lib in self._libraries.values():
            block = lib.get(name)
            if block is not None:
                return block
        return None

    def add_block(self, block: ContentBlock, library_name: str = "default") -> None:
        if library_name not in self._libraries:
            self._libraries[library_name] = BlockLibrary(name=library_name)
        self._libraries[library_name].add(block)

    def list_blocks(self) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        for lib in self._libraries.values():
            blocks.extend(lib.list())
        return blocks

    def list_libraries(self) -> list[str]:
        return list(self._libraries.keys())

    def resolve_refs(self, text: str) -> str:
        return resolve_blocks(text, self)


def parse_includes(text: str) -> list[IncludeSyntax]:
    includes: list[IncludeSyntax] = []
    for match in _INCLUDE_PATTERN.finditer(text):
        includes.append(
            IncludeSyntax(
                raw=match.group(0),
                target=match.group(1).strip(),
            )
        )
    return includes


def resolve_blocks(text: str, manager: BlockManager) -> str:
    result = text

    for include in _INCLUDE_PATTERN.finditer(text):
        target = include.group(1).strip()
        block = manager.get(target)
        if block is not None:
            result = result.replace(include.group(0), block.content, 1)
        else:
            fp = Path(target)
            if fp.is_file():
                result = result.replace(include.group(0), fp.read_text(encoding="utf-8"), 1)

    for use in _BLOCK_USE_PATTERN.finditer(text):
        name = use.group(1).strip()
        block = manager.get(name)
        if block is not None:
            result = result.replace(use.group(0), block.content, 1)

    return result


def extract_block_definitions(text: str) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []
    for match in _BLOCK_DEF_PATTERN.finditer(text):
        name = match.group(1)
        content = match.group(2).strip()
        blocks.append(ContentBlock(name=name, content=content))
    return blocks


def strip_block_definitions(text: str) -> str:
    return _BLOCK_DEF_PATTERN.sub("", text).strip()
