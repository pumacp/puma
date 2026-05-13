"""Tests for ``puma list-ollama-models`` (Anexo F § A.2.6)."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from puma.cli import app

SAMPLE_OLLAMA_LIST_OUTPUT = (
    "NAME             ID              SIZE      MODIFIED      \n"
    "qwen2.5:3b       abc123def456    1.9 GB    2 days ago    \n"
    "qwen2.5:1.5b     def456abc789    0.9 GB    5 days ago    \n"
    "gemma3:1b        789abcdef123    0.8 GB    1 week ago    \n"
)


@pytest.mark.unit
def test_list_ollama_models_help_exit_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["list-ollama-models", "--help"])
    assert result.exit_code == 0


@pytest.mark.unit
def test_list_ollama_models_parses_ollama_output() -> None:
    runner = CliRunner()
    completed = subprocess.CompletedProcess(
        args=["docker", "exec", "puma_ollama", "ollama", "list"],
        returncode=0,
        stdout=SAMPLE_OLLAMA_LIST_OUTPUT,
        stderr="",
    )
    with patch("subprocess.run", return_value=completed):
        result = runner.invoke(app, ["list-ollama-models"])
    assert result.exit_code == 0
    assert "qwen2.5:3b" in result.stdout
    assert "qwen2.5:1.5b" in result.stdout
    assert "gemma3:1b" in result.stdout


@pytest.mark.unit
def test_list_ollama_models_json_output() -> None:
    runner = CliRunner()
    completed = subprocess.CompletedProcess(
        args=["docker", "exec", "puma_ollama", "ollama", "list"],
        returncode=0,
        stdout=SAMPLE_OLLAMA_LIST_OUTPUT,
        stderr="",
    )
    with patch("subprocess.run", return_value=completed):
        result = runner.invoke(app, ["list-ollama-models", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 3
    names = {m["model_tag"] for m in data}
    assert names == {"qwen2.5:3b", "qwen2.5:1.5b", "gemma3:1b"}


@pytest.mark.unit
def test_list_ollama_models_ollama_not_responding_exit_one() -> None:
    runner = CliRunner()
    completed = subprocess.CompletedProcess(
        args=["docker", "exec", "puma_ollama", "ollama", "list"],
        returncode=1,
        stdout="",
        stderr="Error: ollama not running",
    )
    with patch("subprocess.run", return_value=completed):
        result = runner.invoke(app, ["list-ollama-models"])
    assert result.exit_code == 1
