"""Fixtures for ``tests/community/`` — in-memory SQLite plus seeded test data.

The community modules are strictly read-only against the database, so the
fixtures own all INSERTs. Tests get a session factory and use it however they
like.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from puma.community import builder as builder_mod
from puma.community.schema import Submitter
from puma.storage.models import (
    Base,
    Emission,
    Instance,
    Metric,
    Prediction,
    ProfileSnapshot,
    Run,
)

SessionFactory = Callable[[], Session]


@pytest.fixture(autouse=True)
def _reset_builder_caches() -> None:
    """Clear builder ``lru_cache`` state between tests.

    The builder caches the git-resolved version and the parsed catalog. Tests
    that monkeypatch ``subprocess.run`` or the catalog need a fresh cache.
    """
    builder_mod._resolve_puma_version_from_git.cache_clear()
    builder_mod._load_excluded_and_pending_models.cache_clear()


def _make_engine() -> Engine:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def in_memory_db() -> Generator[SessionFactory, None, None]:
    engine = _make_engine()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    yield factory
    engine.dispose()


@pytest.fixture
def valid_submitter() -> Submitter:
    return Submitter(
        name_or_alias="alice_42",
        affiliation="Open Research Lab",
        contact=None,
        consent_public_release=True,
        consent_redistribution=True,
        consent_research_use=True,
    )


def _make_instances(session: Session, dataset: str, n: int) -> list[str]:
    ids: list[str] = []
    for i in range(n):
        iid = f"{dataset}-inst-{i:03d}"
        ids.append(iid)
        session.add(
            Instance(
                instance_id=iid,
                dataset=dataset,
                source_id=f"{dataset}/{i}",
                input_text=f"sample {i}",
                gold_label="L1" if dataset == "jira_triage" else "5",
            )
        )
    return ids


def _add_predictions(
    session: Session,
    *,
    run_id: str,
    instance_ids: list[str],
    model: str,
    strategy: str,
    base_latency: float = 100.0,
) -> None:
    for i, iid in enumerate(instance_ids):
        session.add(
            Prediction(
                run_id=run_id,
                instance_id=iid,
                model=model,
                strategy=strategy,
                prompt_hash=f"ph{i:04d}",
                raw_response=f"resp-{i}",
                parsed_label=f"L{i % 3}",
                confidence=0.5 + i * 0.01,
                latency_ms=base_latency + i,
                tokens_in=100,
                tokens_out=50,
            )
        )


def _add_metrics(session: Session, *, run_id: str, kind: str) -> None:
    rows: list[tuple[str, float]]
    if kind == "triage":
        rows = [("f1_macro", 0.58), ("accuracy", 0.62)]
    else:
        rows = [("mae", 4.2), ("accuracy", 0.70)]
    for name, value in rows:
        session.add(
            Metric(
                run_id=run_id,
                scope="global",
                metric_name=name,
                value=value,
            )
        )


def _add_emission(session: Session, *, run_id: str) -> None:
    session.add(
        Emission(
            run_id=run_id,
            kwh=0.03,
            co2_kg=0.0125,
            duration_s=180.0,
            cpu_energy=0.02,
            gpu_energy=0.01,
            ram_energy=0.0,
        )
    )


def _add_snapshot(
    session: Session,
    *,
    run_id: str,
    puma_version: str = "2.7.0",
) -> None:
    session.add(
        ProfileSnapshot(
            run_id=run_id,
            os="Linux 6.8.0-111-generic",
            cpu="Intel Core i7-9750H",
            ram_gb=16.0,
            gpu="NVIDIA RTX 2060 Mobile",
            vram_gb=6.0,
            ollama_version="0.3.10",
            puma_version=puma_version,
            extra={"cpu_cores": 12},
        )
    )


_SPEC_TAWOS = (
    "id: rs-a\n"
    "scenario: estimation_tawos\n"
    "sample_size: 10\n"
    "models: [qwen2.5:3b]\n"
    "adaptation:\n"
    "  strategy: [few-shot-3]\n"
    "  cot: [false]\n"
    "inference:\n"
    "  temperature: 0.0\n"
    "  seed: 42\n"
    "sustainability:\n"
    "  codecarbon: true\n"
    "  country_iso: ESP\n"
)
_SPEC_TRIAGE = (
    "id: rs-b\n"
    "scenario: triage_jira\n"
    "sample_size: 10\n"
    "models: [mistral:7b]\n"
    "adaptation:\n"
    "  strategy: [zero-shot]\n"
    "  cot: [false]\n"
    "inference:\n"
    "  temperature: 0.0\n"
    "  seed: 42\n"
    "sustainability:\n"
    "  codecarbon: true\n"
    "  country_iso: ESP\n"
)


@pytest.fixture
def populated_db(in_memory_db: SessionFactory) -> SessionFactory:
    """Seed three runs A/B/C as described in the prompt's Step 5.

    * Run A — done, ``qwen2.5:3b`` / ``few-shot-3`` / ``estimation_tawos``.
    * Run B — done, ``mistral:7b`` / ``zero-shot`` / ``triage_jira``.
    * Run C — error, no metrics, no emissions, no predictions.
    """
    started = datetime(2026, 5, 10, 9, 0, tzinfo=UTC)
    finished = datetime(2026, 5, 10, 9, 30, tzinfo=UTC)

    with in_memory_db() as session:
        instances_tawos = _make_instances(session, "tawos", 10)
        instances_jira = _make_instances(session, "jira_triage", 10)

        session.add(
            Run(
                run_id="run-A",
                spec_hash="aaaaaaaa11111111",
                spec_yaml=_SPEC_TAWOS,
                profile="gpu-entry",
                started_at=started,
                finished_at=finished,
                status="done",
            )
        )
        _add_predictions(
            session,
            run_id="run-A",
            instance_ids=instances_tawos,
            model="qwen2.5:3b",
            strategy="few-shot-3",
        )
        _add_metrics(session, run_id="run-A", kind="effort")
        _add_emission(session, run_id="run-A")
        _add_snapshot(session, run_id="run-A")

        session.add(
            Run(
                run_id="run-B",
                spec_hash="bbbbbbbb22222222",
                spec_yaml=_SPEC_TRIAGE,
                profile="gpu-entry",
                started_at=started,
                finished_at=finished,
                status="done",
            )
        )
        _add_predictions(
            session,
            run_id="run-B",
            instance_ids=instances_jira,
            model="mistral:7b",
            strategy="zero-shot",
        )
        _add_metrics(session, run_id="run-B", kind="triage")
        _add_emission(session, run_id="run-B")
        _add_snapshot(session, run_id="run-B")

        session.add(
            Run(
                run_id="run-C",
                spec_hash="cccccccc33333333",
                spec_yaml=_SPEC_TAWOS,
                profile=None,
                started_at=started,
                finished_at=None,
                status="error",
            )
        )
        session.commit()

    return in_memory_db


def add_run(
    session: Session,
    *,
    run_id: str,
    spec_yaml: str,
    profile: str | None = "gpu-entry",
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    status: str = "done",
) -> None:
    """Helper for tests that need to insert custom runs."""
    session.add(
        Run(
            run_id=run_id,
            spec_hash=run_id.replace("-", "")[:16].ljust(16, "0"),
            spec_yaml=spec_yaml,
            profile=profile,
            started_at=started_at or datetime(2026, 5, 10, 9, 0, tzinfo=UTC),
            finished_at=finished_at or datetime(2026, 5, 10, 9, 30, tzinfo=UTC),
            status=status,
        )
    )


def add_full_run(
    session: Session,
    *,
    run_id: str,
    model: str,
    strategy: str,
    scenario: str,
    dataset: str = "tawos",
    n_instances: int = 5,
    metric_kind: str = "effort",
) -> None:
    """Insert a complete run with predictions/metrics/emissions/snapshot."""
    spec = (
        f"id: {run_id}\n"
        f"scenario: {scenario}\n"
        f"sample_size: {n_instances}\n"
        f"models: [{model}]\n"
        "adaptation:\n"
        f"  strategy: [{strategy}]\n"
        "  cot: [false]\n"
        "inference:\n"
        "  temperature: 0.0\n"
        "  seed: 42\n"
        "sustainability:\n"
        "  codecarbon: true\n"
        "  country_iso: ESP\n"
    )
    add_run(session, run_id=run_id, spec_yaml=spec)
    inst_ids = _make_instances(session, f"{dataset}-{run_id}", n_instances)
    _add_predictions(
        session,
        run_id=run_id,
        instance_ids=inst_ids,
        model=model,
        strategy=strategy,
    )
    _add_metrics(session, run_id=run_id, kind=metric_kind)
    _add_emission(session, run_id=run_id)
    _add_snapshot(session, run_id=run_id)


SAMPLE_VALID_PAYLOAD: dict[str, Any] = {
    "schema_version": "1.0.0",
    "submitter": {
        "name_or_alias": "alice_42",
        "affiliation": "Open Research Lab",
        "contact": None,
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
    "metrics": {"f1_macro": 0.5867, "accuracy": 0.62},
    "sustainability": {
        "codecarbon_version": "2.4.1",
        "co2_grams_total": 12.5,
        "energy_kwh_total": 0.03,
        "tracking_mode": "machine",
        "country_iso": "ESP",
    },
    "integrity": {"predictions_summary_hash": "a" * 64},
}
