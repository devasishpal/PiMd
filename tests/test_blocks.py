"""Tests for reusable content blocks."""

from pathlib import Path

from pimd.blocks.manager import (
    BlockLibrary,
    BlockManager,
    ContentBlock,
    extract_block_definitions,
    parse_includes,
    resolve_blocks,
    strip_block_definitions,
)


class TestParseIncludes:
    def test_no_includes(self) -> None:
        result = parse_includes("Plain text without includes")
        assert result == []

    def test_single_include(self) -> None:
        result = parse_includes("Before {{include:legal.md}} After")
        assert len(result) == 1
        assert result[0].target == "legal.md"
        assert result[0].raw == "{{include:legal.md}}"

    def test_multiple_includes(self) -> None:
        result = parse_includes("{{include:a.md}} {{include:b.md}} {{include:c.md}}")
        assert len(result) == 3

    def test_include_with_spaces(self) -> None:
        result = parse_includes("{{include: path/to/file.md }}")
        assert len(result) == 1
        assert result[0].target == "path/to/file.md"


class TestBlockLibrary:
    def test_add_and_get(self) -> None:
        lib = BlockLibrary("test")
        block = ContentBlock(name="disclaimer", content="This is confidential")
        lib.add(block)
        assert lib.get("disclaimer") is not None
        assert lib.get("disclaimer").content == "This is confidential"

    def test_get_nonexistent(self) -> None:
        lib = BlockLibrary("test")
        assert lib.get("nonexistent") is None

    def test_remove(self) -> None:
        lib = BlockLibrary("test")
        lib.add(ContentBlock(name="test", content="hello"))
        assert lib.remove("test")
        assert not lib.remove("nonexistent")

    def test_list(self) -> None:
        lib = BlockLibrary("test")
        lib.add(ContentBlock(name="a", content="1"))
        lib.add(ContentBlock(name="b", content="2"))
        assert len(lib.list()) == 2

    def test_contains(self) -> None:
        lib = BlockLibrary("test")
        lib.add(ContentBlock(name="present", content="yes"))
        assert "present" in lib
        assert "missing" not in lib

    def test_len(self) -> None:
        lib = BlockLibrary("test")
        assert len(lib) == 0
        lib.add(ContentBlock(name="x", content="y"))
        assert len(lib) == 1


class TestBlockManager:
    def test_add_library(self) -> None:
        mgr = BlockManager()
        lib = BlockLibrary("legal")
        lib.add(ContentBlock(name="disclaimer", content="Legal disclaimer"))
        mgr.add_library(lib)
        assert mgr.get_library("legal") is lib

    def test_get_block_across_libraries(self) -> None:
        mgr = BlockManager()
        lib1 = BlockLibrary("lib1")
        lib1.add(ContentBlock(name="shared", content="From lib1"))
        mgr.add_library(lib1)
        block = mgr.get("shared")
        assert block is not None
        assert block.content == "From lib1"

    def test_list_blocks(self) -> None:
        mgr = BlockManager()
        mgr.add_block(ContentBlock(name="a", content="1"))
        mgr.add_block(ContentBlock(name="b", content="2"))
        assert len(mgr.list_blocks()) == 2

    def test_remove_library(self) -> None:
        mgr = BlockManager()
        mgr.add_library(BlockLibrary("test"))
        assert mgr.remove_library("test")
        assert not mgr.remove_library("nonexistent")


class TestExtractDefinitions:
    def test_no_definitions(self) -> None:
        blocks = extract_block_definitions("Plain text")
        assert blocks == []

    def test_single_definition(self) -> None:
        text = "{{block:my-block}}\nContent here\n{{/block}}"
        blocks = extract_block_definitions(text)
        assert len(blocks) == 1
        assert blocks[0].name == "my-block"
        assert "Content here" in blocks[0].content

    def test_multiple_definitions(self) -> None:
        text = "{{block:a}}A{{/block}} {{block:b}}B{{/block}}"
        blocks = extract_block_definitions(text)
        assert len(blocks) == 2

    def test_strip_definitions(self) -> None:
        text = "Before {{block:test}}Inside{{/block}} After"
        stripped = strip_block_definitions(text)
        assert "{{block:test}}" not in stripped
        assert "Before" in stripped
        assert "After" in stripped


class TestResolveBlocks:
    def test_resolve_with_manager(self) -> None:
        mgr = BlockManager()
        mgr.add_block(ContentBlock(name="header", content="# Header Content"))
        result = resolve_blocks("{{use:header}}", mgr)
        assert "# Header Content" in result

    def test_resolve_include_from_file(self, tmp_path: Path) -> None:
        mgr = BlockManager()
        include_file = tmp_path / "include.md"
        include_file.write_text("Included content", encoding="utf-8")
        result = resolve_blocks("{{include:" + str(include_file) + "}}", mgr)
        assert "Included content" in result
