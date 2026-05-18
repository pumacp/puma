"""Construct PUMA Community Submission instances from local SQLite runs.

The builder is strictly read-only against the database: only SELECT statements
are issued. It bridges PUMA's internal naming (``estimation_tawos``, kebab-case
strategies) to the community schema's canonical naming (``effort_tawos``,
snake_case strategies). Models on the exclusion or pending-validation lists are
refused before any submission is constructed.
"""

from __future__ import annotations

import functools
import logging
import re
import subprocess
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from puma.community.integrity import compute_predictions_hash
from puma.community.schema import (
    HardwareProfile,
    Integrity,
    Metrics,
    RunMetadata,
    Submission,
    Submitter,
    Sustainability,
    validate_no_pii,
)
from puma.storage.models import Emission, Metric, Prediction, ProfileSnapshot, Run

log = logging.getLogger("puma.community.builder")

REPO_ROOT = Path(__file__).resolve().parents[3]
_CATALOG_PATH = REPO_ROOT / "config" / "models_catalog.yaml"

# ``config/models_catalog.yaml`` does not use ``excluded: true`` or
# ``pending_validation: true`` flags, and there is no top-level
# ``excluded_models`` list. Convention discovered by inspecting the file:
#   * Excluded models are simply absent from the catalog (Kimi K2.6 is not
#     present at all). They are hard-coded here, since "absent" cannot be
#     enumerated from the YAML.
#   * Pending-validation models carry the sentinel string
#     ``"Empirical validation status: pending"`` inside their ``notes`` field.
_PENDING_SENTINEL = "Empirical validation status: pending"
_HARD_EXCLUDED_MODELS: frozenset[str] = frozenset({"kimi-k2:6.0"})

_SCENARIO_TRANSLATIONS: dict[str, str] = {
    "triage_jira": "triage_jira",
    "estimation_tawos": "effort_tawos",
    "prioritization_jira": "prioritization_jira",
}

_VALID_SCHEMA_STRATEGIES: frozenset[str] = frozenset(
    {
        "zero_shot",
        "zero_shot_cot",
        "few_shot_3",
        "few_shot_6",
        "cot_few_shot",
        "rcoif",
        "contextual_anchoring",
        "egi",
        "self_consistency",
    }
)

_GIT_TAG_PATTERN = re.compile(r"^v(\d+\.\d+\.\d+)$")
_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9\.]+)?$")

# The schema regex ``^\d+\.\d+\.\d+(-[a-zA-Z0-9\.]+)?$`` does not accept the
# ``+unknown`` build-metadata form, so the fallback sentinel uses ``-unknown``.
_VERSION_UNKNOWN = "0.0.0-unknown"

_SORT_FLOOR = datetime.min.replace(tzinfo=UTC)


