# Diagram Guide

PiMD includes a universal diagram rendering architecture that supports 16+ diagram languages with auto-detection, caching, plugin extensibility, and professional DOCX embedding.

## Supported Diagram Languages

| Language | Renderer | Auto-Detect | Aliases |
|----------|----------|-------------|---------|
| Mermaid | Mermaid | Yes | `mmd` |
| PlantUML | PlantUML | Yes | `puml` |
| Graphviz DOT | Graphviz | Yes | `graphviz` |
| D2 | D2 | Yes | |
| ASCII / DITAA | ASCII | Yes | `ditaa` |
| SVG | SVG | No | |
| BlockDiag | BlockDiag | No | |
| SeqDiag | SeqDiag | No | |
| ActDiag | ActDiag | No | |
| NwDiag | NwDiag | No | |
| PacketDiag | PacketDiag | No | |
| BPMN | BPMN | No | |
| Vega | Vega | Yes | |
| Vega-Lite | Vega-Lite | Yes | `vega-lite` |

## Quick Start

When you run `pimd md input.md output.docx`, PiMD automatically:

1. **Detects** diagram code blocks (```mermaid, ```plantuml, etc.)
2. **Renders** them using the appropriate renderer
3. **Embeds** them as high-quality images in the DOCX
4. **Numbers** figures consecutively with captions
5. **Caches** results for faster rebuilds

## Auto-Detection

PiMD can detect diagram types even without explicit language tags:

```markdown
\`\`\`
graph TD
    A-->B
\`\`\`
```

This will be auto-detected as **Mermaid** because the content matches the `graph` keyword pattern.

### Detection Priority

1. Explicit language tag (e.g., \`\`\`mermaid)
2. Language alias (e.g., \`\`\`mmd → mermaid)
3. Pattern-based detection (regex on source content)
4. ASCII diagram heuristics (box-drawing chars, +-- | patterns)

## Diagram Numbering

Figures are automatically numbered in the order they appear:

- **Figure 1**: First diagram with caption
- **Figure 2**: Second diagram with caption
- etc.

Captions are displayed below the diagram in italic gray text.

## Caching

Rendered diagrams are cached using SHA256 content hashing:

- **Memory cache**: Fast, in-process cache for single sessions
- **Filesystem cache**: Persistent cache across runs
- **Cache key**: SHA256(source + language)

## Plugin System

Register custom diagram renderers without modifying PiMD:

```python
from pimd import register_diagram_renderer, DiagramRenderer, DiagramResult

class MyRenderer(DiagramRenderer):
    language = "mydsl"
    name = "My DSL Renderer"
    version = "1.0"
    description = "Renders MyDSL diagrams"

    def is_available(self) -> bool:
        return True

    def render(self, source: str, **options) -> DiagramResult:
        png_data = render_my_dsl(source)
        return DiagramResult(source=source, language=self.language, png=png_data)

register_diagram_renderer("mydsl", MyRenderer())
```

See [Plugin Development](#plugin-development) for details.

## Context & Plugin Pipeline

The `DiagramContext` object carries configuration and metadata through the rendering pipeline:

```python
from pimd.diagrams import DiagramContext, DiagramScaleMode, DiagramPlacement

ctx = DiagramContext(
    source=source,
    language="mermaid",
    scale_mode=DiagramScaleMode.FIT_WIDTH,
    placement=DiagramPlacement.CENTER,
    caption="My Diagram",
    label="fig:my_diagram",
)
```

### DiagramPlugin Hooks

| Hook | Trigger |
|------|---------|
| `BEFORE_RENDER` | Before renderer executes |
| `AFTER_RENDER` | After renderer completes |
| `BEFORE_CACHE` | Before cache lookup |
| `AFTER_CACHE` | After cache hit/miss |
| `BEFORE_EMBED` | Before embedding in DOCX |
| `AFTER_EMBED` | After embedding in DOCX |
| `ON_ERROR` | When rendering fails |
| `ON_FALLBACK` | When fallback is used |

## Installation Requirements

Some renderers require external CLI tools:

| Renderer | Required Tool | Install |
|----------|---------------|---------|
| Mermaid | `mmdc` (mermaid-cli) | `npm install -g @mermaid-js/mermaid-cli` |
| PlantUML | Java + `plantuml.jar` | `apt install plantuml` or download JAR |
| Graphviz | `dot` | `apt install graphviz` |
| D2 | `d2` | `npm install -g d2` or `go install` |
| ASCII | Pillow | `pip install Pillow` |
| SVG | `cairosvg` or `inkscape` | `pip install cairosvg` |
| BlockDiag | `blockdiag`, `seqdiag`, etc. | `pip install blockdiag seqdiag actdiag nwdiag` |
| BPMN | `bpmn-to-svg` | `npm install -g bpmn-to-svg` |
| Vega | `vg2svg` | `npm install -g vega` |

Run `pimd diagrams doctor` to check which renderers are available on your system.

## Advanced Configuration

```python
from pimd.diagrams import DiagramConfig

config = DiagramConfig(
    cache=True,
    svg_preferred=True,
    max_width=6.5,       # inches
    figure_captions=True,
    auto_number=True,
    default_width=600,
    default_height=400,
    dpi=150,
    max_concurrent=4,
    detect_diagrams=True,
)
```
