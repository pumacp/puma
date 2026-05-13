"""Tests for ``puma generate-plots`` (Anexo F § A.2.4)."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from puma.cli import app


@pytest.mark.unit
def test_generate_plots_help_exit_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["generate-plots", "--help"])
    assert result.exit_code == 0


@pytest.mark.unit
def test_generate_plots_phase_b_invokes_script() -> None:
    runner = CliRunner()
    completed = subprocess.CompletedProcess(
        args=["python", "scripts/generate_phase_b_plots.py"],
        returncode=0,
        stdout="ok",
        stderr="",
    )
    with patch("subprocess.run", return_value=completed) as run_mock:
        result = runner.invoke(app, ["generate-plots", "--source", "phase_b"])
    assert result.exit_code == 0
    assert run_mock.called


@pytest.mark.unit
def test_generate_plots_phase_b_script_failure_exit_one() -> None:
    runner = CliRunner()
    completed = subprocess.CompletedProcess(
        args=["python", "scripts/generate_phase_b_plots.py"],
        returncode=1,
        stdout="",
        stderr="no rows",
    )
    with patch("subprocess.run", return_value=completed):
        result = runner.invoke(app, ["generate-plots", "--source", "phase_b"])
    assert result.exit_code == 1


@pytest.mark.unit
def test_generate_plots_unsupported_source_exits_nonzero() -> None:
    """bias_eval / multi_seed plotting is documented but not yet implemented."""
    runner = CliRunner()
    result = runner.invoke(app, ["generate-plots", "--source", "bias_eval"])
    # Either 0 with informative message, or 2 with "not implemented".
    # Implementation choice: exit 2 to signal unsupported source.
    assert result.exit_code == 2


@pytest.mark.unit
def test_generate_plots_invalid_source_rejected() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["generate-plots", "--source", "totally_made_up"])
    # Typer should reject the value before our code runs; non-zero exit either way.
    assert result.exit_code != 0
