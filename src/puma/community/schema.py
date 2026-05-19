"""PUMA Community submission schema (v1.0.0).

This module defines the canonical data contract for community-contributed evaluation
results that PUMA Community publishes to ``pumacp/puma-community``. The schema is the
single source of truth: the Pydantic v2 models, the on-disk JSON Schema artifact in
``schema_data/submission.v1.json``, and every downstream validator share these
definitions.

Importing this module has no side effects beyond:
    * loading the canonical hardware-profile catalog from ``config/profiles.yaml`` once,
      to populate ``_VALID_PROFILE_IDS``;
    * compiling the personal-data regex set used by ``validate_no_pii``.

No network, no filesystem writes, no logging beyond a single warning if the profile
catalog cannot be located.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

log = logging.getLogger("puma.community.schema")


# ── Canonical profile catalog ────────────────────────────────────────────────────────
#
# The schema sources its valid profile_id values from ``config/profiles.yaml``, the
# same file that powers ``puma.preflight.profile``. Sourcing from the YAML rather than
# hardcoding a list ensures that any profile added by future PUMA releases (the
# v2.6.0 Apple-Silicon family, the v2.7.0 catalog expansion, anything later) is
# automatically accepted by this schema with no code change required.


def _load_valid_profile_ids() -> frozenset[str]:
    """Read ``config/profiles.yaml`` and return its profile-id key set.

    The file lives at ``<repo-root>/config/profiles.yaml`` in the canonical layout.
    Returns an empty frozenset and emits a warning if the file is missing — callers
    should treat this as a degraded mode (profile_id validation will reject every
    value).
    """
    profiles_path = Path(__file__).resolve().parents[3] / "config" / "profiles.yaml"
    try:
        with open(profiles_path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except FileNotFoundError:
        log.warning(
            "Profile catalog not found at %s — profile_id validation will reject all values.",
            profiles_path,
        )
        return frozenset()
    profiles = raw.get("profiles") or {}
    return frozenset(profiles.keys())


_VALID_PROFILE_IDS: frozenset[str] = _load_valid_profile_ids()


# ── Personal-data detectors ──────────────────────────────────────────────────────────
#
# Patterns are compiled once at import time. ``validate_no_pii`` returns the list of
# pattern names that matched, never the matched substring (so the error path never
# echoes the offending content back into logs or exceptions).


_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "ipv6": re.compile(r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b"),
    "linux_path": re.compile(r"/(?:home|Users|root|var|opt|tmp)/[^\s]+"),
    "windows_path": re.compile(r"[A-Z]:\\[^\s]+"),
    "spanish_dni": re.compile(r"\b\d{8}[A-HJ-NP-TV-Z]\b"),
    "spanish_nie": re.compile(r"\b[XYZ]\d{7}[A-HJ-NP-TV-Z]\b"),
    "phone_es": re.compile(r"(?:\+34|0034|34)?[6-9]\d{8}"),
    "credit_card_simple": re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_classic_pat": re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    "github_fine_grained_pat": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{82}\b"),
}


def validate_no_pii(text: str) -> list[str]:
    """Return the names of personal-data patterns detected in ``text``.

    Returns an empty list when no pattern matches. Never returns the matched
    substring, so callers can include the result list in error messages without
    leaking the offending content.
    """
    return [name for name, pat in _PII_PATTERNS.items() if pat.search(text)]


# ── Sub-models ───────────────────────────────────────────────────────────────────────


class Submitter(BaseModel):
    """Contributor identity and consent block."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name_or_alias: str = Field(
        min_length=3,
        max_length=64,
        pattern=r"^[A-Za-z0-9_\-\.]+$",
    )
    affiliation: str | None = Field(default=None, max_length=128)
    contact: str | None = Field(default=None, max_length=128)
    consent_public_release: bool
    consent_redistribution: bool
    consent_research_use: bool
    license: Literal["CC-BY-4.0"] = "CC-BY-4.0"

    @model_validator(mode="after")
    def _check_consents(self) -> Submitter:
        missing: list[str] = []
        if not self.consent_public_release:
            missing.append("consent_public_release")
        if not self.consent_redistribution:
            missing.append("consent_redistribution")
        if not self.consent_research_use:
            missing.append("consent_research_use")
        if missing:
            raise ValueError(f"All consent fields must be true. Missing or false: {missing}")
        return self


class RunMetadata(BaseModel):
    """Per-run identification: scenario, model, strategy, timing, latency."""

    model_config = ConfigDict(extra="forbid")

    scenario: Literal["triage_jira", "effort_tawos", "prioritization_jira"]
    model: str = Field(max_length=128)
    strategy: Literal[
        "zero_shot",
        "zero_shot_cot",
        "few_shot_3",
        "few_shot_6",
        "cot_few_shot",
        "rcoif",
        "contextual_anchoring",
        "egi",
        "self_consistency",
    ]
    n_instances: int = Field(ge=1, le=100000)
    seed: int = 42
    temperature: float = Field(ge=0.0, le=2.0)
    ollama_version: str = Field(max_length=64)
    started_at: datetime
    completed_at: datetime
    latency_ms_total: int = Field(ge=0)
    latency_ms_p50: int = Field(ge=0)
    latency_ms_p95: int = Field(ge=0)

    @field_validator("started_at", "completed_at", mode="before")
    @classmethod
    def _ensure_utc(cls, v: Any) -> datetime:
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if not isinstance(v, datetime):
            raise ValueError("datetime field requires an ISO-8601 string or datetime")
        if v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware (UTC)")
        return v.astimezone(UTC)

    @model_validator(mode="after")
    def _validate_sanity(self) -> RunMetadata:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be >= started_at")
        if not (self.latency_ms_p95 >= self.latency_ms_p50 >= 0):
            raise ValueError("latency invariant: latency_ms_p95 >= latency_ms_p50 >= 0")
        return self


