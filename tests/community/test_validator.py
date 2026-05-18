"""Tests for the Submission validator and safety sweep."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from puma.community.schema import Submission
from puma.community.validator import (
    is_safe_to_publish,
    sweep_pii,
    validate_submission_dict,
    validate_submission_file,
)
from tests.community.conftest import SAMPLE_VALID_PAYLOAD


def _payload(**overrides) -> dict:
    """Deep-copy ``SAMPLE_VALID_PAYLOAD`` and apply top-level overrides."""
    payload = json.loads(json.dumps(SAMPLE_VALID_PAYLOAD))
    payload.update(overrides)
    return payload


def test_validate_dict_valid():
    submission = validate_submission_dict(_payload())
    assert isinstance(submission, Submission)


def test_validate_dict_invalid_clear_error_path():
    bad = _payload()
    bad["hardware_profile"]["profile_id"] = "not-a-real-profile"
    with pytest.raises(ValidationError) as exc:
        validate_submission_dict(bad)
    locs = {".".join(str(p) for p in err["loc"]) for err in exc.value.errors()}
    assert any("hardware_profile" in loc and "profile_id" in loc for loc in locs)


def test_validate_file_round_trip(tmp_path: Path):
    submission = Submission(**_payload())
    path = tmp_path / "submission.json"
    path.write_text(submission.model_dump_json(), encoding="utf-8")
    round_tripped = validate_submission_file(path)
    assert round_tripped.run_metadata.scenario == "triage_jira"
    assert round_tripped.submitter.name_or_alias == "alice_42"


def test_sweep_pii_clean_returns_empty_dict():
    submission = Submission(**_payload())
    assert sweep_pii(submission) == {}


def test_sweep_pii_finds_email_in_notes():
    """Post-construction mutation bypasses the schema's notes validator,
    so we can stage a tainted notes field to exercise ``sweep_pii``."""
    submission = Submission(**_payload(), notes="benign placeholder")
    submission.notes = "please contact alice@example.com tomorrow"
    detected = sweep_pii(submission)
    assert detected.get("notes") == ["email"]


def test_is_safe_to_publish_clean_returns_true():
    submission = Submission(**_payload())
    ok, reasons = is_safe_to_publish(submission)
    assert ok is True
    assert reasons == []


def test_is_safe_to_publish_pii_returns_false_with_reasons():
    payload = _payload()
    payload["submitter"]["contact"] = "alice@example.com"
    submission = Submission(**payload)
    ok, reasons = is_safe_to_publish(submission)
    assert ok is False
    assert any("PII detected in submitter.contact" in r for r in reasons)


def test_is_safe_to_publish_suspicious_metric_flags_for_review():
    payload = _payload()
    payload["metrics"]["f1_macro"] = 0.99
    payload["run_metadata"]["scenario"] = "triage_jira"
    submission = Submission(**payload)
    ok, reasons = is_safe_to_publish(submission)
    assert ok is False
    assert any("F1 > 0.95 on triage_jira" in r for r in reasons)


def test_is_safe_to_publish_flags_anomalous_future_timestamp():
    payload = _payload()
    far_future = datetime(2099, 1, 1, tzinfo=UTC).isoformat()
    payload["run_metadata"]["started_at"] = far_future
    payload["run_metadata"]["completed_at"] = far_future
    submission = Submission(**payload)
    ok, reasons = is_safe_to_publish(submission)
    assert ok is False
    assert any("Anomalous timestamps" in r for r in reasons)
