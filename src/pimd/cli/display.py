"""Rich display helpers — banner, progress, error panels."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from rich.console import Console

console = Console(color_system="auto", highlight=False)
_error_console = Console(stderr=True, highlight=False)

# ======================================================================
# Banner
# ======================================================================


def show_banner() -> None:
    """Display the PiMD startup banner."""
    banner_text = Text()
    banner_text.append("PiMD", style="bold cyan")
    banner_text.append("\n")
    banner_text.append("Professional Document Converter", style="dim white")

    panel = Panel(
        Align.center(banner_text),
        border_style="cyan",
        padding=(1, 4),
        width=50,
    )
    console.print()
    console.print(panel)
    console.print()


def show_sub_banner(command: str) -> None:
    """Show a small status banner for a specific command."""
    from pimd import __version__

    text = Text()
    text.append("PiMD ", style="cyan")
    text.append(f"v{__version__}", style="dim")
    text.append(" — ", style="dim")
    text.append(command, style="bold white")
    console.print(text)


# ======================================================================
# Progress
# ======================================================================


@contextmanager
def progress_spinner(
    description: str = "Working...",
    transient: bool = True,
) -> Generator[Progress, Any, None]:
    """A spinner-based progress context manager.

    Usage::

        with progress_spinner("Parsing HTML") as progress:
            task = progress.add_task("", total=None)
            # ... do work ...
            progress.update(task, description="[green]Done[/]")
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=transient,
    )
    with progress:
        task = progress.add_task(description, total=None)
        try:
            yield progress
        finally:
            progress.update(task, visible=not transient)


@contextmanager
def progress_bar(
    total: int = 100,
    description: str = "Processing...",
    transient: bool = True,
) -> Generator[Progress, Any, None]:
    """A progress-bar context manager for file operations.

    Usage::

        with progress_bar(total=100, description="Converting") as progress:
            task = progress.add_task("", total=100)
            # ... do work, progress.update(task, advance=n)
            progress.update(task, advance=100)
    """
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=transient,
    )
    with progress:
        task = progress.add_task(description, total=total)
        try:
            yield progress, task
        finally:
            progress.update(task, visible=not transient)


# ======================================================================
# Steps (sequential check-mark steps)
# ======================================================================


class StepDisplay:
    """Display a sequence of steps with check-mark / failure indicators.

    Usage::

        steps = StepDisplay()
        steps.add("Reading file")
        steps.add("Parsing")
        steps.add("Rendering")
        steps.add("Writing DOCX")

        for name in steps.names:
            steps.start(name)
            # ... do work ...
            steps.succeed(name)

        steps.complete("output.docx")
    """

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()
        self.names: list[str] = []
        self._status: dict[str, str] = {}  # name -> "waiting" | "running" | "ok" | "fail"
        self._start_times: dict[str, float] = {}

    def add(self, name: str) -> None:
        """Register a step."""
        self.names.append(name)
        self._status[name] = "waiting"

    def start(self, name: str) -> None:
        """Mark a step as in-progress."""
        self._status[name] = "running"
        self._start_times[name] = time.monotonic()
        self._render()

    def succeed(self, name: str) -> None:
        """Mark a step as completed successfully."""
        self._status[name] = "ok"
        self._render()

    def fail(self, name: str) -> None:
        """Mark a step as failed."""
        self._status[name] = "fail"
        self._render()

    def complete(self, output_path: str, elapsed: float | None = None) -> None:
        """Show final success message with output path."""
        fallback = time.monotonic() - min(self._start_times.values()) if self._start_times else 0
        duration = elapsed if elapsed is not None else fallback

        self._console.print()
        text = Text()
        text.append(" Conversion completed", style="bold green")
        if duration:
            text.append(f" in {duration:.2f}s", style="dim")
        self._console.print(Panel(text, border_style="green"))

        out_text = Text()
        out_text.append(" Output: ", style="bold")
        out_text.append(output_path, style="cyan")
        self._console.print(out_text)
        self._console.print()

    def _render(self) -> None:
        for name in self.names:
            status = self._status.get(name, "waiting")
            if status == "running":
                icon = " Running..."
                style = "yellow"
            elif status == "ok":
                icon = " Done"
                style = "green"
            elif status == "fail":
                icon = " Failed"
                style = "red"
            else:
                icon = " ..."
                style = "dim"

            self._console.print(f"  {name}{icon}", style=style)


# ======================================================================
# Error panels
# ======================================================================


def display_error(title: str, message: str, hint: str | None = None) -> None:
    """Show a beautiful error panel.

    Args:
        title: Short error title (e.g. "Conversion Error").
        message: Descriptive error message.
        hint: Optional suggestion for the user.
    """
    content = Text(message, style="red")
    if hint:
        content.append("\n\n")
        content.append(f"Tip: {hint}", style="dim italic")

    panel = Panel(
        content,
        title=f" {title} ",
        title_align="left",
        border_style="red",
    )
    _error_console.print()
    _error_console.print(panel)
    _error_console.print()


def display_warning(message: str) -> None:
    """Show a warning panel."""
    panel = Panel(
        Text(message, style="yellow"),
        border_style="yellow",
        padding=(0, 1),
    )
    _error_console.print(panel)


def display_success(message: str) -> None:
    """Show a success message."""
    _error_console.print(f" {message}", style="bold green")


# ======================================================================
# Doctor results
# ======================================================================


def doctor_table(items: list[dict[str, str]]) -> None:
    """Render a doctor-check results table.

    Each item: {"check": str, "status": str, "detail": str}
    Status: "ok", "warning", "error"
    """
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Icon", width=2)
    table.add_column("Check", style="bold", width=20)
    table.add_column("Detail")

    for item in items:
        status = item.get("status", "ok")
        if status == "ok":
            icon = "[green]OK[/]"
        elif status == "warning":
            icon = "[yellow]Warning[/]"
        else:
            icon = "[red]Error[/]"
        table.add_row(icon, item.get("check", ""), item.get("detail", ""))

    console.print(table)


# ======================================================================
# Info table
# ======================================================================


def info_table(data: dict[str, str]) -> None:
    """Render key-value info table."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", width=30)
    table.add_column("Value")
    for key, value in data.items():
        table.add_row(key, value)
    console.print(table)
