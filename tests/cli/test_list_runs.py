"""Tests for ``puma list-runs`` (Anexo F § A.2.5)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from puma.cli import app


def _make_db(path: Path, n_runs: int = 3) -> None:
    """Create a tiny DB with ``runs`` + ``metrics`` for list-runs tests."""
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE runs ("
        "run_id TEXT PRIMARY KEY, spec_hash TEXT, profile TEXT, "
        "started_at TEXT, finished_at TEXT, status TEXT)"
    )
    con.execute(
        "CREATE TABLE metrics ("
        "metric_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, "
        "scope TEXT, model TEXT, strategy TEXT, metric_name TEXT, "
        "value REAL, subgroup TEXT, computed_at TEXT)"
    )
    for i in range(n_runs):
        run_id = f"r{i}_triage_qwen2.5_3b_2026-05-{10 + i:02d}"
        started = f"2026-05-{10 + i:02d}T10:00:00"
        con.execute(
            "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, "h", "gpu-entry", started, started, "done"),
        )
        con.execute(
            "INSERT INTO metrics (run_id, scope, model, strategy, metric_name, value) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, "global", None, None, "f1_macro", 0.58 + i * 0.01),
        )
    con.commit()
    con.close()


@pytest.mark.unit
def test_list_runs_help_exit_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["list-runs", "--help"])
    assert result.exit_code == 0
    assert "list-runs" in result.stdout.lower() or "scenario" in result.stdout.lower()


@pytest.mark.unit
def test_list_runs_empty_db_exit_code_2(tmp_path: Path) -> None:
    """With no rows, the command exits 2 (informative empty)."""
    db = tmp_path / "empty.db"
    _make_db(db, n_runs=0)
    runner = CliRunner()
    result = runner.invoke(app, ["list-runs", "--db", str(db)])
    assert result.exit_code == 2


@pytest.mark.unit
def test_list_runs_missing_db_exit_code_1(tmp_path: Path) -> None:
    """When the DB file does not exist, exit 1."""
    runner = CliRunner()
    result = runner.invoke(app, ["list-runs", "--db", str(tmp_path / "nope.db")])
    assert result.exit_code == 1


@pytest.mark.unit
def test_list_runs_default_lists_all(tmp_path: Path) -> None:
    db = tmp_path / "tiny.db"
    _make_db(db, n_runs=3)
    runner = CliRunner()
    result = runner.invoke(app, ["list-runs", "--db", str(db)])
    assert result.exit_code == 0
    # All three runs should appear by their run_id prefix
    for i in range(3):
        assert f"r{i}_triage" in result.stdout


@pytest.mark.unit
def test_list_runs_last_n_limits_output(tmp_path: Path) -> None:
    db = tmp_path / "tiny.db"
    _make_db(db, n_runs=3)
    runner = CliRunner()
    result = runner.invoke(app, ["list-runs", "--db", str(db), "--last-n", "1"])
    assert result.exit_code == 0
    # Most recent run only (r2)
    assert "r2_triage" in result.stdout
    assert "r0_triage" not in result.stdout


@pytest.mark.unit
def test_list_runs_json_output_valid(tmp_path: Path) -> None:
    import json

    db = tmp_path / "tiny.db"
    _make_db(db, n_runs=2)
    runner = CliRunner()
    result = runner.invoke(app, ["list-runs", "--db", str(db), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 2
    assert {"run_id", "started_at"}.issubset(data[0].keys())
