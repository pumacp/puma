"""Integration tests for the multi-model comparison dashboard layer.

Exercises ``get_multi_model_results`` against a purpose-built tmp SQLite DB
(predictions + instances + metrics + emissions) and verifies the view module
wires into the router. No Ollama / live inference involved — this is a pure
read-only consumer of persisted results.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from puma.dashboard.data import _MULTI_MODEL_COLUMNS, get_multi_model_results

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_PATH = REPO_ROOT / "src" / "puma" / "dashboard" / "app.py"


def _make_db(tmp_path: Path) -> Path:
    """Build a tiny results DB.

    triage_jira:
      - alpha:  one run, f1_macro=0.60, latency p50/p95/p99, co2_kg=0.001 (→ 1.0 g)
      - beta:   two runs with *identical* predictions → deterministic fingerprint
      - gamma:  two runs with *divergent* predictions → "varies (2)"
    estimation_tawos:
      - alpha:  one run with mae=3.5 (estimation-only metric)
    """
    db = tmp_path / "results.db"
    con = sqlite3.connect(db)
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
    con.execute("CREATE TABLE metrics (run_id TEXT, metric_name TEXT, value REAL, scope TEXT)")
    con.execute("CREATE TABLE emissions (run_id TEXT, co2_kg REAL)")

    # instances: 2 triage, 1 estimation
    con.executemany(
        "INSERT INTO instances VALUES (?, ?, ?, ?, ?)",
        [
            ("t1", "triage_jira", "t1", "bug A", "Critical"),
            ("t2", "triage_jira", "t2", "bug B", "Minor"),
            ("e1", "estimation_tawos", "e1", "story A", "5"),
        ],
    )

    def pred(run_id: str, inst: str, model: str, label: str) -> tuple:
        return (
            run_id,
            inst,
            model,
            "zero-shot",
            label,
            0.9,
            None,
            10.0,
            1,
            1,
            None,
            42,
            "h",
            label,
        )

    preds = [
        # alpha — single triage run
        pred("r_alpha", "t1", "alpha", "Critical"),
        pred("r_alpha", "t2", "alpha", "Minor"),
        # beta — two runs, identical predictions
        pred("r_beta1", "t1", "beta", "Critical"),
        pred("r_beta1", "t2", "beta", "Major"),
        pred("r_beta2", "t1", "beta", "Critical"),
        pred("r_beta2", "t2", "beta", "Major"),
        # gamma — two runs, divergent predictions
        pred("r_gamma1", "t1", "gamma", "Critical"),
        pred("r_gamma2", "t1", "gamma", "Minor"),
        # alpha — estimation run
        pred("r_alpha_est", "e1", "alpha", "5"),
    ]
    con.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", preds)

    con.executemany(
        "INSERT INTO metrics VALUES (?, ?, ?, 'global')",
        [
            ("r_alpha", "f1_macro", 0.60),
            ("r_alpha", "accuracy", 0.70),
            ("r_alpha", "latency.p50", 100.0),
            ("r_alpha", "latency.p95", 200.0),
            ("r_alpha", "latency.p99", 300.0),
            ("r_beta1", "f1_macro", 0.40),
            ("r_beta2", "f1_macro", 0.50),  # beta f1 mean = 0.45
            ("r_gamma1", "f1_macro", 0.30),
            ("r_alpha_est", "mae", 3.5),  # estimation-only
        ],
    )
    con.executemany(
        "INSERT INTO emissions VALUES (?, ?)",
        [("r_alpha", 0.001), ("r_beta1", 0.002), ("r_beta2", 0.002)],
    )
    con.commit()
    con.close()
    return db


@pytest.mark.integration
class TestGetMultiModelResults:
    def test_returns_expected_columns_and_index(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        df = get_multi_model_results("triage_jira", ["alpha", "beta"], db)

        assert df.index.name == "model"
        assert list(df.columns) == _MULTI_MODEL_COLUMNS
        assert list(df.index) == ["alpha", "beta"]  # order preserved
        assert df.loc["alpha", "f1_macro"] == pytest.approx(0.60)
        assert df.loc["alpha", "run_count"] == 1
        assert df.loc["beta", "f1_macro"] == pytest.approx(0.45)  # mean of two runs
        assert df.loc["beta", "run_count"] == 2

    def test_latency_and_carbon_populated(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        df = get_multi_model_results("triage_jira", ["alpha"], db)
        assert df.loc["alpha", "p50_latency_ms"] == pytest.approx(100.0)
        assert df.loc["alpha", "p95_latency_ms"] == pytest.approx(200.0)
        assert df.loc["alpha", "p99_latency_ms"] == pytest.approx(300.0)
        # co2_kg 0.001 → 1.0 gCO2eq
        assert df.loc["alpha", "total_carbon_gco2eq"] == pytest.approx(1.0)

    def test_mae_is_estimation_only(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        triage = get_multi_model_results("triage_jira", ["alpha"], db)
        estimation = get_multi_model_results("estimation_tawos", ["alpha"], db)
        assert pd.isna(triage.loc["alpha", "mae"])  # no mae on triage
        assert estimation.loc["alpha", "mae"] == pytest.approx(3.5)

    def test_missing_model_is_graceful(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        df = get_multi_model_results("triage_jira", ["alpha", "ghost:99b"], db)
        assert list(df.index) == ["alpha", "ghost:99b"]
        assert df.loc["ghost:99b", "run_count"] == 0
        # missing model has no fingerprint (None coerced to NaN by pandas in a mixed column)
        assert pd.isna(df.loc["ghost:99b", "predictions_summary_hash"])
        assert pd.isna(df.loc["ghost:99b", "f1_macro"])

    def test_deterministic_fingerprint(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        df = get_multi_model_results("triage_jira", ["beta", "gamma"], db)
        # beta: two runs, identical predictions → single 16-char hex fingerprint
        beta_hash = df.loc["beta", "predictions_summary_hash"]
        assert isinstance(beta_hash, str)
        assert len(beta_hash) == 16
        assert not beta_hash.startswith("varies")
        # gamma: two runs, divergent predictions → "varies (2)"
        assert df.loc["gamma", "predictions_summary_hash"] == "varies (2)"

    def test_stable_across_calls(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        first = get_multi_model_results("triage_jira", ["alpha", "beta", "gamma"], db)
        second = get_multi_model_results("triage_jira", ["alpha", "beta", "gamma"], db)
        pd.testing.assert_frame_equal(first, second)

    def test_missing_db_returns_empty_with_columns(self, tmp_path: Path) -> None:
        df = get_multi_model_results("triage_jira", ["alpha"], tmp_path / "nope.db")
        assert df.empty
        assert list(df.columns) == _MULTI_MODEL_COLUMNS
        assert df.index.name == "model"


@pytest.mark.integration
class TestMultiModelView:
    def test_view_module_exposes_render(self) -> None:
        from puma.dashboard.views import multi_model

        assert callable(multi_model.render)

    def test_view_registered_in_router(self) -> None:
        # app.py runs top-level streamlit calls, so check the source text (per smoke convention).
        src = APP_PATH.read_text(encoding="utf-8")
        assert "🔬 Multi-model" in src
        assert "multi_model" in src
