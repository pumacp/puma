"""TDD-first tests for ``puma validate-baseline`` (debt D1).

The command runs a canonical baseline spec and exits 0 if the resulting
``f1_macro`` is within ``--tolerance`` of ``--expected-f1``, non-zero
otherwise. Useful as a CI sanity check and reproducibility guard.

Tests fail until ``puma.cli.validate_baseline`` and the
``_run_baseline_for_validation`` helper land.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

import puma.cli as cli_module
from puma.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.unit
def test_validate_baseline_command_registered(runner: CliRunner) -> None:
    """The command is exposed and shows help text mentioning the baseline."""
    result = runner.invoke(app, ["validate-baseline", "--help"])
    assert result.exit_code == 0, result.stdout
    assert "baseline" in result.stdout.lower()


@pytest.mark.unit
def test_validate_baseline_passes_within_tolerance(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F1 within the tolerance window exits 0 with PASS marker."""
    monkeypatch.setattr(
        cli_module,
        "_run_baseline_for_validation",
        lambda spec, db_path, ollama_host: {"f1_macro": 0.5870},
    )
    result = runner.invoke(app, ["validate-baseline"])
    assert result.exit_code == 0, result.stdout
    assert "PASS" in result.stdout


@pytest.mark.unit
def test_validate_baseline_fails_outside_tolerance(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F1 outside the tolerance window exits non-zero with FAIL marker."""
    monkeypatch.setattr(
        cli_module,
        "_run_baseline_for_validation",
        lambda spec, db_path, ollama_host: {"f1_macro": 0.4500},
    )
    result = runner.invoke(app, ["validate-baseline"])
    assert result.exit_code != 0
    assert "FAIL" in result.stdout
