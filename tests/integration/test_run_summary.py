"""Integration tests for the end-of-run summary emission (US-12.12).

The k/l/m cases use ``dry_run`` (no Ollama) and force the terminal state to
exercise the emit/suppress decision deterministically. The n case runs real
triage inference (stable per D29) to prove the summary does not alter outputs.
"""

from __future__ import annotations

import os

import pytest

from puma.orchestrator.runner import Runner
from puma.orchestrator.runspec import RunSpec

_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def _force_terminal(monkeypatch, value: bool) -> None:
    monkeypatch.setattr("rich.console.Console.is_terminal", property(lambda self: value))


def _spec(run_id: str = "e5d_it", n: int = 3) -> RunSpec:
    return RunSpec(id=run_id, scenario="triage_jira", models=["qwen2.5:3b"], sample_size=n)


@pytest.mark.integration
class TestRunSummaryEmission:
    def test_run_emits_summary_when_tty(self, monkeypatch, capsys, tmp_path):
        _force_terminal(monkeypatch, True)
        Runner(_spec(), db_path=tmp_path / "a.db", dry_run=True, summary=True).run()
        assert "Run summary" in capsys.readouterr().err

    def test_run_suppresses_summary_when_no_summary_flag(self, monkeypatch, capsys, tmp_path):
        _force_terminal(monkeypatch, True)
        Runner(_spec(), db_path=tmp_path / "b.db", dry_run=True, summary=False).run()
        assert "Run summary" not in capsys.readouterr().err

    def test_run_suppresses_summary_when_non_tty(self, monkeypatch, capsys, tmp_path):
        _force_terminal(monkeypatch, False)
        Runner(_spec(), db_path=tmp_path / "c.db", dry_run=True, summary=True).run()
        assert "Run summary" not in capsys.readouterr().err


@pytest.mark.ollama
def test_run_summary_does_not_alter_predictions(monkeypatch, tmp_path):
    from puma.community.integrity import compute_predictions_hash
    from puma.storage.db import init_db, session_scope

    _force_terminal(monkeypatch, True)
    db = tmp_path / "determinism.db"
    spec = RunSpec(id="e5d_det", scenario="triage_jira", models=["qwen2.5:3b"], sample_size=5)

    # Warm the model so both compared runs share the same warm state.
    Runner(spec, db_path=db, ollama_host=_HOST, summary=False).run()

    with_summary = Runner(spec, db_path=db, ollama_host=_HOST, summary=True).run()
    without_summary = Runner(spec, db_path=db, ollama_host=_HOST, summary=False).run()

    init_db(db)
    with session_scope() as session:
        h_with = compute_predictions_hash(session=session, run_id=with_summary["run_id"])
        h_without = compute_predictions_hash(session=session, run_id=without_summary["run_id"])

    assert h_with == h_without, f"summary altered predictions: {h_with} != {h_without}"
