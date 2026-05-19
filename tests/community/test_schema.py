"""Unit tests for the PUMA Community submission schema (v1.0.0)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from puma.community.schema import (
    _VALID_PROFILE_IDS,
    HardwareProfile,
    Metrics,
    Submission,
    Submitter,
    validate_no_pii,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ON_DISK = REPO_ROOT / "src" / "puma" / "community" / "schema_data" / "submission.v1.json"


@pytest.fixture
def valid_submission_dict() -> dict[str, Any]:
    """A complete, valid submission payload used by every positive test."""
    return {
        "schema_version": "1.0.0",
        "submission_id": str(uuid4()),
        "submitted_at": "2026-05-18T10:00:00+00:00",
        "submitter": {
            "name_or_alias": "alice_42",
            "affiliation": "Open Research Lab",
            "contact": "alice@example.org",
            "consent_public_release": True,
            "consent_redistribution": True,
            "consent_research_use": True,
            "license": "CC-BY-4.0",
        },
        "puma_version": "2.7.0",
        "run_metadata": {
            "scenario": "triage_jira",
            "model": "qwen2.5:3b",
            "strategy": "zero_shot",
            "n_instances": 200,
            "seed": 42,
            "temperature": 0.0,
            "ollama_version": "0.3.10",
            "started_at": "2026-05-18T09:00:00+00:00",
            "completed_at": "2026-05-18T09:30:00+00:00",
            "latency_ms_total": 180000,
            "latency_ms_p50": 800,
            "latency_ms_p95": 1500,
        },
        "hardware_profile": {
            "profile_id": "gpu-entry",
            "cpu_model": "Intel Core i7-9750H",
            "cpu_cores": 12,
            "ram_gb": 16,
            "gpu_model": "NVIDIA RTX 2060 Mobile",
            "gpu_vram_gb": 6,
            "os": "Linux 6.8.0-111-generic",
        },
        "metrics": {
            "f1_macro": 0.5867,
            "accuracy": 0.62,
        },
        "sustainability": {
            "codecarbon_version": "2.4.1",
            "co2_grams_total": 12.5,
            "energy_kwh_total": 0.03,
            "tracking_mode": "machine",
            "country_iso": "ESP",
        },
        "integrity": {
            "predictions_summary_hash": "a" * 64,
            "payload_signature": None,
            "verification_status": "self-attested",
        },
        "raw_predictions_url": None,
        "notes": "Clean note about run conditions.",
    }


# ── Positive cases ───────────────────────────────────────────────────────────────────


def test_valid_submission_passes(valid_submission_dict: dict[str, Any]) -> None:
    sub = Submission(**valid_submission_dict)
    assert sub.schema_version == "1.0.0"
    assert sub.submitter.name_or_alias == "alice_42"
    assert sub.run_metadata.scenario == "triage_jira"


def test_minimal_metrics_passes_with_f1_only(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["metrics"] = {"f1_macro": 0.5}
    sub = Submission(**valid_submission_dict)
    assert sub.metrics.f1_macro == 0.5
    assert sub.metrics.accuracy is None


def test_metrics_with_mae_only_passes(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["metrics"] = {"mae": 5.71}
    valid_submission_dict["run_metadata"]["scenario"] = "effort_tawos"
    sub = Submission(**valid_submission_dict)
    assert sub.metrics.mae == 5.71


def test_metrics_with_accuracy_only_passes(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["metrics"] = {"accuracy": 0.7}
    sub = Submission(**valid_submission_dict)
    assert sub.metrics.accuracy == 0.7


def test_optional_fields_can_be_omitted(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["submitter"].pop("affiliation", None)
    valid_submission_dict["submitter"].pop("contact", None)
    valid_submission_dict.pop("raw_predictions_url", None)
    valid_submission_dict.pop("notes", None)
    valid_submission_dict["hardware_profile"]["gpu_model"] = None
    valid_submission_dict["hardware_profile"]["gpu_vram_gb"] = None
    sub = Submission(**valid_submission_dict)
    assert sub.submitter.affiliation is None
    assert sub.notes is None


# ── Consent validation ──────────────────────────────────────────────────────────────


def test_consent_public_release_required(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["submitter"]["consent_public_release"] = False
    with pytest.raises(ValidationError) as exc:
        Submission(**valid_submission_dict)
    assert "consent_public_release" in str(exc.value)


def test_consent_redistribution_required(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["submitter"]["consent_redistribution"] = False
    with pytest.raises(ValidationError) as exc:
        Submission(**valid_submission_dict)
    assert "consent_redistribution" in str(exc.value)


def test_consent_research_use_required(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["submitter"]["consent_research_use"] = False
    with pytest.raises(ValidationError) as exc:
        Submission(**valid_submission_dict)
    assert "consent_research_use" in str(exc.value)


# ── Format validation ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_version", ["1.0", "v1.0.0", "1.0.0.0", "1.0.a"])
def test_invalid_semver_rejected(valid_submission_dict: dict[str, Any], bad_version: str) -> None:
    valid_submission_dict["puma_version"] = bad_version
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


@pytest.mark.parametrize("ok_version", ["1.0.0", "2.7.0", "2.7.0-alpha", "2.7.0-rc.1"])
def test_valid_semver_accepted(valid_submission_dict: dict[str, Any], ok_version: str) -> None:
    valid_submission_dict["puma_version"] = ok_version
    sub = Submission(**valid_submission_dict)
    assert sub.puma_version == ok_version


def test_invalid_alias_too_short(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["submitter"]["name_or_alias"] = "ab"
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


def test_invalid_alias_too_long(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["submitter"]["name_or_alias"] = "a" * 65
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


def test_invalid_alias_with_spaces(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["submitter"]["name_or_alias"] = "alice doe"
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


def test_invalid_alias_with_special_chars(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["submitter"]["name_or_alias"] = "alice@home"
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


@pytest.mark.parametrize("alias", ["jdoe", "alice_42", "user-name.x", "ABC123"])
def test_valid_alias_accepted(valid_submission_dict: dict[str, Any], alias: str) -> None:
    valid_submission_dict["submitter"]["name_or_alias"] = alias
    sub = Submission(**valid_submission_dict)
    assert sub.submitter.name_or_alias == alias


def test_invalid_country_iso_lowercase(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["sustainability"]["country_iso"] = "esp"
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


def test_invalid_country_iso_wrong_length(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["sustainability"]["country_iso"] = "ES"
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


def test_sha256_hash_lowercase_hex_64_only(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["integrity"]["predictions_summary_hash"] = "A" * 64
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


# ── Sanity validation ───────────────────────────────────────────────────────────────


def test_at_least_one_metric_required(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["metrics"] = {"ece": 0.05}
    with pytest.raises(ValidationError) as exc:
        Submission(**valid_submission_dict)
    assert "f1_macro" in str(exc.value) or "At least one" in str(exc.value)


def test_completed_at_before_started_at_rejected(
    valid_submission_dict: dict[str, Any],
) -> None:
    valid_submission_dict["run_metadata"]["completed_at"] = "2026-05-18T08:00:00+00:00"
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


def test_p95_below_p50_rejected(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["run_metadata"]["latency_ms_p95"] = 100
    valid_submission_dict["run_metadata"]["latency_ms_p50"] = 500
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


def test_n_instances_zero_rejected(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict["run_metadata"]["n_instances"] = 0
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


def test_temperature_out_of_range_rejected(
    valid_submission_dict: dict[str, Any],
) -> None:
    valid_submission_dict["run_metadata"]["temperature"] = 2.5
    with pytest.raises(ValidationError):
        Submission(**valid_submission_dict)


# ── PII detection (unit tests on the helper) ────────────────────────────────────────


def test_pii_detection_finds_email() -> None:
    assert "email" in validate_no_pii("contact me at alice@example.com")


def test_pii_detection_finds_ipv4() -> None:
    assert "ipv4" in validate_no_pii("server at 192.168.1.10 was down")


def test_pii_detection_finds_linux_path() -> None:
    assert "linux_path" in validate_no_pii("data lives in /home/user/runs/foo")


def test_pii_detection_finds_windows_path() -> None:
    assert "windows_path" in validate_no_pii(r"see C:\Users\bob\data.csv")


def test_pii_detection_finds_spanish_dni() -> None:
    assert "spanish_dni" in validate_no_pii("DNI 12345678Z for reference")


def test_pii_detection_finds_spanish_nie() -> None:
    assert "spanish_nie" in validate_no_pii("NIE X1234567L sample")


def test_pii_detection_finds_github_classic_pat() -> None:
    token = "ghp_" + "A" * 36
    assert "github_classic_pat" in validate_no_pii(f"token was {token} here")


def test_pii_detection_finds_github_fine_grained_pat() -> None:
    token = "github_pat_" + "A" * 82
    assert "github_fine_grained_pat" in validate_no_pii(f"token was {token} here")


def test_pii_detection_clean_text_returns_empty() -> None:
    assert validate_no_pii("just a clean note about a benchmark run") == []


def test_pii_detection_multiple_patterns() -> None:
    text = "email alice@example.com and IP 10.0.0.1 in one note"
    detected = validate_no_pii(text)
    assert "email" in detected
    assert "ipv4" in detected


def test_notes_with_pii_rejects_submission_with_pattern_names(
    valid_submission_dict: dict[str, Any],
) -> None:
    valid_submission_dict["notes"] = "Please contact alice@example.com for raw data"
    with pytest.raises(ValidationError) as exc:
        Submission(**valid_submission_dict)
    # The custom message in errors()[].msg must name the pattern and must NOT echo
    # the offending content. (Pydantic also surfaces the raw input via `input` in
    # its own internal annotation, which is out of our control.)
    messages = [e["msg"] for e in exc.value.errors() if e["loc"] == ("notes",)]
    assert messages, "Expected a validation error on 'notes'"
    custom_msg = messages[0]
    assert "email" in custom_msg
    assert "alice@example.com" not in custom_msg


# ── Hardware profile / v2.6.0 coexistence ───────────────────────────────────────────


def test_hardware_profile_accepts_canonical_cpu_profile_id(
    valid_submission_dict: dict[str, Any],
) -> None:
    valid_submission_dict["hardware_profile"]["profile_id"] = "cpu-lite"
    valid_submission_dict["hardware_profile"]["gpu_model"] = None
    valid_submission_dict["hardware_profile"]["gpu_vram_gb"] = None
    sub = Submission(**valid_submission_dict)
    assert sub.hardware_profile.profile_id == "cpu-lite"


def test_hardware_profile_accepts_apple_silicon_profile_id(
    valid_submission_dict: dict[str, Any],
) -> None:
    apple_ids = [pid for pid in _VALID_PROFILE_IDS if pid.startswith("apple-silicon-")]
    assert apple_ids, "v2.6.0 Apple Silicon profiles must be present in the catalog"
    valid_submission_dict["hardware_profile"]["profile_id"] = sorted(apple_ids)[0]
    valid_submission_dict["hardware_profile"]["gpu_model"] = None
    valid_submission_dict["hardware_profile"]["gpu_vram_gb"] = None
    sub = Submission(**valid_submission_dict)
    assert sub.hardware_profile.profile_id.startswith("apple-silicon-")


def test_hardware_profile_rejects_unknown_profile_id(
    valid_submission_dict: dict[str, Any],
) -> None:
    valid_submission_dict["hardware_profile"]["profile_id"] = "gpu-imaginary"
    with pytest.raises(ValidationError) as exc:
        Submission(**valid_submission_dict)
    assert "Unknown profile_id" in str(exc.value) or "gpu-imaginary" in str(exc.value)


# ── Schema export ───────────────────────────────────────────────────────────────────


def test_json_schema_is_draft_2020_12() -> None:
    from jsonschema import Draft202012Validator

    schema = Submission.export_json_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)


def test_json_schema_has_correct_id() -> None:
    schema = Submission.export_json_schema()
    assert schema["$id"] == ("https://pumacp.github.io/puma-community/schema/submission.v1.json")


def test_json_schema_file_matches_pydantic_model() -> None:
    """Drift detector: the on-disk artifact must match the live Pydantic schema."""
    on_disk = json.loads(SCHEMA_ON_DISK.read_text(encoding="utf-8"))
    generated = Submission.export_json_schema()
    assert on_disk == generated, (
        "src/puma/community/schema_data/submission.v1.json is stale. "
        "Re-run `python scripts/regenerate_submission_schema.py`."
    )


# ── Smoke: helpers and re-exports stay accessible ───────────────────────────────────


def test_submitter_consent_block_alone(valid_submission_dict: dict[str, Any]) -> None:
    """Submitter validates standalone with all consents True."""
    sub = Submitter(**valid_submission_dict["submitter"])
    assert sub.consent_public_release is True


def test_metrics_block_alone() -> None:
    """Metrics with f1_macro alone is valid."""
    m = Metrics(f1_macro=0.6)
    assert m.f1_macro == 0.6
    assert m.mae is None


def test_hardware_profile_block_alone(valid_submission_dict: dict[str, Any]) -> None:
    """HardwareProfile validates standalone with a known profile_id."""
    hw = HardwareProfile(**valid_submission_dict["hardware_profile"])
    assert hw.profile_id == "gpu-entry"


def test_submitted_at_defaults_to_utc_now(valid_submission_dict: dict[str, Any]) -> None:
    valid_submission_dict.pop("submitted_at", None)
    sub = Submission(**valid_submission_dict)
    assert sub.submitted_at.tzinfo is not None
    assert (datetime.now(UTC) - sub.submitted_at).total_seconds() < 5
