"""Shared test fixtures for PiMD."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

# ------------------------------------------------------------------
# Sample data
# ------------------------------------------------------------------

SAMPLE_MARKDOWN = """# Test Document

This is a **bold** and *italic* paragraph.

- List item 1
- List item 2

1. Ordered item 1
2. Ordered item 2

```python
print("hello")
```

> A blockquote.
"""

SAMPLE_HTML = """<!DOCTYPE html>
<html>
<body>
<h1>Test Document</h1>
<p>This is a <strong>bold</strong> and <em>italic</em> paragraph.</p>
<ul>
<li>List item 1</li>
<li>List item 2</li>
</ul>
</body>
</html>
"""

SAMPLE_MARKDOWN_WITH_DIAGRAMS = """# Diagrams

```mermaid
graph TD
    A-->B
```

```plantuml
@startuml
A->B: hello
@enduml
```
"""


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def sample_markdown() -> str:
    return SAMPLE_MARKDOWN


@pytest.fixture
def sample_html() -> str:
    return SAMPLE_HTML


@pytest.fixture
def sample_markdown_with_diagrams() -> str:
    return SAMPLE_MARKDOWN_WITH_DIAGRAMS


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    """Create a temporary output .docx path."""
    return tmp_path / "output.docx"


@pytest.fixture
def tmp_input_md(tmp_path: Path) -> Path:
    """Create a temporary Markdown input file."""
    path = tmp_path / "input.md"
    path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
    return path


@pytest.fixture
def tmp_input_html(tmp_path: Path) -> Path:
    """Create a temporary HTML input file."""
    path = tmp_path / "input.html"
    path.write_text(SAMPLE_HTML, encoding="utf-8")
    return path


@pytest.fixture
def pimd_engine() -> Any:
    """Create a PiMD engine instance with caching disabled."""
    from pimd import PiMD

    return PiMD(enable_cache=False)


@pytest.fixture
def pimd_engine_cached() -> Any:
    """Create a PiMD engine instance with caching enabled."""
    from pimd import PiMD

    return PiMD(enable_cache=True)
