"""Deterministic, bounded retry for transient Ollama inference failures.

Scoped to the single per-sample inference HTTP call in the runner. No
third-party retry library, no asyncio, and no jitter: the backoff timing is a
fixed exponential pattern so behavior is fully predictable and easy to test.
Non-transient errors propagate immediately. On a healthy run no retry fires, so
the data path is byte-identical to a no-retry run — retries only change the
recovery path on transient failure, never which samples are processed or in
what order.

With the default policy the wait pattern before each retry is ``0.5s`` then
``1.0s`` (two retries across three attempts), i.e. ``1.5s`` total worst-case
wait before the final attempt.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

import httpx

T = TypeVar("T")

# HTTP status codes that indicate a transient, retry-worthy condition.
_RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded exponential-backoff retry policy with deterministic timing."""

    max_attempts: int = 3
    initial_backoff_s: float = 0.5
    backoff_multiplier: float = 2.0
    max_backoff_s: float = 8.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

    def backoff_for_attempt(self, attempt: int) -> float:
        """Seconds to wait *before* the retry following attempt ``attempt``.

        ``attempt`` is 1-indexed (the wait after the 1st failed call is
        ``backoff_for_attempt(1)``). Capped at ``max_backoff_s``.
        """
        raw = self.initial_backoff_s * (self.backoff_multiplier ** (attempt - 1))
        return min(raw, self.max_backoff_s)


DEFAULT_POLICY: RetryPolicy = RetryPolicy()


def is_retryable(exc: BaseException) -> bool:
    """Return True only for transient network/runtime errors worth retrying.

    Retryable: connection/timeout/protocol errors, and HTTP status errors whose
    code is in ``{408, 425, 429, 500, 502, 503, 504}``. Everything else
    (``ModelNotFound``, malformed JSON, ``ValueError``/``KeyError`` from parsing,
    other 4xx, etc.) is treated as a hard error and propagates immediately.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS
    return isinstance(
        exc,
        httpx.TimeoutException | httpx.ConnectError | httpx.RemoteProtocolError,
    )


def retry_call(
    fn: Callable[[], T],
    policy: RetryPolicy,
    *,
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """Call ``fn`` with bounded retries on transient (``is_retryable``) failures.

    Returns ``fn()``'s value on the first success. On a retryable exception,
    fires ``on_retry(attempt, exc)`` (logging only), waits the policy backoff,
    and retries up to ``policy.max_attempts`` total invocations. Non-retryable
    exceptions propagate immediately. If every attempt fails, the last exception
    is re-raised with its original traceback.
    """
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if not is_retryable(exc) or attempt == policy.max_attempts:
                raise
            if on_retry is not None:
                on_retry(attempt, exc)
            time.sleep(policy.backoff_for_attempt(attempt))
    raise AssertionError("unreachable: max_attempts >= 1 guarantees return or raise")