def _ensure_utc(value: datetime) -> datetime:
    """SQLite strips tzinfo from ``DateTime(timezone=True)`` columns on read.

    The PUMA storage convention is to write UTC-naive timestamps via
    ``datetime.now(UTC)``, so the safe coercion is to re-attach UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class CommunityError(Exception):
    """Base class for builder failures."""


class RunNotFoundError(CommunityError):
    pass


class IncompleteRunError(CommunityError):
    pass


class PIIDetectedError(CommunityError):
    def __init__(self, patterns: list[str]) -> None:
        self.patterns = patterns
        super().__init__(
            f"Personal-data pattern(s) detected in notes: {patterns}. "
            "Redact the offending content and retry."
        )


class UnknownScenarioError(CommunityError):
    pass


class UnknownStrategyError(CommunityError):
    pass


class ExcludedModelError(CommunityError):
    def __init__(self, model: str, reason: Literal["excluded", "pending_validation"]) -> None:
        self.model = model
        self.reason = reason
        super().__init__(
            f"Model {model!r} is {reason} and cannot be shared via PUMA Community."
        )


@functools.lru_cache(maxsize=1)
def _load_excluded_and_pending_models() -> tuple[frozenset[str], frozenset[str]]:
    """Return ``(excluded, pending_validation)`` model sets.

    The excluded set is the hard-coded list above. The pending set is built by
    scanning each catalog entry's ``notes`` for ``_PENDING_SENTINEL``.
    """
    pending: set[str] = set()
    try:
        with open(_CATALOG_PATH, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        log.warning(
            "Models catalog not found at %s — pending list defaults to empty.",
            _CATALOG_PATH,
        )
        return _HARD_EXCLUDED_MODELS, frozenset()
    for entry in raw.get("models", []):
        notes = entry.get("notes") or ""
        if _PENDING_SENTINEL in notes:
            tag = entry.get("ollama_tag")
            if tag:
                pending.add(tag)
    return _HARD_EXCLUDED_MODELS, frozenset(pending)


def _check_model_exclusion(model: str) -> None:
    excluded, pending = _load_excluded_and_pending_models()
    if model in excluded:
        raise ExcludedModelError(model, "excluded")
    if model in pending:
        raise ExcludedModelError(model, "pending_validation")


def _translate_scenario(name: str) -> str:
    mapped = _SCENARIO_TRANSLATIONS.get(name)
    if mapped is None:
        raise UnknownScenarioError(
            f"Unknown scenario {name!r}. Canonical schema values: "
            f"{sorted(set(_SCENARIO_TRANSLATIONS.values()))}"
        )
    return mapped


def _translate_strategy(name: str) -> str:
    snake = name.replace("-", "_")
    if snake not in _VALID_SCHEMA_STRATEGIES:
        raise UnknownStrategyError(
            f"Unknown strategy {name!r}. Canonical schema values: "
            f"{sorted(_VALID_SCHEMA_STRATEGIES)}"
        )
    return snake


@functools.lru_cache(maxsize=1)
def _resolve_puma_version_from_git() -> str | None:
    """Return the most recent ``vX.Y.Z`` annotated tag, with leading ``v`` stripped."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(REPO_ROOT),
            check=False,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        log.debug("git describe failed: %s", exc)
        return None
    if result.returncode != 0:
        log.debug("git describe non-zero exit: %s", result.stderr.strip())
        return None
    tag = result.stdout.strip()
    match = _GIT_TAG_PATTERN.match(tag)
    if match is None:
        log.debug("git describe returned non-semver tag %r", tag)
        return None
    return match.group(1)


def _resolve_puma_version(snapshot: ProfileSnapshot | None) -> str:
    """git describe → ProfileSnapshot.puma_version → ``0.0.0-unknown``."""
    from_git = _resolve_puma_version_from_git()
    if from_git is not None:
        return from_git
    if (
        snapshot is not None
        and snapshot.puma_version
        and _SEMVER_PATTERN.match(snapshot.puma_version)
    ):
        return snapshot.puma_version
    log.warning(
        "Could not resolve PUMA version from git tag or ProfileSnapshot; "
        "using fallback sentinel %r.",
        _VERSION_UNKNOWN,
    )
    return _VERSION_UNKNOWN


def _quantile(values: list[float], q: float) -> float:
    """Linear-interpolation percentile, matching ``numpy.percentile`` defaults."""
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lower = int(pos)
    upper = min(lower + 1, len(sorted_vals) - 1)
    weight = pos - lower
    return sorted_vals[lower] * (1 - weight) + sorted_vals[upper] * weight


def _percentiles(latencies: Iterable[float | None]) -> tuple[int, int, int]:
    """Return ``(total_ms, p50_ms, p95_ms)`` for per-prediction latencies."""
    cleaned = [v for v in latencies if v is not None]
    if not cleaned:
        return 0, 0, 0
    if len(cleaned) < 2:
        log.warning("Run has fewer than 2 latencies; p50 and p95 default to 0.")
        return int(sum(cleaned)), 0, 0
    total = int(sum(cleaned))
    p50 = int(_quantile(cleaned, 0.5))
    p95 = int(_quantile(cleaned, 0.95))
    return total, p50, p95


def _codecarbon_version() -> str:
    try:
        import codecarbon

        version = getattr(codecarbon, "__version__", "unknown")
    except Exception:  # pragma: no cover — defensive only
        version = "unknown"
    return str(version)[:32]


