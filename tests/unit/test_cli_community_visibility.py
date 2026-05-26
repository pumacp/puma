"""CLI-level tests for `puma community status` / `channels` (S12.13 / E8)."""

from __future__ import annotations

import pytest
from rich.text import Text
from typer.testing import CliRunner

from puma.cli import app

runner = CliRunner()
_WIDE = {"COLUMNS": "200"}


@pytest.mark.unit
class TestCommunityVisibilityCli:
    def test_puma_community_status_exits_0(self):
        result = runner.invoke(app, ["community", "status"], env=_WIDE)
        assert result.exit_code == 0
        assert "PUMA Community status" in result.stdout

    def test_puma_community_channels_exits_0(self):
        result = runner.invoke(app, ["community", "channels"], env=_WIDE)
        assert result.exit_code == 0
        assert "Hugging Face" in result.stdout

    def test_community_commands_respect_theme(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        captured: dict[str, object] = {}

        def fake_render(theme, channels):  # test stub
            captured["theme"] = theme
            return Text("channels")

        monkeypatch.setattr("puma.ui.community_view.render_channels_table", fake_render)

        result = runner.invoke(app, ["--theme", "green", "community", "channels"], env=_WIDE)
        assert result.exit_code == 0
        assert captured["theme"].name == "green"

        captured.clear()
        result = runner.invoke(app, ["community", "channels"], env=_WIDE)
        assert result.exit_code == 0
        assert captured["theme"].name == "amber"
