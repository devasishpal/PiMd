# Equation Guide

PiMD provides native Word equation support through a LaTeX-to-OMML compiler. Equations are rendered as editable OMML (Office Math Markup Language) elements — not images — so they can be edited directly in Microsoft Word.

## Features

- **Native Word Equations**: LaTeX → OMML (editable in Word)
- **SVG Fallback**: If OMML compilation fails
- **Automatic Numbering**: `(1)`, `(2)`, `(3)` with cross-reference support
- **Chemical Formulas**: H₂O, CO₂, NH₃, CH₄ with automatic detection
- **Inline & Display**: `$...$` for inline, `$$...$$` for display
- **MathJax / KaTeX Compatible**: Standard delimiters supported

## Supported LaTeX Syntax

### Inline Math

```latex
$E = mc^2$
```

Rendered as an inline equation within a paragraph.

### Display Math

```latex
$$
\int_{-\infty}^{\infty} e^{-x^2} \, dx = \sqrt{\pi}
$$
```

Rendered as a centered block equation with optional numbering.

### Fractions

```latex
\frac{a}{b}
\quad
\frac{n!}{k!(n-k)!}
```

### Matrices

```latex
\begin{pmatrix}
a & b \\
c & d
\end{pmatrix}
```

### Integrals

```latex
\int_{a}^{b} f(x) \, dx
\quad
\iint_{D} f(x,y) \, dA
```

### Summations

```latex
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
```

### Greek Letters

```latex
\alpha, \beta, \gamma, \delta, \epsilon, \theta, \mu, \pi, \sigma, \phi, \omega
\Gamma, \Delta, \Theta, \Pi, \Sigma, \Phi, \Omega
```

### Chemical Formulas

```latex
H_2O
CO_2
NH_3
CH_4
C_6H_{12}O_6
```

Chemical formulas are automatically detected by the presence of element symbols and subscript patterns. They are rendered as OMML with proper subscript formatting.

## Equation Numbering

Display equations are automatically numbered `(1)`, `(2)`, `(3)`:

```latex
$$
E = mc^2
$$
```

This renders as:

```
E = mc²                    (1)
```

## Cross-References

Use `\label{...}` and `\ref{...}` for cross-references:

```latex
As shown in equation \ref{eq:energy}:

$$
E = mc^2 \label{eq:energy}
$$
```

The validator checks that all `\ref{}` references have matching `\label{}` definitions.

## Fallback Chain

1. **OMML** (native Word equation) — preferred
2. **SVG** — if OMML compilation fails
3. **LaTeX source** — displayed as formatted text if both fail

## Configuration

```python
from pimd.equations import EquationConfig

config = EquationConfig(
    numbering=True,
    number_start=1,
    chemical_detection=True,
    fallback_to_svg=True,
    cache_results=True,
)
```

## CLI Diagnostics

Run `pimd equations doctor` to check if the equation engine is available and working correctly.