# HardwareProfile.profile_id defers to the canonical PUMA catalog loaded from
# ``config/profiles.yaml`` at module import. v2.6.0 introduced the Apple-Silicon
# profile family; v2.7.0 left the catalog unchanged for hardware. The schema picks
# up the full set automatically — no edits are required here when the catalog grows.
class HardwareProfile(BaseModel):
    """Hardware identification keyed by canonical PUMA profile_id."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(max_length=64)
    cpu_model: str = Field(max_length=128)
    cpu_cores: int = Field(ge=1, le=512)
    ram_gb: int = Field(ge=1, le=4096)
    gpu_model: str | None = Field(default=None, max_length=128)
    gpu_vram_gb: int | None = Field(default=None, ge=0, le=512)
    os: str = Field(max_length=128)

    @field_validator("profile_id")
    @classmethod
    def _validate_profile_id(cls, v: str) -> str:
        if v not in _VALID_PROFILE_IDS:
            raise ValueError(
                f"Unknown profile_id {v!r}. Canonical catalog: {sorted(_VALID_PROFILE_IDS)}"
            )
        return v


class Metrics(BaseModel):
    """Scenario-specific quality metrics. At least one of f1_macro / mae / accuracy."""

    model_config = ConfigDict(extra="forbid")

    f1_macro: float | None = Field(default=None, ge=0.0, le=1.0)
    f1_per_class: dict[str, float] | None = None
    mae: float | None = Field(default=None, ge=0.0)
    mdae: float | None = Field(default=None, ge=0.0)
    accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    confusion_matrix: list[list[int]] | None = None
    ece: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _at_least_one_metric(self) -> Metrics:
        if self.f1_macro is None and self.mae is None and self.accuracy is None:
            raise ValueError("At least one of f1_macro, mae, or accuracy must be provided")
        return self


class Sustainability(BaseModel):
    """CodeCarbon emissions block (cf. PUMA core sustainability subsystem)."""

    model_config = ConfigDict(extra="forbid")

    codecarbon_version: str = Field(max_length=32)
    co2_grams_total: float = Field(ge=0.0)
    energy_kwh_total: float = Field(ge=0.0)
    tracking_mode: Literal["machine", "process"]
    country_iso: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")


class Integrity(BaseModel):
    """Integrity attestations for the submission payload."""

    model_config = ConfigDict(extra="forbid")

    predictions_summary_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    payload_signature: str | None = Field(default=None, max_length=512)
    verification_status: Literal["unverified", "self-attested", "community-verified"] = (
        "self-attested"
    )


# ── Root model ───────────────────────────────────────────────────────────────────────


class Submission(BaseModel):
    """Root submission payload (v1.0.0)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = "1.0.0"
    submission_id: UUID = Field(default_factory=uuid4)
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    submitter: Submitter
    # ``puma_version`` validates semver format only. The builder (Prompt 3) populates
    # it from the git tag (``git describe --tags --abbrev=0``) or from
    # ``ProfileSnapshot.puma_version`` recorded at run time, never from
    # ``pyproject.toml.version`` (which currently disagrees with the latest tag and
    # with ``src/puma/__init__.py.__version__``; see RT3 in
    # ``docs/community/risk-register.md``).
    puma_version: str = Field(pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9\.]+)?$")
    run_metadata: RunMetadata
    hardware_profile: HardwareProfile
    metrics: Metrics
    sustainability: Sustainability
    integrity: Integrity
    raw_predictions_url: HttpUrl | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("notes", mode="after")
    @classmethod
    def _validate_no_pii_in_notes(cls, v: str | None) -> str | None:
        if v is None:
            return v
        detected = validate_no_pii(v)
        if detected:
            raise ValueError(
                f"PII pattern(s) detected in notes: {detected}. "
                "Remove the offending content and resubmit."
            )
        return v

    @classmethod
    def export_json_schema(cls) -> dict[str, Any]:
        """Return a Pydantic-derived JSON Schema annotated as Draft 2020-12.

        The dict carries top-level ``$schema`` and ``$id`` keys so external
        validators (the community repository's GitHub Action, ``jsonschema-cli``,
        etc.) can consume the artifact directly.
        """
        schema: dict[str, Any] = cls.model_json_schema()
        # Re-order so $schema and $id appear first, then the original keys.
        meta: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://pumacp.github.io/puma-community/schema/submission.v1.json",
        }
        meta.update(schema)
        return meta


__all__ = [
    "HardwareProfile",
    "Integrity",
    "Metrics",
    "RunMetadata",
    "Submission",
    "Submitter",
    "Sustainability",
    "validate_no_pii",
]


def _dump_schema_to(path: Path) -> None:
    """Write the canonical JSON Schema artifact to ``path``."""
    schema = Submission.export_json_schema()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, indent=2, sort_keys=False) + "\n", encoding="utf-8")
