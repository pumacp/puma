"""Tests for ``puma wilcoxon`` (Anexo F § A.2.2)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from puma.cli import app


def _make_paired_db(path: Path, n: int = 30) -> tuple[str, str]:
    """Two runs over the same instance set; deterministic correctness pattern."""
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
    run_a, run_b = "run_a_qwen", "run_b_gemma"
    for i in range(n):
        inst = f"I{i:03d}"
        con.execute(
            "INSERT INTO instances VALUES (?, 'triage', ?, '', ?)",
            (inst, inst, "Critical"),
        )
        # Run A: 80% correct
        pred_a = "Critical" if i % 5 != 0 else "Major"
        con.execute(
            "INSERT INTO predictions (run_id, instance_id, model, parsed_label) "
            "VALUES (?, ?, ?, ?)",
            (run_a, inst, "qwen2.5:3b", pred_a),
        )
        # Run B: 50% correct
        pred_b = "Critical" if i % 2 == 0 else "Minor"
        con.execute(
            "INSERT INTO predictions (run_id, instance_id, model, parsed_label) "
            "VALUES (?, ?, ?, ?)",
            (run_b, inst, "gemma3:1b", pred_b),
        )
    con.commit()
    con.close()
    return run_a, run_b


@pytest.mark.unit
def test_wilcoxon_help_exit_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["wilcoxon", "--help"])
    assert result.exit_code == 0


@pytest.mark.unit
def test_wilcoxon_missing_db_exit_one(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app, ["wilcoxon", "r1", "r2", "--db", str(tmp_path / "nope.db")]
    )
    assert result.exit_code == 1


@pytest.mark.unit
def test_wilcoxon_unknown_run_exit_one(tmp_path: Path) -> None:
    db = tmp_path / "tiny.db"
    _make_paired_db(db, n=30)
    runner = CliRunner()
    result = runner.invoke(
        app, ["wilcoxon", "does_not_exist", "run_b_gemma", "--db", str(db)]
    )
    assert result.exit_code == 1


@pytest.mark.unit
def test_wilcoxon_too_few_pairs_exit_two(tmp_path: Path) -> None:
    """With fewer than 10 paired instances the command must refuse the test."""
    db = tmp_path / "tiny.db"
    _make_paired_db(db, n=5)
    runner = CliRunner()
    result = runner.invoke(
        app, ["wilcoxon", "run_a_qwen", "run_b_gemma", "--db", str(db)]
    )
    assert result.exit_code == 2


@pytest.mark.unit
def test_wilcoxon_happy_path_emits_p_value(tmp_path: Path) -> None:
    db = tmp_path / "tiny.db"
    run_a, run_b = _make_paired_db(db, n=30)
    runner = CliRunner()
    result = runner.invoke(app, ["wilcoxon", run_a, run_b, "--db", str(db)])
    assert result.exit_code == 0
    out = result.stdout.lower()
    assert "p" in out and ("value" in out or "=" in out)


@pytest.mark.unit
def test_wilcoxon_writes_output_file(tmp_path: Path) -> None:
    db = tmp_path / "tiny.db"
    run_a, run_b = _make_paired_db(db, n=30)
    out = tmp_path / "result.md"
    runner = CliRunner()
    result = runner.invoke(
        app, ["wilcoxon", run_a, run_b, "--db", str(db), "--output", str(out)]
    )
    assert result.exit_code == 0
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert run_a in body and run_b in body
