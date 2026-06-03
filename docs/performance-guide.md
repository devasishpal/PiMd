# PiMD Performance Guide

## Overview

PiMD is designed for high-performance document conversion at scale. This guide covers optimization strategies, benchmarking, and tuning.

## Key Performance Features

- **Streaming architecture**: Process files larger than available RAM
- **Parallel processing**: Thread and process pool executors
- **Incremental builds**: Skip unchanged files using hash tracking
- **Caching**: Memory and optional Redis caching for diagrams, equations, and conversions
- **Pipeline profiling**: Built-in timing and memory profiling

## Measuring Performance

### Quick benchmark

```bash
python -m pytest benchmarks/ -v -s
```

### Profiling a conversion

```python
from pimd.profiling import profile_conversion, Profiler
from pimd import PiMD

engine = PiMD()
result, report = profile_conversion(engine.md_text_to_docx_bytes, large_content)
print(report.summary())
```

## Optimization Tips

### 1. Use Parallel Processing

```python
from pimd.parallel import parallel_batch
from pimd.converters.markdown import MarkdownConverter

converter = MarkdownConverter()
docs = [f"# Doc {i}" for i in range(100)]
summary = parallel_batch(converter.convert_text, docs, max_workers=8)
print(f"Converted {summary.succeeded}/{summary.total} in {summary.duration:.1f}s")
```

### 2. Enable Incremental Builds

```python
from pimd.incremental import IncrementalBuildTracker

tracker = IncrementalBuildTracker(".pimd-build-state.json")
if tracker.needs_rebuild("chapter1.md"):
    # convert...
    tracker.record_build("chapter1.md")
```

### 3. Use the Pipeline for Complex Workflows

```python
from pimd.pipeline import PipelineManager

pm = PipelineManager()
pipeline = PipelineManager.default_md_pipeline()
pipeline.add_stage(ExportStage("export_pdf", target_format="pdf"))
pm.register("my-pipeline", pipeline)
```

### 4. Configure Caching

```python
from pimd.equations import EquationEngine, EquationConfig
from pimd.caching.redis_cache import RedisEquationCache

# Redis cache (optional, fallback to memory)
cache = RedisEquationCache(url="redis://localhost:6379/0")
engine = EquationEngine(cache=cache)
```

## Pipeline Profiling

Each pipeline stage is profiled automatically:

```python
from pimd.pipeline import Pipeline, PipelineContext

p = Pipeline("profiled")
# ... add stages ...
ctx, results = p.run(PipelineContext(source_text="# Hello"))
for r in results:
    print(f"  {r.stage_name}: {r.duration*1000:.1f}ms {'OK' if r.success else 'FAIL'}")
```

## Memory Management

- Use `ChunkProcessor.split_document()` for very large documents
- Use `LargeFileHandler.stream_lines()` for streaming input
- Monitor with `Profiler` and `MemorySnapshot`

## Recommended Configuration for Large Files

```python
from pimd.safety import SafetyLimits

limits = SafetyLimits(
    max_input_size=500 * 1024 * 1024,   # 500 MB
    max_file_size=1024 * 1024 * 1024,    # 1 GB
    max_nesting_depth=500,
    max_document_blocks=500_000,
)
```
