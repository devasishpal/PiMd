# Scientific Publishing Guide

PiMD provides a complete scientific publishing subsystem for academic papers, research documents, and technical reports.

## Features

- **Native Word Equations**: LaTeX → editable OMML
- **Citations**: APA, MLA, IEEE, Chicago styles
- **Bibliography**: BibTeX file support
- **Footnotes & Endnotes**: Automatic numbering and placement
- **Cross-References**: Section, figure, table, equation references
- **Document Templates**: Academic, Technical, Professional, Book
- **Chemical Formulas**: Automatic detection and rendering
- **Callouts/Admonitions**: Notes, warnings, tips, and more

## Academic Paper Structure

A typical academic paper in PiMD:

```markdown
---
title: "A Novel Approach to Document Generation"
author: "Jane Doe"
date: "2024-12-01"
abstract: |
  This paper presents a novel approach...
tags: [document generation, LaTeX, OMML]
status: draft
---

## Introduction

Lorem ipsum dolor sit amet...
```

## Citations

### BibTeX Database

Create a `references.bib` file:

```bibtex
@article{smith2024,
  author = {Smith, John},
  title = {A New Method},
  journal = {Journal of Examples},
  year = {2024},
  volume = {42},
  pages = {123--145}
}
```

### In-Text Citations

```latex
As shown in Smith \cite{smith2024}, the method improves...
```

### Bibliography

```latex
\bibliography{references}
```

### Citation Styles

| Style | Format |
|-------|--------|
| APA | (Smith, 2024) |
| IEEE | [1] |
| MLA | (Smith 123) |
| Chicago | Smith 2024 |

## Footnotes

```markdown
This is a statement with a footnote.[^1]

[^1]: Detailed explanation of the statement.
```

## Callouts / Admonitions

```markdown
> [!NOTE]
> This is important context for the reader.

> [!WARNING]
> Be careful with this step.

> [!TIP]
> Here's a helpful suggestion.

> [!IMPORTANT]
> This is a key requirement.
```

In DOCX output, callouts render as formatted tables with colored left borders, background fills, and styled titles.

## Cross-References

```latex
See Section \ref{sec:methods} and Figure \ref{fig:results}.
```

The document validator checks that all `\ref{}` references have matching `\label{}` definitions and generates warnings for broken references — without halting document generation.

## Templates

PiMD includes five academic-oriented templates:

| Template | Use Case |
|----------|----------|
| Academic | Research papers, theses |
| Technical | Technical reports, documentation |
| Professional | Business proposals, whitepapers |
| Book | Book manuscripts, long-form content |
| Custom | User-defined templates |

```python
from pimd import PiMD
from pimd.templates import TemplateManager

engine = PiMD()
tm = TemplateManager()
academic_template = tm.get("academic")

# Apply template overrides
config = academic_template.merge_config({
    "page_numbers": True,
    "generate_toc": True,
    "cover_page": True,
})
```

## Equation Features

- Inline: `$E = mc^2$`
- Display: `$$ \int_{-\infty}^{\infty} e^{-x^2} dx $$`
- Automatic numbering: `(1)`, `(2)`, `(3)`
- Chemical formulas: `H_2O`, `CO_2`, `CH_4`
- Cross-references: `\label{eq:energy}` / `\ref{eq:energy}`

## Document Validation

```bash
pimd doctor
```

The validation system checks for:
- Broken diagram references
- Malformed equations
- Missing assets (images, attachments)
- Broken `\ref{}` / `\label{}` references
- Invalid citations
- Document size and nesting limits

Validation never terminates document generation — issues are reported as warnings.
