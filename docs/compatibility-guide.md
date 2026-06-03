# PiMD Compatibility Guide

PiMD automatically detects and normalizes content from the widest range of documentation ecosystems.

## Supported Flavors

| Flavor | File Extensions | Detection Method |
|--------|----------------|------------------|
| GitHub Flavored Markdown (GFM) | `.md` | Task lists, tables, reference links, alerts |
| GitLab Markdown | `.md` | Alerts (extended set: NOTE/TIP/WARNING/CAUTION/INFO/SUCCESS/QUESTION/DANGER) |
| MkDocs | `.md`, `mkdocs.yml` | mkdocs.yml present, nav structure, YAML frontmatter |
| Sphinx | `.rst`, `.md`, `conf.py` | RST directives (.. note::, .. warning::), roles (:ref:), toctree |
| Docusaurus | `.md`, `.mdx`, `sidebars.js`, `docusaurus.config.js` | Import statements, JSX tags, sidebar configuration |
| Obsidian | `.md`, `.obsidian/` | Wikilinks [[link]], embeds ![[image.png]], callouts > [!NOTE] |
| Quartz | `.md` | Hugo-style frontmatter, compatible with Obsidian wikilinks |
| CommonMark | `.md` | Standard Markdown (fallback) |

## Automatic Detection

```python
from pimd.compatibility import detect_flavor, CompatibilityLayer

# Detect from content
flavor = detect_flavor(content)
print(flavor)  # MarkdownFlavor.GFM

# Full pipeline: detect + normalize
layer = CompatibilityLayer()
normalized = layer.process(content, source_path="file.md")
```

## CLI Usage

```bash
# Detect flavor of a file
pimd flavor input.md

# Normalize during conversion (auto-detected)
pimd md input.md output.docx
```

## Normalization Rules

### Obsidian → Standard Markdown
- `[[page]]` → `[page](page.md)`
- `[[page|Display]]` → `[Display](page.md)`
- `[[page#section]]` → `[page](page.md#section)`
- `![[image.png]]` → `![image](image.png)`
- `> [!NOTE]` → Standard blockquote with label

### Sphinx RST → Markdown
- `.. note::` → `> **Note:**
- `:ref:`target`` → `` `target` ``
- `toctree` directives → Navigation list
- Section headers (`===`, `---`) → `#`, `##` headings

### Docusaurus MDX → Markdown
- `import` statements removed
- JSX tags converted to HTML
- `@site/` paths resolved
- Frontmatter extracted
- Sidebar structure mapped

### GitHub/GitLab Features
- Task lists: `- [x]` → `<input type="checkbox" checked>`
- Alerts: `> [!NOTE]` → `> **Note:**
- Reference links resolved inline
- Anchor IDs generated: `{#slug}`

## Frontmatter Formats

```yaml
# YAML (--- delimiters)
---
title: Guide
author: John
---

# TOML (+++ delimiters)
+++
title = "Guide"
+++

# JSON (--- delimiters with {...})
---
{"title": "Guide"}
---
```

## Flavor Detection Priority

1. File extension (`.mdx` → Docusaurus)
2. Project markers (mkdocs.yml, conf.py, .obsidian/)
3. Content signatures (wikilinks, RST directives, tables)
4. Fallback to CommonMark
