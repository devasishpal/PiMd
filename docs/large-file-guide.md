# PiMD Large File Guide

## Overview

PiMD can process Markdown files from 10 MB to 100 MB and beyond. This guide explains the streaming architecture, chunk processing, and memory management techniques.

## Streaming Architecture

Large files are never loaded entirely into memory. Instead, PiMD uses:

1. **Line streaming**: Read one line at a time
2. **Chunk streaming**: Read in 4 MB blocks
3. **Paragraph streaming**: Read paragraph by paragraph (blank-line delimited)

```python
from pimd.streaming import LargeFileHandler

handler = LargeFileHandler()

# Count lines without loading
count = handler.count_lines("100mb-document.md")
print(f"{count} lines")

# Stream paragraphs for incremental conversion
for paragraph in handler.stream_paragraphs("large-doc.md"):
    process_paragraph(paragraph)
```

## Chunk Processing

For documents that have already been parsed, use `ChunkProcessor` to split and merge:

```python
from pimd.streaming import ChunkProcessor
from pimd.models import Document

processor = ChunkProcessor(max_blocks_per_chunk=5000)
chunks = processor.split_document(large_doc)

for chunk in chunks:
    render_chunk(chunk)  # process each chunk independently

# Recombine if needed
full_doc = processor.merge_documents(chunks)
```

## Detecting Large Files

```python
from pimd.streaming import is_large_file, fast_file_hash

if is_large_file("report.md", threshold_mb=10):
    print("Large file detected — using streaming")
    hash_val = fast_file_hash("report.md")
    print(f"SHA-256: {hash_val}")
```

## Memory-Efficient Conversion

```python
from pimd.streaming import StreamingMarkdownReader

reader = StreamingMarkdownReader("large-book.md")
print(f"File size: {reader.size_mb:.1f} MB")
print(f"Line count: {len(reader)}")

for paragraph in reader:
    # Process one paragraph at a time
    result = convert_paragraph(paragraph)
```

## Safety Limits for Large Files

Configure limits to match your workload:

```python
from pimd.safety import SafetyLimits, SafetyGuard

limits = SafetyLimits(
    max_input_size=500 * 1024 * 1024,    # 500 MB text
    max_file_size=1024 * 1024 * 1024,    # 1 GB files
    max_document_blocks=500_000,         # 500K blocks
    max_nesting_depth=500,
)

guard = SafetyGuard(limits)
guard.check_file_size("massive-doc.md")
```

## Parallel Processing for Large Files

Combine streaming with parallel execution:

```python
from pimd.parallel import parallel_map
from pimd.streaming import LargeFileHandler

handler = LargeFileHandler()
chunks = list(handler.stream_chunks("large-doc.md"))

results = parallel_map(convert_chunk, chunks, max_workers=4)
```

## Recommended Workflow for 100 MB+ Files

1. **Check file size** with `is_large_file()`
2. **Hash** with `fast_file_hash()` for change detection
3. **Stream paragraphs** with `LargeFileHandler.stream_paragraphs()`
4. **Process in chunks** with `ChunkProcessor`
5. **Render incrementally** or merge output chunks

```python
from pimd.streaming import LargeFileHandler, ChunkProcessor
from pimd.parallel import parallel_batch
from pimd.converters.markdown import MarkdownConverter

def process_paragraph(text):
    converter = MarkdownConverter()
    return converter.convert_text(text)

handler = LargeFileHandler()
paragraphs = list(handler.stream_paragraphs("100mb-doc.md"))
summary = parallel_batch(process_paragraph, paragraphs, max_workers=8)
print(f"Processed {summary.succeeded} paragraphs in {summary.duration:.1f}s")
```
