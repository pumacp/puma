"""Unit tests for the Runner's use of the retry policy (US-12.15)."""

from __future__ import annotations

import httpx
import pytest

from puma.orchestrator.runner import Runner
from puma.orchestrator.runspec import RunSpec
from puma.runtime.client import GenerationResult
from puma.runtime.retry import DEFAULT_POLICY, RetryPolicy


def _spec(**overrides) -> RunSpec:
    base = {
        "id": "retry_test_v1",
        "description": "retry unit test",
        "scenario": "triage_jira",
        "sample_size": 2,
        "models": ["qwen2.5:3b"],
        "adaptation": {"strategy": ["zero-shot"]},
        "inference": {"temperature": 0.0, "seed": 42},
        "metrics": ["f1_macro"],
    }
    base.update(overrides)
    return RunSpec(**base)


class _FakeClient:
    """Stands in for OllamaClient: controllable transient/hard failures."""

    def __init__(self, *, fail_first: int = 0, raise_exc: Exception | None = None):
        self.calls = 0
        self.fail_first = fail_first
        self.raise_exc = raise_exc

    def generate_sync(self, **kwargs) -> GenerationResult:
        self.calls += 1
        if self.raise_exc is not None:
            raise self.raise_exc
        if self.calls <= self.fail_first:
            raise httpx.TimeoutException("transient")
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


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr("puma.runtime.retry.time.sleep", lambda s: None)


@pytest.mark.unit
class TestRunnerRetry:
    def test_runner_uses_default_policy_when_no_retry_policy_passed(self, tmp_path):
        runner = Runner(_spec(), db_path=tmp_path / "x.db")
        assert runner._retry_policy is DEFAULT_POLICY

    def test_runner_uses_custom_policy_when_passed(self, tmp_path):
        custom = RetryPolicy(max_attempts=5)
        runner = Runner(_spec(), db_path=tmp_path / "x.db", retry_policy=custom)
        assert runner._retry_policy is custom

    def test_runner_logs_retry_warnings_on_transient_failure(self, tmp_path, monkeypatch, no_sleep):
        warnings: list[tuple[str, dict]] = []

        class _FakeLogger:
            def warning(self, event, **kw):
                warnings.append((event, kw))

            def info(self, *a, **k):
                pass

            def error(self, *a, **k):
                pass

        monkeypatch.setattr("puma.orchestrator.runner.logger", _FakeLogger())
        runner = Runner(_spec(), db_path=tmp_path / "x.db")
        fake = _FakeClient(fail_first=1)

        result = runner._infer_one(fake, "qwen2.5:3b", "prompt")

        assert result.response == "Bug"
        assert fake.calls == 2  # one transient failure + one success
        retry_events = [kw for ev, kw in warnings if ev == "inference.retry"]
        assert len(retry_events) == 1
        assert retry_events[0]["attempt"] == 1
        assert retry_events[0]["model"] == "qwen2.5:3b"

    def test_runner_propagates_non_retryable_immediately(self, tmp_path, no_sleep):
        runner = Runner(_spec(), db_path=tmp_path / "x.db")
        fake = _FakeClient(raise_exc=ValueError("hard error"))

        with pytest.raises(ValueError, match="hard error"):
            runner._infer_one(fake, "qwen2.5:3b", "prompt")
        assert fake.calls == 1  # no retry on a non-retryable error
