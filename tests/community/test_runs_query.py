"""Tests for the read-only runs_query module."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime

import pytest

from puma.community import runs_query
from puma.community.runs_query import get_run_summary, list_shareable_runs
from tests.community.conftest import (
    _add_emission,
    _add_metrics,
    _add_predictions,
    _add_snapshot,
    _make_instances,
    add_run,
)


@pytest.fixture
def patched_session_scope(populated_db, monkeypatch):
    """Route ``runs_query.session_scope`` through ``populated_db``."""

    @contextmanager
    def fake_scope():
        session = populated_db()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(runs_query, "session_scope", fake_scope)
    return populated_db


def test_lists_only_done_runs(patched_session_scope):
    rows = list_shareable_runs(min_predictions=1)
    run_ids = {r.run_id for r in rows}
    assert "run-A" in run_ids
    assert "run-B" in run_ids
    assert "run-C" not in run_ids


def test_filters_runs_with_insufficient_predictions(patched_session_scope):
    rows = list_shareable_runs(min_predictions=50)
    assert rows == []


def test_filters_runs_without_metrics(patched_session_scope):
    with patched_session_scope() as session:
        spec = "scenario: estimation_tawos\n"
        add_run(session, run_id="run-no-metrics", spec_yaml=spec)
        iids = _make_instances(session, "no-metrics", 5)
        _add_predictions(
            session,
            run_id="run-no-metrics",
            instance_ids=iids,
            model="qwen2.5:3b",
            strategy="zero-shot",
        )
        _add_emission(session, run_id="run-no-metrics")
        _add_snapshot(session, run_id="run-no-metrics")
        session.commit()

    rows = list_shareable_runs(min_predictions=1)
    run_ids = {r.run_id for r in rows}
    assert "run-no-metrics" not in run_ids


def test_filters_runs_without_emissions(patched_session_scope):
    with patched_session_scope() as session:
        spec = "scenario: estimation_tawos\n"
        add_run(session, run_id="run-no-em", spec_yaml=spec)
        iids = _make_instances(session, "no-em", 5)
        _add_predictions(
            session,
            run_id="run-no-em",
            instance_ids=iids,
            model="qwen2.5:3b",
            strategy="zero-shot",
        )
        _add_metrics(session, run_id="run-no-em", kind="effort")
        _add_snapshot(session, run_id="run-no-em")
        session.commit()

    rows = list_shareable_runs(min_predictions=1)
    run_ids = {r.run_id for r in rows}
    assert "run-no-em" not in run_ids


def test_get_run_summary_for_existing_run(patched_session_scope):
    summary = get_run_summary("run-A")
    assert summary is not None
    assert summary.run_id == "run-A"
    assert summary.scenario == "estimation_tawos"
    assert summary.model == "qwen2.5:3b"
    assert summary.strategy == "few-shot-3"
    assert summary.has_metrics is True
    assert summary.has_emissions is True


def test_get_run_summary_returns_none_for_unknown_or_non_done(patched_session_scope):
    assert get_run_summary("does-not-exist") is None
    # run-C has status "error", not "done"
    assert get_run_summary("run-C") is None


def test_summary_orders_by_finished_at_desc(patched_session_scope):
    with patched_session_scope() as session:
        older_finish = datetime(2025, 1, 1, tzinfo=UTC)
        spec = "scenario: estimation_tawos\n"
        add_run(
            session,
            run_id="run-old",
            spec_yaml=spec,
            finished_at=older_finish,
        )
        iids = _make_instances(session, "old", 5)
        _add_predictions(
            session,
            run_id="run-old",
            instance_ids=iids,
            model="qwen2.5:3b",
            strategy="zero-shot",
        )
        _add_metrics(session, run_id="run-old", kind="effort")
        _add_emission(session, run_id="run-old")
        _add_snapshot(session, run_id="run-old")
        session.commit()

    rows = list_shareable_runs(min_predictions=1)
    finished_ats = [r.finished_at for r in rows]
    # newest first
    assert finished_ats == sorted(finished_ats, reverse=True)
