"""Themed renderers for the diagnostic subcommands (``puma doctor`` / ``puma env``).

Presentation only. Imports the diagnostics data types under TYPE_CHECKING so
the UI layer carries no runtime dependency on the diagnostics package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from puma.ui.themes import Theme

if TYPE_CHECKING:
    from puma.diagnostics.checks import CheckResult
    from puma.diagnostics.env import EnvironmentInfo

_ICONS = {"ok": "✓", "warn": "⚠", "fail": "✗"}


def _status_cell(theme: Theme, status: str) -> Text:
    style = {
        "ok": theme.success,
        "warn": theme.warning,
        "fail": theme.error,
    }.get(status, theme.muted)
    return Text(f"{_ICONS.get(status, '?')} {status}", style=style)


def render_doctor_table(theme: Theme, results: list[CheckResult]) -> RenderableType:
    show_hints = any(r.hint for r in results)
    table = Table(show_header=True, header_style=theme.title, box=None, pad_edge=False)
    table.add_column("Check", style=theme.muted)
    table.add_column("Status")
    table.add_column("Detail")
    if show_hints:
        table.add_column("Hint", style=theme.muted)
    for result in results:
        row = [Text(result.name), _status_cell(theme, result.status), Text(result.detail)]
        if show_hints:
            row.append(Text(result.hint or ""))
        table.add_row(*row)
    return Panel(
        table,
        title=f"[{theme.title}]Environment doctor[/]",
        border_style=theme.border,
        padding=(1, 2),
    )


def render_env_table(theme: Theme, env: EnvironmentInfo) -> RenderableType:
    table = Table(show_header=True, header_style=theme.title, box=None, pad_edge=False)
    table.add_column("Field", style=theme.muted)
    table.add_column("Value")
    rows = [
        ("PUMA version", env.puma_version),
        ("Python", env.python_version),
        ("Platform", env.platform),
        ("Theme", env.theme),
        ("Profile", env.profile),
        ("Ollama endpoint", env.ollama_endpoint),
        ("Database", env.db_path),
        ("Cache dirs", ", ".join(env.cache_dirs)),
    ]
    for field, value in rows:
        table.add_row(field, value)
    return Panel(
        table,
        title=f"[{theme.title}]Environment[/]",
        border_style=theme.border,
        padding=(1, 2),
    )