def _parse_runspec(spec_yaml: str | None) -> dict[str, Any]:
    if not spec_yaml:
        return {}
    try:
        parsed = yaml.safe_load(spec_yaml) or {}
    except yaml.YAMLError as exc:
        log.warning("Failed to parse run.spec_yaml: %s", exc)
        return {}
    return parsed if isinstance(parsed, dict) else {}


def build_submission_from_run(
    *,
    run_id: str,
    submitter: Submitter,
    session: Session,
    notes: str | None = None,
) -> Submission:
    """Construct a ``Submission`` for ``run_id`` from local SQLite state.

    Read-only: only SELECT statements are issued. Raises one of the module's
    custom exceptions on any failure; Pydantic ``ValidationError`` propagates
    unchanged for downstream callers.
    """
    run = session.execute(select(Run).where(Run.run_id == run_id)).scalar_one_or_none()
    if run is None:
        raise RunNotFoundError(f"run_id {run_id!r} not found")

    pair_rows = session.execute(
        select(distinct(Prediction.model), Prediction.strategy).where(
            Prediction.run_id == run_id
        )
    ).all()
    if not pair_rows:
        raise IncompleteRunError(f"run_id {run_id!r} has no predictions")
    if len(pair_rows) > 1:
        raise IncompleteRunError(
            f"run_id {run_id!r} spans multiple (model, strategy) pairs: "
            f"{pair_rows}. A community submission represents a single slice."
        )
    raw_model, raw_strategy = pair_rows[0]

    _check_model_exclusion(raw_model)

    spec = _parse_runspec(run.spec_yaml)
    raw_scenario = spec.get("scenario")
    if raw_scenario is None:
        raise IncompleteRunError(
            f"run_id {run_id!r} has no scenario recorded in spec_yaml"
        )
    scenario = _translate_scenario(raw_scenario)
    strategy = _translate_strategy(raw_strategy)

    snapshot = session.execute(
        select(ProfileSnapshot).where(ProfileSnapshot.run_id == run_id)
    ).scalar_one_or_none()
    if snapshot is None:
        raise IncompleteRunError(f"run_id {run_id!r} has no profile_snapshot")
    if not run.profile:
        raise IncompleteRunError(
            f"run_id {run_id!r} has no profile_id (Run.profile is NULL)"
        )

    emission = (
        session.execute(
            select(Emission)
            .where(Emission.run_id == run_id)
            .order_by(Emission.emission_id.desc())
        )
        .scalars()
        .first()
    )
    if emission is None:
        raise IncompleteRunError(f"run_id {run_id!r} has no emissions record")

    metric_rows = session.execute(
        select(Metric.metric_name, Metric.value).where(
            Metric.run_id == run_id,
            Metric.scope == "global",
        )
    ).all()
    if not metric_rows:
        raise IncompleteRunError(f"run_id {run_id!r} has no global metrics")
    metric_map: dict[str, float] = {row[0]: row[1] for row in metric_rows}

    n_instances = session.execute(
        select(func.count(Prediction.pred_id)).where(Prediction.run_id == run_id)
    ).scalar_one()
    latencies = (
        session.execute(
            select(Prediction.latency_ms).where(Prediction.run_id == run_id)
        )
        .scalars()
        .all()
    )
    total_ms, p50_ms, p95_ms = _percentiles(latencies)

    predictions_hash = compute_predictions_hash(session=session, run_id=run_id)

    if notes is not None:
        detected = validate_no_pii(notes)
        if detected:
            raise PIIDetectedError(detected)

    if run.finished_at is None:
        raise IncompleteRunError(f"run_id {run_id!r} has no finished_at timestamp")

    extra = snapshot.extra or {}
    cpu_cores = extra.get("cpu_cores")
    if cpu_cores is None:
        raise IncompleteRunError(
            f"run_id {run_id!r} ProfileSnapshot.extra is missing 'cpu_cores'."
        )

    inference_raw = spec.get("inference")
    inference: dict[str, Any] = inference_raw if isinstance(inference_raw, dict) else {}
    sustainability_raw = spec.get("sustainability")
    sustainability_block: dict[str, Any] = (
        sustainability_raw if isinstance(sustainability_raw, dict) else {}
    )
    seed_value = inference.get("seed", 42)
    temperature_value = inference.get("temperature", 0.0)
    country_iso = sustainability_block.get("country_iso", "ESP")

    return Submission(
        submitter=submitter,
        puma_version=_resolve_puma_version(snapshot),
        run_metadata=RunMetadata(
            scenario=cast(Any, scenario),
            model=raw_model,
            strategy=cast(Any, strategy),
            n_instances=int(n_instances),
            seed=int(seed_value),
            temperature=float(temperature_value),
            ollama_version=(snapshot.ollama_version or "unknown")[:64],
            started_at=_ensure_utc(run.started_at),
            completed_at=_ensure_utc(run.finished_at),
            latency_ms_total=total_ms,
            latency_ms_p50=p50_ms,
            latency_ms_p95=p95_ms,
        ),
        hardware_profile=HardwareProfile(
            profile_id=run.profile,
            cpu_model=(snapshot.cpu or "unknown")[:128],
            cpu_cores=int(cpu_cores),
            ram_gb=int(snapshot.ram_gb or 1),
            gpu_model=snapshot.gpu,
            gpu_vram_gb=int(snapshot.vram_gb) if snapshot.vram_gb is not None else None,
            os=(snapshot.os or "unknown")[:128],
        ),
        metrics=Metrics(
            f1_macro=metric_map.get("f1_macro"),
            mae=metric_map.get("mae"),
            accuracy=metric_map.get("accuracy"),
        ),
        sustainability=Sustainability(
            codecarbon_version=_codecarbon_version(),
            co2_grams_total=float((emission.co2_kg or 0.0) * 1000.0),
            energy_kwh_total=float(emission.kwh or 0.0),
            tracking_mode="machine",
            country_iso=country_iso,
        ),
        integrity=Integrity(predictions_summary_hash=predictions_hash),
        notes=notes,
    )


