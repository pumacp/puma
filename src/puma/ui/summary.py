"""Themed end-of-run summary table for the PUMA CLI.

Presentation only: a read-only Rich panel summarizing a completed run. It never
re-computes a metric, never touches the database or JSONL, and degrades
gracefully — any missing field renders as a muted "—" rather than raising.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from puma.ui.themes import Theme

_DASH = "—"


def _fmt_runtime(seconds: float) -> str:
    if seconds >= 60:
        minutes, secs = divmod(int(seconds), 60)
        return f"{minutes}m {secs}s"
    return f"{seconds:.2f}s"


def _samples_cell(theme: Theme, succeeded: int, failed: int, total: int) -> Text:
    """Build the 'Samples' value: succeeded (success), failed (error if any,
    else muted), total."""
    cell = Text()
    cell.append(str(succeeded), style=theme.success)
    cell.append(" succeeded / ")
    cell.append(str(failed), style=theme.error if failed > 0 else theme.muted)
    cell.append(f" failed / {total} total")
    return cell


def render_run_summary(
    theme: Theme,
    *,
    run_id: str,
    task: str,
    model: str,
    profile: str,
    samples_total: int,
    samples_succeeded: int,
    samples_failed: int,
    primary_metric_name: str,
    primary_metric_value: float,
    runtime_seconds: float,
    emissions_g_co2: float | None,
    predictions_path: Path | None,
) -> RenderableType:
    """Build the themed run-summary as a Rich Panel(Table). Never raises."""
    table = Table(show_header=True, header_style=theme.title, box=None, pad_edge=False)
    table.add_column("Field", style=theme.muted)
    table.add_column("Value")

    def _val(value: Any) -> Text:
        if value is None:
            return Text(_DASH, style=theme.muted)
        return Text(str(value))

    table.add_row("Run ID", _val(run_id))
    table.add_row("Task", _val(task))
    table.add_row("Model", _val(model))
    table.add_row("Profile", _val(profile))
    table.add_row("Samples", _samples_cell(theme, samples_succeeded, samples_failed, samples_total))

    if isinstance(primary_metric_value, float) and math.isnan(primary_metric_value):
        metric_cell = Text(_DASH, style=theme.muted)
    else:
        metric_cell = Text(f"{primary_metric_value:.4f}", style=theme.accent)
    table.add_row(primary_metric_name or "metric", metric_cell)

    table.add_row("Runtime", _val(_fmt_runtime(runtime_seconds)))

    if emissions_g_co2 is None:
        table.add_row("Emissions", Text(_DASH, style=theme.muted))
    else:
        table.add_row("Emissions", _val(f"{emissions_g_co2:.4f} gCO2eq"))

    table.add_row(
        "Predictions", _val(str(predictions_path) if predictions_path is not None else None)
    )

    return Panel(
        table,
        title=f"[{theme.title}]Run summary[/]",
        border_style=theme.border,
        padding=(1, 2),
    )


def print_run_summary(console: Console, theme: Theme, **kwargs: Any) -> None:
    """Render the run summary and print it to the given (stderr-bound) console."""
    console.print(render_run_summary(theme, **kwargs))
