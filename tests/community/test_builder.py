"""Tests for the Submission builder."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest
from sqlalchemy import update

from puma.community import builder as builder_mod
from puma.community.builder import (
    ExcludedModelError,
    IncompleteRunError,
    PIIDetectedError,
    RunNotFoundError,
    UnknownScenarioError,
    UnknownStrategyError,
    _percentiles,
    _translate_scenario,
    _translate_strategy,
    build_submission_from_run,
    list_shareable_runs,
)
from puma.community.schema import Submission
from puma.storage.models import ProfileSnapshot, Run
from tests.community.conftest import add_full_run


def test_build_from_completed_run_succeeds(populated_db, valid_submitter):
    with populated_db() as session:
        submission = build_submission_from_run(
            run_id="run-A", submitter=valid_submitter, session=session
        )
    assert isinstance(submission, Submission)
    assert submission.run_metadata.scenario == "effort_tawos"
    assert submission.run_metadata.strategy == "few_shot_3"
    assert submission.run_metadata.model == "qwen2.5:3b"
    assert submission.metrics.mae == pytest.approx(4.2)
    assert submission.metrics.accuracy == pytest.approx(0.70)
    assert submission.hardware_profile.cpu_cores == 12


def test_missing_run_raises_run_not_found(populated_db, valid_submitter):
    with populated_db() as session:
        with pytest.raises(RunNotFoundError):
            build_submission_from_run(
                run_id="does-not-exist", submitter=valid_submitter, session=session
            )


def test_incomplete_run_no_metrics_raises_incomplete(populated_db, valid_submitter):
    with populated_db() as session:
        with pytest.raises(IncompleteRunError):
            build_submission_from_run(run_id="run-C", submitter=valid_submitter, session=session)


def test_failed_run_excluded_from_shareable(populated_db):
    with populated_db() as session:
        rows = list_shareable_runs(session=session)
    run_ids = {row["run_id"] for row in rows}
    assert "run-C" not in run_ids
    assert {"run-A", "run-B"}.issubset(run_ids)


def test_latency_percentiles_correct():
    latencies = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0, 190.0]
    total, p50, p95 = _percentiles(latencies)
    assert total == 1450
    assert p50 == 145
    assert p95 == 185


def test_list_shareable_runs_returns_metadata_keys(populated_db):
    with populated_db() as session:
        rows = list_shareable_runs(session=session)
    assert rows, "expected at least one shareable run"
    expected_keys = {
        "run_id",
        "scenario",
        "model",
        "strategy",
        "completed_at",
        "f1_macro",
        "mae",
        "accuracy",
        "co2_grams_total",
        "n_instances",
    }
    assert expected_keys.issubset(rows[0].keys())


def test_list_shareable_runs_empty_when_no_runs(in_memory_db):
    with in_memory_db() as session:
        rows = list_shareable_runs(session=session)
    assert rows == []


def test_pii_in_notes_raises_with_pattern_names(populated_db, valid_submitter):
    with populated_db() as session:
        with pytest.raises(PIIDetectedError) as exc:
            build_submission_from_run(
                run_id="run-A",
                submitter=valid_submitter,
                session=session,
                notes="please contact alice@example.com for follow-up",
            )
    assert "email" in exc.value.patterns


def test_build_uses_resolved_puma_version_from_git_tag(populated_db, valid_submitter, monkeypatch):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="v9.9.9\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    builder_mod._resolve_puma_version_from_git.cache_clear()

    with populated_db() as session:
        submission = build_submission_from_run(
            run_id="run-A", submitter=valid_submitter, session=session
        )
    assert submission.puma_version == "9.9.9"


def test_translate_scenario_estimation_to_effort():
    assert _translate_scenario("estimation_tawos") == "effort_tawos"
    assert _translate_scenario("triage_jira") == "triage_jira"
    assert _translate_scenario("prioritization_jira") == "prioritization_jira"
    with pytest.raises(UnknownScenarioError):
        _translate_scenario("bogus_scenario")


def test_translate_strategy_kebab_to_snake():
    assert _translate_strategy("zero-shot") == "zero_shot"
    assert _translate_strategy("cot-few-shot") == "cot_few_shot"
    assert _translate_strategy("self-consistency") == "self_consistency"
    assert _translate_strategy("rcoif") == "rcoif"
    with pytest.raises(UnknownStrategyError):
        _translate_strategy("non-existent-strategy")


def test_excluded_model_raises_excluded_model_error(populated_db, valid_submitter):
    with populated_db() as session:
        add_full_run(
            session,
            run_id="run-kimi",
            model="kimi-k2:6.0",
            strategy="zero-shot",
            scenario="triage_jira",
            metric_kind="triage",
            dataset="jira_triage",
        )
        session.commit()
        with pytest.raises(ExcludedModelError) as exc:
            build_submission_from_run(run_id="run-kimi", submitter=valid_submitter, session=session)
    assert exc.value.reason == "excluded"
    assert exc.value.model == "kimi-k2:6.0"


def test_pending_validation_model_raises_excluded_model_error(populated_db, valid_submitter):
    with populated_db() as session:
        add_full_run(
            session,
            run_id="run-qwen3",
            model="qwen3:30b",
            strategy="zero-shot",
            scenario="triage_jira",
            metric_kind="triage",
            dataset="jira_triage",
        )
        session.commit()
        with pytest.raises(ExcludedModelError) as exc:
            build_submission_from_run(
                run_id="run-qwen3", submitter=valid_submitter, session=session
            )
    assert exc.value.reason == "pending_validation"
    assert exc.value.model == "qwen3:30b"


def test_list_shareable_runs_filters_excluded_models(populated_db):
    with populated_db() as session:
        add_full_run(
            session,
            run_id="run-kimi",
            model="kimi-k2:6.0",
            strategy="zero-shot",
            scenario="triage_jira",
            metric_kind="triage",
            dataset="jira_triage",
        )
        add_full_run(
            session,
            run_id="run-qwen3",
            model="qwen3:30b",
            strategy="zero-shot",
            scenario="triage_jira",
            metric_kind="triage",
            dataset="jira_triage",
        )
        session.commit()
        rows = list_shareable_runs(session=session)
    run_ids = {row["run_id"] for row in rows}
    assert "run-kimi" not in run_ids
    assert "run-qwen3" not in run_ids


def test_build_falls_back_to_unknown_when_git_and_snapshot_fail(
    populated_db, valid_submitter, monkeypatch
):
    def failing_run(*args, **kwargs):
        return SimpleNamespace(returncode=128, stdout="", stderr="fatal")

    monkeypatch.setattr(subprocess, "run", failing_run)
    builder_mod._resolve_puma_version_from_git.cache_clear()

    with populated_db() as session:
        session.execute(
            update(ProfileSnapshot)
            .where(ProfileSnapshot.run_id == "run-A")
            .values(puma_version=None)
        )
        session.commit()
        submission = build_submission_from_run(
            run_id="run-A", submitter=valid_submitter, session=session
        )
    assert submission.puma_version == "0.0.0-unknown"


def test_unknown_scenario_in_runspec_raises(populated_db, valid_submitter):
    bad_spec = "id: rs\nscenario: not_a_real_scenario\n"
    with populated_db() as session:
        session.execute(update(Run).where(Run.run_id == "run-A").values(spec_yaml=bad_spec))
        session.commit()
        with pytest.raises(UnknownScenarioError):
            build_submission_from_run(run_id="run-A", submitter=valid_submitter, session=session)
