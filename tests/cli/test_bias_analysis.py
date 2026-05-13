"""Tests for ``puma bias-analysis`` (Anexo F § A.2.3)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from puma.cli import app


def _make_perturbed_db(path: Path) -> None:
    """Three conditions per model (baseline + male prefix + female prefix), 4 instances."""
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE predictions (run_id TEXT, instance_id TEXT, model TEXT, "
        "strategy TEXT, parsed_label TEXT, confidence REAL, logprobs_json TEXT, "
        "latency_ms REAL, tokens_in INT, tokens_out INT, perturbation TEXT, "
        "seed INT, prompt_hash TEXT, raw_response TEXT)"
    )
    con.execute(
        "CREATE TABLE instances (instance_id TEXT, dataset TEXT, source_id TEXT, "
        "input_text TEXT, gold_label TEXT)"
    )
    for i in range(4):
        inst = f"I{i}"
        con.execute(
            "INSERT INTO instances VALUES (?, 'triage_jira', ?, '', 'Critical')",
            (inst, inst),
        )
    # Baseline run: all correct
    for i in range(4):
        con.execute(
            "INSERT INTO predictions (run_id, instance_id, model, parsed_label, perturbation) "
            "VALUES ('r_base', ?, 'qwen2.5:3b', 'Critical', NULL)",
            (f"I{i}",),
        )
    # Male prefix: 1 wrong
    for i in range(4):
        label = "Critical" if i != 0 else "Major"
        con.execute(
            "INSERT INTO predictions (run_id, instance_id, model, parsed_label, perturbation) "
            "VALUES ('r_male', ?, 'qwen2.5:3b', ?, 'gender_swap_prefix_male')",
            (f"I{i}", label),
        )
    # Female prefix: 2 wrong
    for i in range(4):
        label = "Critical" if i > 1 else "Minor"
        con.execute(
            "INSERT INTO predictions (run_id, instance_id, model, parsed_label, perturbation) "
            "VALUES ('r_female', ?, 'qwen2.5:3b', ?, 'gender_swap_prefix_female')",
            (f"I{i}", label),
        )
    con.commit()
    con.close()


@pytest.mark.unit
def test_bias_analysis_help_exit_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["bias-analysis", "--help"])
    assert result.exit_code == 0


@pytest.mark.unit
def test_bias_analysis_no_perturbed_runs_exit_one(tmp_path: Path) -> None:
    db = tmp_path / "empty.db"
    sqlite3.connect(db).close()
    runner = CliRunner()
    result = runner.invoke(app, ["bias-analysis", "--db", str(db)])
    assert result.exit_code == 1


@pytest.mark.unit
def test_bias_analysis_writes_output(tmp_path: Path) -> None:
    db = tmp_path / "tiny.db"
    _make_perturbed_db(db)
    out = tmp_path / "bias.md"
    runner = CliRunner()
    result = runner.invoke(app, ["bias-analysis", "--db", str(db), "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "qwen2.5:3b" in body
    assert "gender_swap_prefix_male" in body or "gender_swap_prefix_female" in body
