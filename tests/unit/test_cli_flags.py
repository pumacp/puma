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


_MINI_SPEC = "id: e5b_cli\nscenario: triage_jira\nmodels:\n  - qwen2.5:3b\nsample_size: 2\n"


def _invoke_run(monkeypatch, tmp_path, flags):
    """Invoke ``puma <flags> run <spec> --dry-run`` with Runner stubbed,
    returning (result, captured-Runner-kwargs)."""
    captured: dict[str, object] = {}

    class _FakeRunner:
        def __init__(self, spec, **kwargs):
            captured.update(kwargs)

        def run(self):
            return {"run_id": "fake", "n_predictions": 0, "metrics": {}}

    monkeypatch.setattr("puma.orchestrator.runner.Runner", _FakeRunner)
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(_MINI_SPEC, encoding="utf-8")
    result = runner.invoke(app, [*flags, "run", str(spec_path), "--dry-run"])
    return result, captured


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

    def test_quiet_flag_stored_in_ctx_obj(self, monkeypatch, tmp_path):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        result, captured = _invoke_run(monkeypatch, tmp_path, ["--quiet"])
        assert result.exit_code == 0
        assert captured.get("quiet") is True

    def test_quiet_and_no_banner_independent(self, monkeypatch, tmp_path):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        # --quiet alone does NOT suppress the banner.
        bare = runner.invoke(app, ["--quiet"])
        assert bare.exit_code == 0
        assert "_|_|" in bare.output
        # --no-banner alone does NOT enable quiet (progress stays on).
        result, captured = _invoke_run(monkeypatch, tmp_path, ["--no-banner"])
        assert result.exit_code == 0
        assert captured.get("quiet") is False

    def test_verbose_flag_stored_in_ctx_obj(self, monkeypatch):
        # --verbose flows through ctx.obj into the run command, which passes it
        # to print_error as show_traceback. Capture that to prove storage.
        monkeypatch.delenv("PUMA_THEME", raising=False)
        captured: dict[str, object] = {}

        def fake_print_error(console, theme, exc, *, show_traceback=False):
            captured["show_traceback"] = show_traceback

        monkeypatch.setattr("puma.ui.errors.print_error", fake_print_error)
        result = runner.invoke(app, ["--verbose", "run", "/no/such.yaml"])
        assert result.exit_code == 1
        assert captured.get("show_traceback") is True

    def test_verbose_independent_of_quiet_and_no_banner(self, monkeypatch):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        # --verbose alone does NOT suppress the banner.
        bare = runner.invoke(app, ["--verbose"])
        assert bare.exit_code == 0
        assert "_|_|" in bare.output
        # --no-banner + --quiet do NOT enable verbose (traceback stays hidden).
        captured: dict[str, object] = {}

        def fake_print_error(console, theme, exc, *, show_traceback=False):
            captured["show_traceback"] = show_traceback

        monkeypatch.setattr("puma.ui.errors.print_error", fake_print_error)
        result = runner.invoke(app, ["--no-banner", "--quiet", "run", "/no/such.yaml"])
        assert result.exit_code == 1
        assert captured.get("show_traceback") is False
