"""Unit tests for CLI error routing, themed panels, and exit codes (US-12.12)."""

from __future__ import annotations

import contextlib

import pytest
from typer.testing import CliRunner

import puma.cli as cli
from puma.cli import app

runner = CliRunner()


def _all_output(result) -> str:
    text = result.output
    with contextlib.suppress(ValueError, AttributeError):
        text += result.stderr
    return text


@pytest.mark.unit
class TestCliErrors:
    def test_invalid_theme_exits_2_with_themed_panel(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        result = runner.invoke(app, ["--theme", "purple"])
        assert result.exit_code == 2
        assert "Unknown theme" in _all_output(result)

    def test_missing_spec_file_exits_1_with_themed_panel(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        result = runner.invoke(app, ["run", "/no/such.yaml"])
        assert result.exit_code == 1
        assert "FileNotFoundError" in _all_output(result)

    def test_verbose_includes_traceback(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        result = runner.invoke(app, ["-v", "run", "/no/such.yaml"])
        assert result.exit_code == 1
        assert "Traceback" in _all_output(result)

    def test_default_hides_traceback(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        result = runner.invoke(app, ["run", "/no/such.yaml"])
        assert result.exit_code == 1
        assert "Traceback" not in _all_output(result)

    def test_keyboard_interrupt_exits_130(self, monkeypatch, capsys):
        def boom(*args, **kwargs):
            raise KeyboardInterrupt

        monkeypatch.setattr(cli, "app", boom)
        with pytest.raises(SystemExit) as exit_info:
            cli.main()
        assert exit_info.value.code == 130
        assert "Interrupted" in capsys.readouterr().err
