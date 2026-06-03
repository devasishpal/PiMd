# Asset Management Guide

PiMD provides a comprehensive asset management system for handling images, diagrams, fonts, and other document resources.

## Asset Cache

The `AssetCache` provides SHA256-based content-addressable storage:

```python
from pimd.attachments import AssetCache

cache = AssetCache()
sha = cache.store("logo.png")
cached_path = cache.get(sha)
assert cache.contains(sha)
```

### Features

- **Deduplication**: Identical files produce the same SHA256 hash
- **Shard-based layout**: Files stored as `cache_dir/{first_2_hex}/{full_hash}`
- **In-memory and filesystem**: Cache backends available for both

## Attachment Processing

PiMD automatically resolves, copies, and embeds attachments:

```python
from pimd.attachments import AttachmentConfig, process_attachments

config = AttachmentConfig(
    copy_to_output=True,
    embed_in_docx=True,
    max_image_width=600,
    svg_to_png=True,
    missing_file_action="warn",
    max_file_size=50 * 1024 * 1024,
)
```

### Supported Attachment Types

| Type | Extensions | Handling |
|------|-----------|----------|
| IMAGE | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp` | Embedded in DOCX |
| SVG | `.svg` | Rendered to PNG if `svg_to_png=True` |
| PDF | `.pdf` | Copied to output directory |
| FONT | `.ttf`, `.otf`, `.woff`, `.woff2` | Embedded in DOCX |
| STYLESHEET | `.css` | Applied to HTML output |
| SCRIPT | `.js` | Applied to HTML output |

## Caching Strategy

1. **Diagram Cache**: SHA256 of source code + language for rendered diagram output
2. **Equation Cache**: SHA256 of LaTeX source for OMML/SVG results
3. **Asset Cache**: SHA256 of raw file content for asset deduplication
4. **Conversion Cache**: Generic memory/Redis cache for conversion results

## Error Handling

- Missing assets produce a warning but never halt document generation
- Security path traversal checks block malicious image paths
- Large files exceeding `max_file_size` are skipped with a warning
- SVG-to-PNG conversion failures fall back to embedding raw SVG

## Configuration

```python
from pimd import PiMD
from pimd.safety import SafetyLimits

engine = PiMD(
    limits=SafetyLimits(
        max_text_size=10 * 1024 * 1024,  # 10 MB
        max_file_size=50 * 1024 * 1024,  # 50 MB
        max_nesting_depth=50,
        max_block_count=10000,
        max_image_size=10 * 1024 * 1024,  # 10 MB
    )
)
```
