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

    def test_no_summary_flag_stored_in_ctx_obj(self, monkeypatch, tmp_path):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        result, captured = _invoke_run(monkeypatch, tmp_path, ["--no-summary"])
        assert result.exit_code == 0
        assert captured.get("summary") is False

    def test_no_summary_independent_of_quiet_and_no_banner(self, monkeypatch, tmp_path):
        monkeypatch.delenv("PUMA_THEME", raising=False)
        # default: summary on, quiet off.
        _, cap_default = _invoke_run(monkeypatch, tmp_path, [])
        assert cap_default.get("summary") is True
        assert cap_default.get("quiet") is False
        # --no-summary alone: summary off, quiet still off (independent).
        _, cap_ns = _invoke_run(monkeypatch, tmp_path, ["--no-summary"])
        assert cap_ns.get("summary") is False
        assert cap_ns.get("quiet") is False
        # --quiet alone: quiet on, summary still on (independent).
        _, cap_q = _invoke_run(monkeypatch, tmp_path, ["--quiet"])
        assert cap_q.get("quiet") is True
        assert cap_q.get("summary") is True
        # --no-summary alone does NOT suppress the banner.
        bare = runner.invoke(app, ["--no-summary"])
        assert "_|_|" in bare.output


def _fake_version(value: str):
    """Return an ``importlib.metadata.version`` stand-in that records the queried name."""
    seen: list[str] = []

    def fake(name: str) -> str:
        seen.append(name)
        return value

    return fake, seen


@pytest.mark.unit
class TestVersionFlag:
    def test_version_prints_distribution_name_and_version(self, monkeypatch):
        fake, seen = _fake_version("9.9.9")
        monkeypatch.setattr("puma.cli.version", fake)
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "puma-cp 9.9.9"
        # The PyPI distribution is ``puma-cp``; the import package name would raise.
        assert seen == ["puma-cp"]

    def test_version_falls_back_when_distribution_is_not_installed(self, monkeypatch):
        from importlib.metadata import PackageNotFoundError

        def missing(name: str) -> str:
            raise PackageNotFoundError(name)

        monkeypatch.setattr("puma.cli.version", missing)
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "puma-cp 0.0.0-unknown"

    def test_version_is_eager_and_short_circuits_the_subcommand(self, monkeypatch):
        fake, _ = _fake_version("9.9.9")
        monkeypatch.setattr("puma.cli.version", fake)
        # ``run`` requires a spec argument; the eager flag must win before that is checked.
        result = runner.invoke(app, ["--version", "run"])
        assert result.exit_code == 0
        assert "puma-cp 9.9.9" in result.stdout
        assert "Missing argument" not in _all_output(result)

    def test_version_does_not_print_the_banner(self, monkeypatch):
        fake, _ = _fake_version("9.9.9")
        monkeypatch.setattr("puma.cli.version", fake)
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "Local LLM benchmarks" not in result.stdout

    def test_version_is_listed_in_root_help(self):
        result = runner.invoke(app, ["--no-banner", "--help"], env={"COLUMNS": "200"})
        assert result.exit_code == 0
        assert "--version" in result.stdout
