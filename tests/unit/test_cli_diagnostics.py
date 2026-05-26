"""Unit tests for the CLI diagnostic subcommands (US-12.13)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from puma.cli import app
from puma.diagnostics.checks import CheckResult

runner = CliRunner()


def _patch_checks(monkeypatch, statuses: list[str]) -> None:
    results = [CheckResult(f"check{i}", status, "detail") for i, status in enumerate(statuses)]
    monkeypatch.setattr("puma.diagnostics.checks.run_all_checks", lambda **kwargs: results)


@pytest.mark.unit
class TestCliDiagnostics:
    def test_doctor_exits_0_when_all_ok(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        _patch_checks(monkeypatch, ["ok", "ok"])
        assert runner.invoke(app, ["doctor"]).exit_code == 0

    def test_doctor_exits_1_when_any_fail(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        _patch_checks(monkeypatch, ["ok", "fail"])
        assert runner.invoke(app, ["doctor"]).exit_code == 1

    def test_doctor_exits_0_when_only_warnings(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        _patch_checks(monkeypatch, ["ok", "warn"])
        assert runner.invoke(app, ["doctor"]).exit_code == 0

    def test_doctor_respects_theme(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        _patch_checks(monkeypatch, ["ok"])
        captured: dict[str, object] = {}

        def fake_render(theme, results):
            captured["theme"] = theme
            return "rendered"

        monkeypatch.setattr("puma.ui.diagnostics_view.render_doctor_table", fake_render)
        result = runner.invoke(app, ["--theme", "green", "doctor"])
        assert result.exit_code == 0
        assert captured["theme"].name == "green"

    def test_doctor_respects_no_banner(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        _patch_checks(monkeypatch, ["ok"])
        result = runner.invoke(app, ["--no-banner", "doctor"])
        assert result.exit_code == 0
        assert "_|_|" not in result.output

    def test_env_exits_0_always(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        assert runner.invoke(app, ["env"]).exit_code == 0

    def test_env_includes_version_and_platform(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        result = runner.invoke(app, ["env"])
        assert result.exit_code == 0
        assert "PUMA version" in result.output
        assert "Platform" in result.output
