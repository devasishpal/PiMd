# PiMD Scaling Guide

## Overview

PiMD scales from single-document conversion on a laptop to processing entire documentation repositories on production servers.

## Scaling Dimensions

| Dimension | Strategy | Module |
|-----------|----------|--------|
| File size | Streaming, chunking | `streaming/` |
| File count | Parallel batch processing | `parallel/` |
| Repository size | Incremental builds, project conversion | `incremental/`, `project/` |
| Rendering | Pipeline engine with custom stages | `pipeline/` |
| Cache | Memory → Redis | `caching/redis_cache.py` |

## Architecture for Large-Scale Deployment

```
Input Files
    │
    ▼
┌─────────────────┐
│  SafetyGuard     │  ← Path traversal, size, nesting checks
└────────┬────────┘
         ▼
┌─────────────────┐
│  Pipeline        │  ← Configurable stages
│  ┌───────────┐  │
│  │ Parse     │  │
│  ├───────────┤  │
│  │ Transform │  │  ← Diagrams, equations (parallel)
│  ├───────────┤  │
│  │ Render    │  │
│  ├───────────┤  │
│  │ Export    │  │
│  └───────────┘  │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Job System      │  ← Background processing
└────────┬────────┘
         ▼
    Output Files
```

## Handling Large Repositories

### Project Conversion

```bash
# Convert an entire documentation directory
pimd project docs/ --output build/ --format docx

# Merge all files into a single document
pimd project docs/ --output build/ --merge

# Parallel batch conversion
pimd project docs/ --output build/ --parallel --workers 8
```

### Programmatic Project Conversion

```python
from pimd.project import ProjectConverter

pc = ProjectConverter(incremental=True)
result = pc.convert_project(
    "docs/",
    "build/",
    merge=False,
    output_format="docx",
)
print(f"Converted: {result.converted}, Skipped: {result.skipped}, Failed: {result.failed}")
```

## Redis for Distributed Caching

For high-traffic or CI environments, use Redis to share caches across processes:

```bash
export PIMD_REDIS_URL="redis://redis-server:6379/0"
```

```python
from pimd.caching.redis_cache import RedisEquationCache, RedisDiagramCache

# Cache equations across builds
eq_cache = RedisEquationCache(url="redis://redis-server:6379/0")

# Cache diagrams across builds
diagram_cache = RedisDiagramCache(url="redis://redis-server:6379/0")
```

## Pipeline Customization

Create custom pipelines for different workflows:

```python
from pimd.pipeline import (
    Pipeline, ParseStage, TransformStage,
    RenderStage, ExportStage, PostProcessStage,
    PipelineManager,
)

pdf_pipeline = Pipeline("pdf")
pdf_pipeline.add_stage(ParseStage("parse"))
pdf_pipeline.add_stage(TransformStage("diagrams"))
pdf_pipeline.add_stage(RenderStage("render", output_format="docx"))
pdf_pipeline.add_stage(ExportStage("export", target_format="pdf"))

PipelineManager().register("pdf-production", pdf_pipeline)
```

## Job System for Background Processing

```python
from pimd.jobs import JobManager

jm = JobManager()
job_id = jm.create_job(
    source_path="large-doc.md",
    output_path="output.pdf",
    options={"format": "md"},
)
result = jm.run_job(job_id)
print(f"Job {job_id}: {result.status} in {result.duration:.1f}s")
```

## Performance Targets

| Workload | Target | Configuration |
|----------|--------|---------------|
| 10 MB Markdown | < 30s | Default |
| 50 MB Markdown | < 120s | 8 workers |
| 100 MB Markdown | < 300s | 16 workers, streaming |
| 1000 files | < 60s | 8 workers, incremental |
