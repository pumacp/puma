"""Unit tests for puma.ui.community_view (S12.13 / E8)."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console, Group

from puma.community.channels import Channel
from puma.community.status import CommunityStatus
from puma.ui.community_view import render_channels_table, render_status_panel
from puma.ui.themes import get_theme


def _status(**kw: object) -> CommunityStatus:
    base: dict[str, object] = {
        "authenticated": True,
        "authenticated_as": None,
        "last_local_submission_id": None,
        "last_local_submission_timestamp": None,
        "configured_channel_count": 0,
        "total_channel_count": 5,
    }
    base.update(kw)
    return CommunityStatus(**base)  # type: ignore[arg-type]


def _channel(configured: bool) -> Channel:
    return Channel(
        name="Hugging Face Datasets",
        kind="mirror",
        target="datasets/pumacp/puma-community",
        workflow_file="mirror-huggingface.yml",
        docs_url="https://example.test/#channels",
        requires_secret="HF_TOKEN",
        is_local_configured=configured,
    )


@pytest.mark.unit
class TestStatusPanel:
    def test_render_status_panel_amber_uses_orange3_for_authenticated(self):
        theme = get_theme("amber")
        panel = render_status_panel(theme, _status(authenticated=True))
        # The Field column carries the amber accent (orange3).
        assert panel.renderable.columns[0].style == "orange3"
        # The authenticated value cell is styled with the success color.
        auth_cell = panel.renderable.columns[1]._cells[0]
        assert auth_cell.style == theme.success

    def test_render_status_panel_shows_dash_for_unknown_fields(self):
        theme = get_theme("amber")
        panel = render_status_panel(theme, _status(last_local_submission_id=None))
        out = StringIO()
        Console(file=out, force_terminal=False, width=100).print(panel)
        assert "—" in out.getvalue()


@pytest.mark.unit
class TestChannelsTable:
    @staticmethod
    def _table(panel):
        # The panel wraps Group(table, "", footer); the table is the first member.
        assert isinstance(panel.renderable, Group)
        return panel.renderable.renderables[0]

    def test_render_channels_table_marks_configured_with_success_color(self):
        theme = get_theme("amber")
        panel = render_channels_table(theme, [_channel(True)])
        cell = self._table(panel).columns[-1]._cells[0]
        assert cell.plain == "✓"
        assert cell.style == theme.success

    def test_render_channels_table_marks_unconfigured_with_muted(self):
        theme = get_theme("amber")
        panel = render_channels_table(theme, [_channel(False)])
        cell = self._table(panel).columns[-1]._cells[0]
        assert cell.plain == "—"
        assert cell.style == theme.muted
