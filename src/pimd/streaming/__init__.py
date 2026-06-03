"""Streaming and chunk processing for large documents (10MB–100MB+)."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from pimd.models import Block, Document

_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB chunks
_MAX_CHUNK_LINES = 10_000


class LargeFileHandler:
    """Memory-efficient processing of large files via streaming and chunking."""

    def __init__(
        self, chunk_size: int = _CHUNK_SIZE, max_chunk_lines: int = _MAX_CHUNK_LINES
    ) -> None:
        self.chunk_size = chunk_size
        self.max_chunk_lines = max_chunk_lines

    def stream_lines(self, path: str | Path) -> Iterator[str]:
        """Stream lines from a file without loading the whole file."""
        with open(path, encoding="utf-8", errors="replace") as f:
            yield from f

    def stream_chunks(self, path: str | Path) -> Iterator[str]:
        """Stream file in fixed-size byte chunks, yielding decoded text."""
        with open(path, encoding="utf-8", errors="replace") as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk

    def stream_paragraphs(self, path: str | Path) -> Iterator[str]:
        """Stream paragraphs (blank-line separated) without loading the full file."""
        buf: list[str] = []
        for line in self.stream_lines(path):
            stripped = line.rstrip("\n\r")
            if not stripped and buf:
                yield "\n".join(buf)
                buf = []
            elif stripped:
                buf.append(stripped)
        if buf:
            yield "\n".join(buf)

    def count_lines(self, path: str | Path) -> int:
        """Count lines in a file without loading it."""
        count = 0
        for _ in self.stream_lines(path):
            count += 1
        return count

    def estimate_size_mb(self, path: str | Path) -> float:
        """Estimate file size in MB without reading content."""
        return os.path.getsize(path) / (1024 * 1024)


class ChunkProcessor:
    """Process documents in manageable chunks to bound memory usage."""

    def __init__(self, max_blocks_per_chunk: int = 5_000) -> None:
        self.max_blocks_per_chunk = max_blocks_per_chunk

    def split_document(self, doc: Document) -> list[Document]:
        """Split a large document into smaller chunk documents."""
        chunks: list[Document] = []
        current: list[Block] = []
        for block in doc.blocks:
            current.append(block)
            if len(current) >= self.max_blocks_per_chunk:
                chunks.append(Document(blocks=current))
                current = []
        if current:
            chunks.append(Document(blocks=current))
        return chunks

    def merge_documents(self, docs: list[Document]) -> Document:
        """Merge chunk documents back into one."""
        blocks: list[Block] = []
        for doc in docs:
            blocks.extend(doc.blocks)
        return Document(blocks=blocks)


def stream_process(
    input_path: str | Path,
    processor: Callable[[str], Any],
    chunk_size: int = _CHUNK_SIZE,
) -> Iterator[Any]:
    """Stream a file through a processing function in chunks."""
    with open(input_path, encoding="utf-8", errors="replace") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield processor(chunk)


def fast_file_hash(path: str | Path) -> str:
    """Compute SHA-256 hash of a file without loading it entirely."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def is_large_file(path: str | Path, threshold_mb: int = 10) -> bool:
    """Check if a file exceeds the large-file threshold."""
    return os.path.getsize(path) > threshold_mb * 1024 * 1024


__all__ = [
    "LargeFileHandler",
    "ChunkProcessor",
    "stream_process",
    "fast_file_hash",
    "is_large_file",
    "StreamingMarkdownReader",
]


class StreamingMarkdownReader:
    """Stream a Markdown file paragraph-by-paragraph for incremental conversion."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._handler = LargeFileHandler()

    def __iter__(self) -> Iterator[str]:
        return self._handler.stream_paragraphs(self.path)

    def __len__(self) -> int:
        return self._handler.count_lines(self.path)

    @property
    def size_mb(self) -> float:
        return self._handler.estimate_size_mb(self.path)
