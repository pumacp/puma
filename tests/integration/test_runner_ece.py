"""Integration tests for ECE pipeline wiring in the Runner (Sprint 3).

When the run spec sets ``inference.logprobs=true``, the runner must:

1. Capture ``result.logprobs`` from the Ollama client.
2. Compute per-prediction confidence via
   ``class_confidence_from_logprobs`` against the scenario's label tokens.
3. Persist the raw logprobs (as JSON) and the confidence in the
   ``predictions`` table.
4. Aggregate the per-prediction confidences and correctness indicators
   into an Expected Calibration Error (ECE) and persist it in the
   ``metrics`` payload.

When ``inference.logprobs=false`` (the v2.0.0 default), nothing changes —
no ECE in the payload, ``predictions.logprobs_json`` and
``predictions.confidence`` remain NULL.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from puma.orchestrator.runner import Runner
from puma.orchestrator.runspec import RunSpec


def _spec(*, logprobs: bool, sample_size: int = 5) -> RunSpec:
    return RunSpec(
        id="test_ece_pipeline",
        description="S3.1.b integration test",
        scenario="triage_jira",
        sample_size=sample_size,
        models=["qwen2.5:1.5b"],
        adaptation={"strategy": ["contextual-anchoring"]},
        inference={
            "temperature": 0.0,
            "seed": 42,
            "max_tokens": 32,
            "logprobs": logprobs,
            "top_logprobs": 5 if logprobs else 0,
        },
        sustainability={"codecarbon": False},
    )


@pytest.mark.integration
@pytest.mark.ollama
def test_ece_persisted_in_metrics_when_logprobs_enabled(tmp_path) -> None:
    """End-to-end with logprobs=True: ECE in [0,1] persisted in metrics."""
    spec = _spec(logprobs=True)
    db = tmp_path / "test.db"
    summary = Runner(spec, db_path=db, ollama_host="http://puma_ollama:11434").run()

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(
        "SELECT metric_name, value FROM metrics WHERE run_id = ?",
        (summary["run_id"],),
    )
    rows = dict(cur.fetchall())
    assert rows, "no metric rows persisted"

    assert "ece" in rows, (
        f"ECE missing from metrics when logprobs=True; got metric names: {sorted(rows.keys())}"
    )
    ece = rows["ece"]
    assert 0.0 <= ece <= 1.0, f"ECE out of [0,1]: {ece}"
    assert rows.get("n_with_confidence", 0) >= 1


@pytest.mark.integration
@pytest.mark.ollama
def test_logprobs_json_persisted_per_prediction(tmp_path) -> None:
    """At least one prediction row must carry logprobs_json + confidence."""
    spec = _spec(logprobs=True)
    db = tmp_path / "test.db"
    summary = Runner(spec, db_path=db, ollama_host="http://puma_ollama:11434").run()

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(
        """SELECT logprobs_json, confidence, parsed_label
           FROM predictions WHERE run_id = ?""",
        (summary["run_id"],),
    )
    rows = cur.fetchall()
    assert rows, "no prediction rows persisted"

    with_logprobs = [r for r in rows if r[0] is not None]
    assert with_logprobs, "no prediction row carries logprobs_json when logprobs=True"
    # Each populated row must have parseable JSON and a confidence in [0,1].
    for logprobs_json, confidence, parsed_label in with_logprobs:
        data = json.loads(logprobs_json)
        assert isinstance(data, list)
        assert data, "logprobs_json must not be an empty list"
        first = data[0]
        assert "token" in first and "logprob" in first and "top_logprobs" in first
        if confidence is not None:
            assert 0.0 <= confidence <= 1.0, (
                f"confidence out of [0,1]: {confidence} for label={parsed_label}"
            )


@pytest.mark.integration
@pytest.mark.ollama
def test_ece_absent_and_logprobs_null_when_disabled(tmp_path) -> None:
    """logprobs=False is the v2.0.0 default; ECE must be absent and
    predictions.logprobs_json / .confidence remain NULL. Regression guard."""
    spec = _spec(logprobs=False)
    db = tmp_path / "test.db"
    summary = Runner(spec, db_path=db, ollama_host="http://puma_ollama:11434").run()

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    cur.execute(
        "SELECT metric_name FROM metrics WHERE run_id = ?",
        (summary["run_id"],),
    )
    names = {r[0] for r in cur.fetchall()}
    assert "ece" not in names, (
        f"ECE must not be persisted when logprobs=False; got metric names: {sorted(names)}"
    )

    cur.execute(
        """SELECT logprobs_json, confidence FROM predictions
           WHERE run_id = ?""",
        (summary["run_id"],),
    )
    for logprobs_json, confidence in cur.fetchall():
        assert logprobs_json is None, "logprobs_json must be NULL when logprobs=False"
        assert confidence is None, "confidence must be NULL when logprobs=False"
