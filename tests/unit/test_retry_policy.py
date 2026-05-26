"""Unit tests for RetryPolicy + is_retryable (US-12.15)."""

from __future__ import annotations

import httpx
import pytest

from puma.models.client import ModelNotFound
from puma.runtime.retry import DEFAULT_POLICY, RetryPolicy, is_retryable


def _status_error(code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "http://h:11434/api/generate")
    response = httpx.Response(code, request=request)
    return httpx.HTTPStatusError(f"HTTP {code}", request=request, response=response)


@pytest.mark.unit
class TestRetryPolicy:
    def test_default_policy_has_3_attempts(self):
        assert DEFAULT_POLICY.max_attempts == 3

    def test_default_policy_bounded_total_wait_budget(self):
        p = DEFAULT_POLICY
        total = sum(p.backoff_for_attempt(i) for i in range(1, p.max_attempts))
        assert total < p.max_backoff_s * p.max_attempts

    def test_max_attempts_below_one_rejected(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RetryPolicy(max_attempts=0)


@pytest.mark.unit
class TestIsRetryable:
    def test_is_retryable_returns_true_for_httpx_timeout(self):
        assert is_retryable(httpx.TimeoutException("t")) is True

    def test_is_retryable_returns_true_for_httpx_connect_error(self):
        assert is_retryable(httpx.ConnectError("refused")) is True

    def test_is_retryable_returns_true_for_remote_protocol_error(self):
        assert is_retryable(httpx.RemoteProtocolError("broke")) is True

    @pytest.mark.parametrize("code", [500, 502, 503, 504])
    def test_is_retryable_returns_true_for_5xx_status(self, code):
        assert is_retryable(_status_error(code)) is True

    def test_is_retryable_returns_true_for_429(self):
        assert is_retryable(_status_error(429)) is True

    def test_is_retryable_returns_true_for_408_and_425(self):
        assert is_retryable(_status_error(408)) is True
        assert is_retryable(_status_error(425)) is True

    def test_is_retryable_returns_false_for_value_error(self):
        assert is_retryable(ValueError("bad")) is False

    @pytest.mark.parametrize("code", [400, 401, 403, 404])
    def test_is_retryable_returns_false_for_4xx_status_other_than_408_425_429(self, code):
        assert is_retryable(_status_error(code)) is False

    def test_is_retryable_returns_false_for_model_not_found(self):
        assert is_retryable(ModelNotFound("ghost:1b")) is False
