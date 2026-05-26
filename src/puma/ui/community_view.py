"""Themed renderers for the ``puma community status`` / ``channels`` views.

Presentation only. The community data types are imported under ``TYPE_CHECKING``
so the UI layer carries no runtime dependency on the community package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from puma.ui.themes import Theme

if TYPE_CHECKING:
    from puma.community.channels import Channel
    from puma.community.status import CommunityStatus

_CHANNELS_FOOTER = (
    "Channels are GitHub Actions workflows in pumacp/puma-community. "
    "See docs/publication_workflow.md."
)


def _auth_text(theme: Theme, status: CommunityStatus) -> Text:
    """Authenticated row value: success when logged in, muted otherwise."""
    if status.authenticated:
        if status.authenticated_as:
            return Text(f"✓ as @{status.authenticated_as}", style=theme.success)
        return Text("✓ authenticated", style=theme.success)
    return Text("✗ not logged in (run `puma auth login`)", style=theme.muted)


def _last_submission_text(theme: Theme, status: CommunityStatus) -> Text:
    """Last-submission row value: id (first 8) + timestamp, or muted dash."""
    if status.last_local_submission_id:
        short = status.last_local_submission_id[:8]
        ts = status.last_local_submission_timestamp
        label = f"{short} ({ts})" if ts else short
        return Text(label)
    return Text("—", style=theme.muted)


def _channels_text(theme: Theme, status: CommunityStatus) -> Text:
    """Configured-channels row value, colored by how many are configured."""
    configured = status.configured_channel_count
    total = status.total_channel_count
    if total and configured == total:
        style = theme.success
    elif configured > 0:
        style = theme.warning
    else:
        style = theme.muted
    return Text(f"{configured}/{total} channels configured", style=style)


def render_status_panel(theme: Theme, status: CommunityStatus) -> RenderableType:
    """Render a local PUMA Community status snapshot as a Field/Value panel."""
    table = Table(show_header=True, header_style=theme.title, box=None, pad_edge=False)
    table.add_column("Field", style=theme.accent)
    table.add_column("Value")
    table.add_row("Authenticated", _auth_text(theme, status))
    table.add_row("Last submission", _last_submission_text(theme, status))
    table.add_row("Channels", _channels_text(theme, status))
    return Panel(
        table,
        title=f"[{theme.title}]PUMA Community status[/]",
        border_style=theme.border,
        padding=(1, 2),
    )


def render_channels_table(theme: Theme, channels: list[Channel]) -> RenderableType:
    """Render the distribution channels with their local-configuration state."""
    table = Table(show_header=True, header_style=theme.title, box=None, pad_edge=False)
    table.add_column("Name", style=theme.accent)
    table.add_column("Kind")
    table.add_column("Target")
    table.add_column("Requires")
    table.add_column("Configured?", justify="center")
    for ch in channels:
        configured_cell = (
            Text("✓", style=theme.success)
            if ch.is_local_configured
            else Text("—", style=theme.muted)
        )
        table.add_row(
            ch.name,
            ch.kind,
            ch.target,
            ch.requires_secret or "—",
            configured_cell,
        )
    return Panel(
        Group(table, Text(""), Text(_CHANNELS_FOOTER, style=theme.muted)),
        title=f"[{theme.title}]PUMA Community channels[/]",
        border_style=theme.border,
        padding=(1, 2),
    )


__all__ = ["render_status_panel", "render_channels_table"]
