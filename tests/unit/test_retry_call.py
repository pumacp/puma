"""Unit tests for retry_call (US-12.15)."""

from __future__ import annotations

import httpx
import pytest

from puma.runtime.retry import RetryPolicy, retry_call


@pytest.fixture
def no_sleep(monkeypatch):
    """Record backoff durations without actually sleeping."""
    sleeps: list[float] = []
    monkeypatch.setattr("puma.runtime.retry.time.sleep", lambda s: sleeps.append(s))
    return sleeps


@pytest.mark.unit
class TestRetryCall:
    def test_retry_call_returns_immediately_on_success(self, no_sleep):
        calls = {"n": 0}

        def fn() -> str:
            calls["n"] += 1
            return "ok"

        assert retry_call(fn, RetryPolicy()) == "ok"
        assert calls["n"] == 1
        assert no_sleep == []

    def test_retry_call_retries_on_retryable_exception(self, no_sleep):
        calls = {"n": 0}

        def fn() -> str:
            calls["n"] += 1
            if calls["n"] <= 2:
                raise httpx.TimeoutException("transient")
            return "ok"

        assert retry_call(fn, RetryPolicy()) == "ok"
        assert calls["n"] == 3

    def test_retry_call_raises_after_max_attempts(self, no_sleep):
        calls = {"n": 0}

        def fn() -> str:
            calls["n"] += 1
            raise httpx.TimeoutException(f"transient {calls['n']}")

        with pytest.raises(httpx.TimeoutException):
            retry_call(fn, RetryPolicy(max_attempts=3))
        assert calls["n"] == 3

    def test_retry_call_does_not_retry_non_retryable_exception(self, no_sleep):
        calls = {"n": 0}

        def fn() -> str:
            calls["n"] += 1
            raise ValueError("hard error")

        with pytest.raises(ValueError, match="hard error"):
            retry_call(fn, RetryPolicy())
        assert calls["n"] == 1
        assert no_sleep == []

    def test_retry_call_invokes_on_retry_callback_with_attempt_number(self, no_sleep):
        seen: list[int] = []

        def fn() -> str:
            if len(seen) < 2:
                raise httpx.ConnectError("refused")
            return "ok"

        retry_call(fn, RetryPolicy(), on_retry=lambda n, _e: seen.append(n))
        assert seen == [1, 2]

    def test_retry_call_uses_exponential_backoff(self, no_sleep):
        calls = {"n": 0}

        def fn() -> str:
            calls["n"] += 1
            if calls["n"] <= 2:
                raise httpx.TimeoutException("transient")
            return "ok"

        retry_call(fn, RetryPolicy())  # defaults: 0.5, *2
        assert no_sleep == [0.5, 1.0]

    def test_retry_call_caps_backoff_at_max_backoff_s(self, no_sleep):
        def fn() -> str:
            raise httpx.TimeoutException("transient")

        policy = RetryPolicy(
            max_attempts=5, initial_backoff_s=0.5, backoff_multiplier=2.0, max_backoff_s=1.0
        )
        with pytest.raises(httpx.TimeoutException):
            retry_call(fn, policy)
        assert no_sleep == [0.5, 1.0, 1.0, 1.0]
        assert all(s <= policy.max_backoff_s for s in no_sleep)
