"""Unit tests for the CLI banner/theme flags (US-12.12)."""

from __future__ import annotations

import contextlib

import pytest
from typer.testing import CliRunner

from puma.cli import app

runner = CliRunner()


def _all_output(result) -> str:
    """Return stdout plus stderr regardless of the CliRunner capture mode."""
    text = result.output
    # Older click mixes stderr into output (accessing .stderr then raises);
    # newer click captures it separately. Tolerate both.
    with contextlib.suppress(ValueError, AttributeError):
        text += result.stderr
    return text


@pytest.mark.unit
class TestCliFlags:
    def test_bare_puma_prints_banner(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "_|_|" in result.output  # figlet block glyphs

    def test_no_banner_flag_suppresses(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        result = runner.invoke(app, ["--no-banner"])
        assert result.exit_code == 0
        assert "_|_|" not in result.output

    def test_theme_green_applied(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        captured: dict[str, object] = {}

        def fake_print_banner(console, theme=None):
            captured["theme"] = theme

        monkeypatch.setattr("puma.ui.banner.print_banner", fake_print_banner)
        result = runner.invoke(app, ["--theme", "green"])
        assert result.exit_code == 0
        assert captured["theme"] is not None
        assert captured["theme"].border == "green3"

    def test_invalid_theme_exits_2(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        result = runner.invoke(app, ["--theme", "purple"])
        assert result.exit_code == 2
        assert "Unknown theme" in _all_output(result)
