"""Determinism guard: themed progress display must not disturb run output.

Sprint 12 S12.7b (US-12.12). Runs the same small spec twice — once with the
progress display enabled, once with --quiet (disabled) — and asserts the
predictions are byte-identical (same canonical SHA-256). This proves the
progress code path (task creation/advance, themed columns) is non-disturbing.

A warmup run precedes the two compared runs so both execute in the same warm
Ollama state (PUMA is bit-exact warm; cold-vs-warm can drift slightly).
Marked ``ollama`` because it performs real inference.
"""

from __future__ import annotations

import os

import pytest

from puma.community.integrity import compute_predictions_hash
from puma.orchestrator.runner import Runner
from puma.orchestrator.runspec import RunSpec
from puma.storage.db import init_db, session_scope

_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def _predictions_hash(run_id: str, db_path) -> str:
    init_db(db_path)
    with session_scope() as session:
        return compute_predictions_hash(session=session, run_id=run_id)


@pytest.mark.ollama
def test_progress_does_not_change_predictions(tmp_path):
    db = tmp_path / "determinism.db"
    spec = RunSpec(
        id="e5b_determinism",
        scenario="triage_jira",
        models=["qwen2.5:3b"],
        sample_size=5,
    )

    # Warm the model so the two compared runs share the same warm state.
    Runner(spec, db_path=db, ollama_host=_HOST, quiet=True).run()

    with_progress = Runner(spec, db_path=db, ollama_host=_HOST, quiet=False).run()
    quiet = Runner(spec, db_path=db, ollama_host=_HOST, quiet=True).run()

    h_progress = _predictions_hash(with_progress["run_id"], db)
    h_quiet = _predictions_hash(quiet["run_id"], db)

    assert h_progress == h_quiet, (
        f"progress display disturbed run output: progress={h_progress} quiet={h_quiet}"
    )
