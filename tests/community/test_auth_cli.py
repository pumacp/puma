"""Tests for the ``puma auth`` Typer sub-app."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from puma.community.auth_cli import auth_app

VALID_GITHUB_PAT = "ghp_" + "a" * 36
VALID_GITHUB_PREVIEW_TAIL = VALID_GITHUB_PAT[-4:]


@pytest.fixture
def runner(tmp_path: Path, monkeypatch) -> CliRunner:
    monkeypatch.setenv("PUMA_CONFIG_DIR", str(tmp_path / "puma-config"))
    return CliRunner()


def test_auth_status_when_nothing_configured(runner: CliRunner) -> None:
    result = runner.invoke(auth_app, ["status"])
    assert result.exit_code == 0
    assert "not configured" in result.stdout
    assert "github" in result.stdout


def test_auth_login_validates_format(runner: CliRunner) -> None:
    result = runner.invoke(auth_app, ["login", "github"], input="not-a-token\n")
    assert result.exit_code == 1
    assert "format" in result.stdout.lower()
    # The raw token must NOT appear in the diagnostics.
    assert "not-a-token" not in result.stdout


def test_auth_login_success_masks_token_in_output(runner: CliRunner) -> None:
    result = runner.invoke(auth_app, ["login", "github"], input=f"{VALID_GITHUB_PAT}\n")
    assert result.exit_code == 0, result.stdout
    assert "ghp_***" in result.stdout
    assert VALID_GITHUB_PREVIEW_TAIL in result.stdout
    # The full token MUST NOT appear in stdout.
    assert VALID_GITHUB_PAT not in result.stdout


def test_auth_status_shows_configured_after_login(runner: CliRunner) -> None:
    login = runner.invoke(auth_app, ["login", "github"], input=f"{VALID_GITHUB_PAT}\n")
    assert login.exit_code == 0
    status = runner.invoke(auth_app, ["status"])
    assert status.exit_code == 0
    assert "configured" in status.stdout
    assert "ghp_***" in status.stdout
    assert VALID_GITHUB_PAT not in status.stdout


def test_auth_logout_with_confirmation_removes_token(runner: CliRunner) -> None:
    runner.invoke(auth_app, ["login", "github"], input=f"{VALID_GITHUB_PAT}\n")
    result = runner.invoke(auth_app, ["logout", "github"], input="y\n")
    assert result.exit_code == 0
    assert "Removed" in result.stdout
    status = runner.invoke(auth_app, ["status"])
    assert "✗ not configured" in status.stdout


def test_auth_logout_without_confirmation_keeps_token(runner: CliRunner) -> None:
    runner.invoke(auth_app, ["login", "github"], input=f"{VALID_GITHUB_PAT}\n")
    result = runner.invoke(auth_app, ["logout", "github"], input="n\n")
    assert result.exit_code == 0
    assert "Aborted" in result.stdout
    status = runner.invoke(auth_app, ["status"])
    assert "✓ configured" in status.stdout


def test_auth_login_unknown_service_rejected(runner: CliRunner) -> None:
    result = runner.invoke(auth_app, ["login", "imaginary"])
    assert result.exit_code == 2
    assert "Unknown service" in result.stdout
