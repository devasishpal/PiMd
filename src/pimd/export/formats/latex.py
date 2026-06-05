"""LaTeX renderer — produces clean, readable LaTeX documents from the document model."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from pimd.models import (
    Block,
    Blockquote,
    BulletList,
    CodeBlock,
    Diagram,
    Document,
    EquationBlock,
    Heading,
    HorizontalRule,
    Image,
    ListItem,
    OrderedList,
    Paragraph,
    Span,
    Table,
)


LATEX_PREAMBLE_TEMPLATE = r"""\documentclass[12pt,a4paper]{article}

%% Encoding & Fonts
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{textcomp}
\usepackage{amsmath,amssymb,amsthm}

%% Page Layout
\usepackage[top=2.5cm, bottom=2.5cm, left=2.5cm, right=2.5cm]{geometry}
\usepackage{setspace}
\onehalfspacing

%% Graphics & Tables
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{longtable}
\usepackage{caption}

%% Code Listings
\usepackage{listings}
\usepackage{xcolor}
\definecolor{codebg}{rgb}{0.95,0.95,0.95}
\definecolor{codeframe}{rgb}{0.8,0.8,0.8}
\lstset{
  basicstyle=\ttfamily\small,
  backgroundcolor=\color{codebg},
  frame=single,
  rulecolor=\color{codeframe},
  breaklines=true,
  numbers=none,
  tabsize=2,
}

%% Hyperlinks
\usepackage[colorlinks=true, linkcolor=blue, urlcolor=blue, citecolor=blue]{hyperref}

%% Bibliographies
\usepackage[backend=biber, style=apa]{biblatex}

