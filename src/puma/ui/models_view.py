"""Themed renderers for the ``puma models`` discovery subcommands.

Presentation only. The model data types are imported under ``TYPE_CHECKING`` so
the UI layer carries no runtime dependency on the models package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from puma.ui.themes import Theme

if TYPE_CHECKING:
    from puma.models.catalog import CuratedModel
    from puma.models.client import LocalModel

_RECOMMENDED_FOOTER = (
    "Local? column reflects current Ollama state; `ollama pull <name>` to fetch missing models."
)


def _human_size(num_bytes: int) -> str:
    """Format a byte count as a short human-readable string (e.g. ``1.9 GB``)."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1000.0:
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1000.0
    return f"{size:.1f} TB"


def _status_text(theme: Theme, status: str) -> Text:
    """Themed status cell: ``validated`` -> success color, else warning color."""
    style = theme.success if status == "validated" else theme.warning
    return Text(status, style=style)


def render_models_list_table(theme: Theme, models: list[LocalModel]) -> RenderableType:
    """Render locally-pulled Ollama models, or a help panel when none exist."""
    if not models:
        return Panel(
            Text(
                "No models pulled locally. Use `ollama pull <name>` to fetch one.",
                style=theme.muted,
            ),
            title=f"[{theme.title}]Local Ollama models[/]",
            border_style=theme.border,
            padding=(1, 2),
        )
    table = Table(show_header=True, header_style=theme.title, box=None, pad_edge=False)
    table.add_column("Name", style=theme.accent)
    table.add_column("Family")
    table.add_column("Size", justify="right")
    table.add_column("Parameters", justify="right")
    table.add_column("Quantization")
    table.add_column("Modified")
    for model in models:
        table.add_row(
            model.name,
            model.family or "—",
            _human_size(model.size_bytes),
            model.parameter_size or "—",
            model.quantization or "—",
            model.modified_at or "—",
        )
    return Panel(
        table,
        title=f"[{theme.title}]Local Ollama models[/]",
        border_style=theme.border,
        padding=(1, 2),
    )


def render_model_show_panel(theme: Theme, model: LocalModel) -> RenderableType:
    """Render every field of a single :class:`LocalModel` as a Field/Value table."""
    table = Table(show_header=True, header_style=theme.title, box=None, pad_edge=False)
    table.add_column("Field", style=theme.muted)
    table.add_column("Value")
    rows = [
        ("Name", model.name),
        ("Family", model.family or "—"),
        ("Parameters", model.parameter_size or "—"),
        ("Quantization", model.quantization or "—"),
        ("Size", _human_size(model.size_bytes)),
        ("Digest", model.digest or "—"),
        ("Modified", model.modified_at or "—"),
    ]
    for field, value in rows:
        table.add_row(field, value)
    return Panel(
        table,
        title=f"[{theme.title}]{model.name}[/]",
        border_style=theme.border,
        padding=(1, 2),
    )


def render_recommended_table(
    theme: Theme,
    pairs: list[tuple[CuratedModel, LocalModel | None]],
) -> RenderableType:
    """Render the curated catalog paired with current local availability."""
    table = Table(show_header=True, header_style=theme.title, box=None, pad_edge=False)
    table.add_column("Name", style=theme.accent)
    table.add_column("Family")
    table.add_column("Params", justify="right")
    table.add_column("Validated for")
    table.add_column("Status")
    table.add_column("Local?", justify="center")
    table.add_column("Rationale")
    for curated, local in pairs:
        local_cell = (
            Text("✓", style=theme.success) if local is not None else Text("—", style=theme.muted)
        )
        table.add_row(
            curated.name,
            curated.family,
            f"{curated.parameter_size_b:.1f} B",
            ", ".join(sorted(curated.validated_for)) or "—",
            _status_text(theme, curated.status),
            local_cell,
            curated.rationale or "—",
        )
    return Panel(
        Group(table, Text(""), Text(_RECOMMENDED_FOOTER, style=theme.muted)),
        title=f"[{theme.title}]Curated PUMA models[/]",
        border_style=theme.border,
        padding=(1, 2),
    )
