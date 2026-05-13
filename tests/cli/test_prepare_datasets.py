"""Tests for ``puma prepare-datasets`` (Anexo F § A.2.1)."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from puma.cli import app


@pytest.mark.unit
def test_prepare_datasets_help_exit_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["prepare-datasets", "--help"])
    assert result.exit_code == 0


@pytest.mark.unit
def test_prepare_datasets_default_invokes_script() -> None:
    """Default invocation runs scripts/prepare_datasets.py via subprocess."""
    runner = CliRunner()
    completed = subprocess.CompletedProcess(
        args=["python", "scripts/prepare_datasets.py"], returncode=0, stdout="ok", stderr=""
    )
    with patch("subprocess.run", return_value=completed) as run_mock:
        result = runner.invoke(app, ["prepare-datasets"])
    assert result.exit_code == 0
    # subprocess.run must have been called
    assert run_mock.called
    args = run_mock.call_args[0][0]
    assert any("prepare_datasets.py" in str(a) for a in args)


@pytest.mark.unit
def test_prepare_datasets_script_failure_propagates_exit_code() -> None:
    """If the script exits with non-zero, the CLI exits 1 (network/source error)."""
    runner = CliRunner()
    completed = subprocess.CompletedProcess(
        args=["python", "scripts/prepare_datasets.py"], returncode=1, stdout="", stderr="boom"
    )
    with patch("subprocess.run", return_value=completed):
        result = runner.invoke(app, ["prepare-datasets"])
    assert result.exit_code == 1
