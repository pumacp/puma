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


@pytest.mark.unit
def test_validate_baseline_with_expected_mae_pass(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MAE within the tolerance window exits 0 with PASS and the mae metric name."""
    monkeypatch.setattr(
        cli_module,
        "_run_baseline_for_validation",
        lambda spec, db_path, ollama_host: {"mae": 2.91},
    )
    result = runner.invoke(
        app,
        ["validate-baseline", "--expected-mae", "2.91", "--tolerance", "0.10"],
    )
    assert result.exit_code == 0, result.stdout
    assert "PASS" in result.stdout
    assert "mae" in result.stdout


@pytest.mark.unit
def test_validate_baseline_with_expected_mae_fail_outside_tolerance(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MAE outside the tolerance window exits non-zero with FAIL marker."""
    monkeypatch.setattr(
        cli_module,
        "_run_baseline_for_validation",
        lambda spec, db_path, ollama_host: {"mae": 4.50},
    )
    result = runner.invoke(
        app,
        ["validate-baseline", "--expected-mae", "2.91", "--tolerance", "0.10"],
    )
    assert result.exit_code != 0
    assert "FAIL" in result.stdout


@pytest.mark.unit
def test_validate_baseline_mutually_exclusive_flags_exits_2(runner: CliRunner) -> None:
    """Providing both --expected-f1 and --expected-mae exits 2 without running the spec."""
    result = runner.invoke(
        app,
        [
            "validate-baseline",
            "--expected-f1",
            "0.5867",
            "--expected-mae",
            "2.91",
        ],
    )
    assert result.exit_code == 2
    assert "mutually exclusive" in result.stdout.lower() or result.stderr_bytes


@pytest.mark.unit
def test_validate_baseline_no_metric_in_results_exits_2(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the run completes but the requested metric is missing, exit 2 with an error."""
    monkeypatch.setattr(
        cli_module,
        "_run_baseline_for_validation",
        lambda spec, db_path, ollama_host: {"f1_macro": 0.5867},  # missing 'mae'
    )
    result = runner.invoke(app, ["validate-baseline", "--expected-mae", "2.91"])
    assert result.exit_code == 2


@pytest.mark.unit
def test_validate_baseline_mae_path_uses_estimation_spec_by_default(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When --expected-mae is given without --spec, the canonical estimation
    spec is selected automatically (regression guard against accidental
    coupling of the MAE path to the triage spec)."""
    captured: dict[str, str] = {}

    def _capture(spec: str, db_path: str, ollama_host: str) -> dict[str, float]:
        captured["spec"] = spec
        return {"mae": 2.91}

    monkeypatch.setattr(cli_module, "_run_baseline_for_validation", _capture)
    result = runner.invoke(
        app,
        ["validate-baseline", "--expected-mae", "2.91", "--tolerance", "0.10"],
    )
    assert result.exit_code == 0, result.stdout
    assert captured["spec"] == "specs/runs/baseline_estimation_canonical.yaml"
