"""Post-construction safety checks for PUMA Community submissions.

Wraps Pydantic validation with clearer field-path errors and adds soft
heuristics that flag suspicious submissions for human review without
auto-rejecting them.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from puma.community.schema import Submission, validate_no_pii

log = logging.getLogger("puma.community.validator")

_SUSPICIOUS_F1_THRESHOLD = 0.95
_MAX_TIMESTAMP_AGE_YEARS = 5
_MAX_FUTURE_DAYS = 30


def validate_submission_dict(d: dict[str, Any]) -> Submission:
    """Validate ``d`` as a Submission, re-raising any ``ValidationError``.

    Pydantic's ``.errors()`` payload carries the exact field path of each
    failure (``loc`` tuple); callers can render this to the user.
    """
    try:
        return Submission(**d)
    except ValidationError as exc:
        log.debug("validation failed: %s", exc.errors())
        raise


def validate_submission_file(path: Path) -> Submission:
    """Read ``path`` as JSON and validate the payload as a Submission."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_submission_dict(data)


def sweep_pii(s: Submission) -> dict[str, list[str]]:
    """Scan free-text fields for personal-data patterns.

    Returns a dict mapping field name to list of detected pattern names; empty
    dict when the submission is clean.
    """
    detected: dict[str, list[str]] = {}
    candidates: dict[str, str | None] = {
        "notes": s.notes,
        "submitter.affiliation": s.submitter.affiliation,
        "submitter.contact": s.submitter.contact,
    }
    for field, value in candidates.items():
        if not value:
            continue
        patterns = validate_no_pii(value)
        if patterns:
            detected[field] = patterns
    return detected


def is_safe_to_publish(s: Submission) -> tuple[bool, list[str]]:
    """Return ``(ok, reasons)`` for ``s``.

    Returns ``(True, [])`` if every soft check passes; otherwise a list of
    human-readable reasons. The CLI surfaces these as warnings the submitter
    can choose to override after manual review (v5 design: anomalies are
    flagged, not auto-rejected).
    """
    reasons: list[str] = []

    pii = sweep_pii(s)
    for field, patterns in pii.items():
        reasons.append(f"PII detected in {field}: {patterns}")

    if (
        s.run_metadata.scenario == "triage_jira"
        and s.metrics.f1_macro is not None
        and s.metrics.f1_macro > _SUSPICIOUS_F1_THRESHOLD
    ):
        reasons.append(
            f"Suspicious metric: F1 > {_SUSPICIOUS_F1_THRESHOLD} on triage_jira may "
            "indicate fabricated data; flagged for review"
        )

    now = datetime.now(UTC)
    past_cutoff = now - timedelta(days=365 * _MAX_TIMESTAMP_AGE_YEARS)
    future_cutoff = now + timedelta(days=_MAX_FUTURE_DAYS)
    for label, ts in (
        ("started_at", s.run_metadata.started_at),
        ("completed_at", s.run_metadata.completed_at),
    ):
        if ts < past_cutoff:
            reasons.append(
                f"Anomalous timestamps: {label} is more than "
                f"{_MAX_TIMESTAMP_AGE_YEARS} years in the past"
            )
        if ts > future_cutoff:
            reasons.append(
                f"Anomalous timestamps: {label} is more than "
                f"{_MAX_FUTURE_DAYS} days in the future"
            )

    return (not reasons, reasons)


__all__ = [
    "is_safe_to_publish",
    "sweep_pii",
    "validate_submission_dict",
    "validate_submission_file",
]
