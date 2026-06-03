# PiMD Migration Guide

Migrate existing documentation projects to PiMD for consistent DOCX output.

## From GitHub/GitLab Wikis

```bash
# 1. Clone your wiki repository
git clone https://github.com/user/repo.wiki.git

# 2. Convert with GFM flavor
pimd repo repo.wiki/ output/ --format docx

# 3. Or use the GitHub export profile
pimd md Home.md Home.docx --profile github
```

## From MkDocs

```bash
# 1. PiMD automatically reads mkdocs.yml
pimd repo docs/ output/

# The navigation structure is preserved:
# - mkdocs.yml nav section → DOCX TOC
# - Section ordering maintained
# - Site metadata extracted
```

```python
from pimd.mkdocs_ import MkDocsProjectConverter

converter = MkDocsProjectConverter()
converter.convert("mkdocs.yml", "output.docx")
```

## From Docusaurus

```bash
# Handles:
# - docusaurus.config.js → document metadata
# - sidebars.js/ts → table of contents
# - Versioned docs (versioned_docs/)
# - Category metadata (_category_.json)

pimd repo docs/ output/ --merge
```

```python
from pimd.docusaurus import DocusaurusProjectConverter

converter = DocusaurusProjectConverter()
stats = converter.convert("docusaurus.config.js", "output/")
```

## From Sphinx / Read the Docs

```bash
# Converts:
# - conf.py → document metadata
# - RST files → Markdown → DOCX
# - toctree directives → chapter structure
# - Admonitions → callout boxes
# - Cross-references → hyperlinks

pimd repo source/ output/
```

```python
from pimd.sphinx import SphinxProjectConverter

converter = SphinxProjectConverter()
converter.convert("conf.py", "output.docx")
```

## From Obsidian Vaults

```bash
# Converts:
# - Wikilinks → standard Markdown links
# - Embeds → images/attachments
# - Callouts → formatted blockquotes
# - Graph structure → linkage report
# - Tags/aliases/frontmatter → metadata

pimd repo my-vault/ output/
```

```python
from pimd.obsidian import VaultExporter, VaultConfig

config = VaultConfig.from_vault("my-vault/")
exporter = VaultExporter("my-vault/", "output/", config)
stats = exporter.export()
```

## Export Profiles

Choose a preset that matches your target output:

```bash
# GitHub-style document
pimd md input.md output.docx --profile github

# Academic paper (Times New Roman, numbered headings, bibliography)
pimd md paper.md paper.docx --profile academic

# Corporate report (cover page, TOC, branding)
pimd md report.md report.docx --profile corporate

# Book (numbered chapters, page numbers)
pimd md manuscript.md book.docx --profile book

# Technical documentation (code highlighting, diagrams)
pimd md guide.md guide.docx --profile technical
```

## Custom Profiles

```python
from pimd.profiles import builtin_profile, customize_profile, ProfileType

profile = builtin_profile(ProfileType.CORPORATE)
profile = customize_profile(profile, {
    "title": "Custom Report",
    "font_family": "Arial",
    "heading_color": "#2B579A",
})
```

## Multi-Format Export

```bash
# Export to multiple formats
pimd export input.md output.pdf
pimd export input.md output.html
pimd export input.md output.txt
pimd export input.md output.docx
```

## Validation

Before migration, analyze your documentation project:

```bash
# Check for issues
pimd validate input.md

# Analyze entire project
pimd analyze docs/

# Detect flavor
pimd flavor input.md
```

## Common Migration Patterns

### Simple Wiki to DOCX
```bash
pimd repo wiki/ wiki-output/ --merge
```

### Multi-ecosystem to Single Book
```python
from pimd.merge import DocumentMerger
from pimd.repository import convert_repository

# Convert each section
convert_repository("docs/", "build/section1.docx")
convert_repository("wiki/", "build/section2.docx")

# Merge into one document
merger = DocumentMerger()
merger.merge(["build/section1.docx", "build/section2.docx"], "complete.docx")
```