def list_shareable_runs(*, session: Session) -> list[dict[str, Any]]:
    """Return metadata for runs eligible to be shared.

    A run is shareable when its status is ``"done"``, it has at least one
    global metric row, exactly one ``(model, strategy)`` pair, and its model
    is on neither the excluded nor the pending-validation list.
    """
    excluded, pending = _load_excluded_and_pending_models()

    runs = session.execute(select(Run).where(Run.status == "done")).scalars().all()
    out: list[dict[str, Any]] = []
    for run in runs:
        pair_rows = session.execute(
            select(distinct(Prediction.model), Prediction.strategy).where(
                Prediction.run_id == run.run_id
            )
        ).all()
        if len(pair_rows) != 1:
            continue
        model, strategy = pair_rows[0]
        if model in excluded or model in pending:
            continue

        metric_rows = session.execute(
            select(Metric.metric_name, Metric.value).where(
                Metric.run_id == run.run_id, Metric.scope == "global"
            )
        ).all()
        if not metric_rows:
            continue
        mmap: dict[str, float] = {row[0]: row[1] for row in metric_rows}

        emission = (
            session.execute(select(Emission).where(Emission.run_id == run.run_id))
            .scalars()
            .first()
        )
        co2 = float((emission.co2_kg or 0.0) * 1000.0) if emission else 0.0

        n_instances = session.execute(
            select(func.count(Prediction.pred_id)).where(Prediction.run_id == run.run_id)
        ).scalar_one()

        spec = _parse_runspec(run.spec_yaml)
        scenario = spec.get("scenario", "unknown")

        out.append(
            {
                "run_id": run.run_id,
                "scenario": scenario,
                "model": model,
                "strategy": strategy,
                "completed_at": _ensure_utc(run.finished_at) if run.finished_at else None,
                "f1_macro": mmap.get("f1_macro"),
                "mae": mmap.get("mae"),
                "accuracy": mmap.get("accuracy"),
                "co2_grams_total": co2,
                "n_instances": int(n_instances),
            }
        )
    out.sort(key=lambda r: r["completed_at"] or _SORT_FLOOR, reverse=True)
    return out


__all__ = [
    "CommunityError",
    "ExcludedModelError",
    "IncompleteRunError",
    "PIIDetectedError",
    "RunNotFoundError",
    "UnknownScenarioError",
    "UnknownStrategyError",
    "build_submission_from_run",
    "list_shareable_runs",
]
