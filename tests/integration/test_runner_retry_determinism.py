"""Integration test: retries preserve output determinism (US-12.15).

Runs a small triage spec twice through the Runner with a mocked Ollama client:
once where every call succeeds, once where the first call raises a single
transient timeout (so the deterministic retry fires and recovers). The canonical
predictions JSONL must be byte-identical, proving the recovery path does not
perturb which samples are processed or their outputs.
"""

from __future__ import annotations

import httpx
import pytest

from puma.community.integrity import export_predictions_jsonl
from puma.orchestrator.runner import Runner
from puma.orchestrator.runspec import RunSpec
from puma.runtime.client import GenerationResult
from puma.storage.db import session_scope


def _spec() -> RunSpec:
    return RunSpec(
        id="retry_determinism_v1",
        description="retry determinism integration test",
        scenario="triage_jira",
        sample_size=4,
        models=["qwen2.5:3b"],
        adaptation={"strategy": ["zero-shot"]},
        inference={"temperature": 0.0, "seed": 42},
        metrics=["f1_macro"],
    )


class _FakeClient:
    def __init__(self, *, fail_first: int = 0):
        self.calls = 0
        self.fail_first = fail_first

    def generate_sync(self, **kwargs) -> GenerationResult:
        self.calls += 1
        if self.calls <= self.fail_first:
            raise httpx.TimeoutException("forced transient")
        return GenerationResult(
            model=kwargs["model"],
            response="Bug",
            logprobs=[],
            total_duration_ns=0,
            load_duration_ns=0,
            prompt_eval_count=1,
            eval_count=1,
            eval_duration_ns=0,
            raw={},
        )


def _run_and_export(tmp_path, monkeypatch, *, fail_first: int, tag: str) -> tuple[bytes, int]:
    fake = _FakeClient(fail_first=fail_first)
    monkeypatch.setattr("puma.runtime.client.client_for_model", lambda *a, **k: fake)
    runner = Runner(_spec(), db_path=tmp_path / f"{tag}.db")
    runner.run()
    target = tmp_path / f"{tag}.predictions.jsonl"
    with session_scope() as session:
        export_predictions_jsonl(session=session, run_id=runner.run_id, target=target)
    return target.read_bytes(), fake.calls


@pytest.mark.integration
def test_run_byte_equality_with_and_without_retries_fired(tmp_path, monkeypatch):
    # No real backoff waits during the test.
    monkeypatch.setattr("puma.runtime.retry.time.sleep", lambda s: None)

    clean_bytes, clean_calls = _run_and_export(tmp_path, monkeypatch, fail_first=0, tag="clean")
    retry_bytes, retry_calls = _run_and_export(tmp_path, monkeypatch, fail_first=1, tag="retry")

    # The canonical predictions JSONL is byte-identical: retry recovered to the
    # same output without changing the sample set or order.
    assert retry_bytes == clean_bytes
    assert clean_bytes  # non-empty (predictions were produced)
    # The retry actually fired: exactly one extra inference call in the retry run.
    assert retry_calls == clean_calls + 1
