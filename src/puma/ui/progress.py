"""Themed ``rich.Progress`` factory for the PUMA retro CLI.

A leaf helper that builds a progress display styled from a :class:`Theme`.
Display only: it writes to a stderr-bound Console by default so stdout stays
clean for deterministic command output, and it never touches the data path.
"""

from __future__ import annotations

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from puma.ui.themes import Theme


def make_progress(
    theme: Theme,
    console: Console | None = None,
    enabled: bool = True,
) -> Progress:
    """Build a themed :class:`rich.progress.Progress`.

    Args:
        theme: color theme supplying the column styles.
        console: console to render on; defaults to a stderr-bound Console so
            stdout is left clean for deterministic output.
        enabled: when False (e.g. ``--quiet``), the Progress is created in
            Rich's no-op (``disable=True``) mode.

    The Progress is also disabled automatically when the console is not a
    terminal (non-tty, captured output, CI logs). The factory does NOT start
    the progress — the caller manages the lifecycle:
    ``with make_progress(...) as progress: ...``.
    """
    progress_console = console if console is not None else Console(stderr=True)
    disable = (not enabled) or (not progress_console.is_terminal)
    return Progress(
        SpinnerColumn(style=theme.accent),
        TextColumn(f"[{theme.title}]{{task.description}}"),
        BarColumn(
            complete_style=theme.accent,
            finished_style=theme.success,
            pulse_style=theme.muted,
        ),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=progress_console,
        disable=disable,
    )