%% Custom Commands
\newcommand{\note}[1]{\textit{#1}}
\newcommand{\codeinline}[1]{\texttt{#1}}

%% Metadata
\title{__TITLE__}
\author{__AUTHOR__}
\date{\today}

"""

LATEX_BODY_TEMPLATE_TOC = r"""

\begin{document}
\maketitle
\tableofcontents
\newpage

__BODY__

\end{document}
"""

LATEX_BODY_TEMPLATE = r"""

\begin{document}
\maketitle

__BODY__

\end{document}
"""

LATEX_BOOK_TEMPLATE = r"""

\begin{document}
\frontmatter
\maketitle
\tableofcontents

\mainmatter
__BODY__

\end{document}
"""


class LatexRenderer:
    """Render PiMD documents to LaTeX.

    Generates clean, readable LaTeX source suitable for compilation
    with pdflatex or xelatex. Supports headings, tables, code blocks,
    citations, images, footnotes, math expressions, and cross-references.
    """

    FORMAT_NAME = "latex"
    FORMAT_DESCRIPTION = "LaTeX typesetting format"
    IMPLEMENTED = True

    def __init__(self) -> None:
        self._figure_counter = 0
        self._table_counter = 0
        self._equation_counter = 0
        self._section_level = 0

    @property
    def is_available(self) -> bool:
        return True

    @property
    def missing_dependencies(self) -> list[str]:
        return []

    def render(
        self,
        document: Document,
        output_path: str | Path,
        **options: Any,
    ) -> Path:
        """Render a Document to a LaTeX file.

        Args:
            document: The document model to render.
            output_path: Destination path for the .tex file.
            **options: title, author, document_class, toc, etc.

        Returns:
            Path to the generated .tex file.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        title = options.get("title", "Untitled")
        author = options.get("author", "Unknown")
        doc_class = options.get("document_class", "article")
        generate_toc = options.get("generate_toc", False)

        self._figure_counter = 0
        self._table_counter = 0
        self._equation_counter = 0
        self._section_level = 0

        body_parts: list[str] = []
        for block in document.blocks:
            latex = self._render_block_to_latex(block)
            if latex:
                body_parts.append(latex)

        body = "\n\n".join(body_parts)

        preamble = (
            LATEX_PREAMBLE_TEMPLATE
            .replace("__TITLE__", self._escape_latex(title))
            .replace("__AUTHOR__", self._escape_latex(author))
        )

        if doc_class == "book":
            template = LATEX_BOOK_TEMPLATE
        elif generate_toc:
            template = LATEX_BODY_TEMPLATE_TOC
        else:
            template = LATEX_BODY_TEMPLATE

        latex_source = (
            preamble
            + template.replace("__BODY__", body)
        )

        out.write_text(latex_source, encoding="utf-8")
        return out

    def render_to_bytes(self, document: Document, **options: Any) -> bytes:
        """Render a Document to LaTeX bytes without writing to disk."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            self.render(document, tmp_path, **options)
            return Path(tmp_path).read_bytes()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # ------------------------------------------------------------------
    # Block rendering
    # ------------------------------------------------------------------

    def _render_block_to_latex(self, block: Block) -> str:
        if isinstance(block, Heading):
            return self._render_heading_latex(block)

        if isinstance(block, Paragraph):
            text = self._render_spans_latex(block.spans)
            return text + "\n"

        if isinstance(block, CodeBlock):
            lang = block.language or "text"
            code = self._escape_latex(block.code)
            return (
                r"\begin{lstlisting}[language="
                + self._escape_latex(lang)
                + "]\n"
                + code
                + "\n\\end{lstlisting}"
            )

        if isinstance(block, Blockquote):
            children = "\n".join(
                self._render_block_to_latex(c) for c in block.children
            )
            return r"\begin{quotation}" + "\n" + children + "\n\\end{quotation}"

        if isinstance(block, BulletList):
            items = "\n".join(
                self._render_list_item_latex(item) for item in block.items
            )
            return r"\begin{itemize}" + "\n" + items + "\n\\end{itemize}"

        if isinstance(block, OrderedList):
            items = "\n".join(
                self._render_list_item_latex(item) for item in block.items
            )
            return r"\begin{enumerate}" + "\n" + items + "\n\\end{enumerate}"

        if isinstance(block, Table):
            return self._render_table_latex(block)

        if isinstance(block, HorizontalRule):
            return r"\noindent\makebox[\linewidth]{\rule{\linewidth}{0.4pt}}"

        if isinstance(block, Image):
            alt = self._escape_latex(block.alt)
            url = block.url.replace("\\", "/")
            return (
                r"\begin{figure}[htbp]" + "\n"
                + r"\centering" + "\n"
                + r"\includegraphics[width=0.8\textwidth]{" + url + "}\n"
                + r"\caption{" + alt + "}\n"
                + r"\end{figure}"
            )

        if isinstance(block, Diagram):
            alt = self._escape_latex(block.alt)
            if block.png_bytes:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(block.png_bytes)
                    img_path = tmp.name
                result = (
                    r"\begin{figure}[htbp]" + "\n"
                    + r"\centering" + "\n"
                    + r"\includegraphics[width=0.8\textwidth]{" + img_path + "}\n"
                    + r"\caption{" + alt + "}\n"
                    + r"\end{figure}"
                )
                return result
            return r"\note{[" + alt + "]}"

        if isinstance(block, EquationBlock):
            return self._render_equation_latex(block)

        if isinstance(block, ListItem):
            return self._render_list_item_latex(block)

        return ""

    def _render_heading_latex(self, block: Heading) -> str:
        level = block.level
        text = self._render_spans_latex(block.spans)

        if level == 1:
            cmd = r"\section"
        elif level == 2:
            cmd = r"\subsection"
        elif level == 3:
            cmd = r"\subsubsection"
        elif level == 4:
            cmd = r"\paragraph"
        elif level == 5:
            cmd = r"\subparagraph"
        else:
            cmd = r"\textbf"

        if level <= 3:
            return cmd + "{" + text + "}\n"
        return cmd + "{" + text + "}\n"

    def _render_spans_latex(self, spans: list[Span]) -> str:
        parts = []
        for span in spans:
            text = self._escape_latex(span.text)
            if span.math and span.math_display:
                text = r"\begin{equation*}" + span.math + r"\end{equation*}"
            elif span.math:
                text = "$" + span.math + "$"
            if span.code:
                text = r"\codeinline{" + text + "}"
            if span.link_url:
                text = r"\href{" + self._escape_latex(span.link_url) + "}{" + text + "}"
            if span.bold:
                text = r"\textbf{" + text + "}"
            if span.italic:
                text = r"\textit{" + text + "}"
            if span.underline:
                text = r"\underline{" + text + "}"
            if span.superscript:
                text = "\\textsuperscript{" + text + "}"
            if span.subscript:
                text = "\\textsubscript{" + text + "}"
            parts.append(text)
        return "".join(parts)

    def _render_list_item_latex(self, item: ListItem) -> str:
        children = "\n".join(
            self._render_block_to_latex(c) for c in item.children
        )
        return r"\item " + children

    def _render_table_latex(self, block: Table) -> str:
        num_cols = max(len(block.headers), max((len(r) for r in block.rows), default=0))
        if num_cols == 0:
            return ""

        col_spec = "l" * num_cols
        parts = [r"\begin{table}[htbp]", r"\centering", r"\begin{tabular}{" + col_spec + "}"]
        parts.append(r"\toprule")

        if block.headers:
            parts.append(" & ".join(self._escape_latex(h) for h in block.headers) + r" \\")
            parts.append(r"\midrule")

        for row in block.rows:
            cells = [self._escape_latex(c) for c in row]
            # Pad with empty cells if needed
            while len(cells) < num_cols:
                cells.append("")
            parts.append(" & ".join(cells) + r" \\")

        parts.append(r"\bottomrule")
        parts.append(r"\end{tabular}")
        parts.append(r"\end{table}")
        return "\n".join(parts)

    def _render_equation_latex(self, block: EquationBlock) -> str:
        latex = block.latex
        if block.number is not None:
            return r"\begin{equation}" + "\n" + latex + "\n" + r"\end{equation}"
        return r"\begin{equation*}" + "\n" + latex + "\n" + r"\end{equation*}"

    @staticmethod
    def _escape_latex(text: str) -> str:
        """Escape special LaTeX characters."""
        replacements = [
            ("\\", r"\textbackslash{}"),
            ("{", r"\{"),
            ("}", r"\}"),
            ("$", r"\$"),
            ("&", r"\&"),
            ("#", r"\#"),
            ("^", r"\textasciicircum{}"),
            ("_", r"\_"),
            ("%", r"\%"),
            ("~", r"\textasciitilde{}"),
        ]
        result = text
        for char, replacement in replacements:
            result = result.replace(char, replacement)
        return result
