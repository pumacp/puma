"""Tests for the deterministic predictions hash."""

from __future__ import annotations

import re

import pytest
from sqlalchemy import update

from puma.community.integrity import (
    EmptyPredictionsError,
    RunNotFoundError,
    compute_predictions_hash,
    verify_predictions_hash,
)
from puma.storage.models import Prediction
from tests.community.conftest import _make_instances, add_run


def test_compute_hash_is_deterministic(populated_db):
    """Hash is identical across multiple invocations on the same DB state."""
    hashes: set[str] = set()
    for _ in range(5):
        with populated_db() as session:
            hashes.add(compute_predictions_hash(session=session, run_id="run-A"))
    assert len(hashes) == 1


def test_compute_hash_changes_if_prediction_changes(populated_db):
    with populated_db() as session:
        before = compute_predictions_hash(session=session, run_id="run-A")
    with populated_db() as session:
        session.execute(
            update(Prediction)
            .where(Prediction.run_id == "run-A")
            .where(Prediction.instance_id == "tawos-inst-000")
            .values(parsed_label="MUTATED")
        )
        session.commit()
        after = compute_predictions_hash(session=session, run_id="run-A")
    assert before != after


def test_compute_hash_independent_of_insertion_order(in_memory_db):
    """Two runs with identical per-instance prediction values but reversed
    pred_id insertion order must yield the same hash, because the implementation
    orders by instance_id ASC."""

    def _payload_for(iid: str, i: int) -> dict:
        return {
            "instance_id": iid,
            "model": "qwen2.5:3b",
            "strategy": "zero-shot",
            "prompt_hash": f"ph{i:04d}",
            "raw_response": f"resp-{i}",
            "parsed_label": f"L{i % 3}",
            "confidence": 0.5 + i * 0.01,
            "latency_ms": 100.0 + i,
            "tokens_in": 100,
            "tokens_out": 50,
        }

    with in_memory_db() as session:
        instance_ids = _make_instances(session, "ord", 5)
        payloads = [_payload_for(iid, i) for i, iid in enumerate(instance_ids)]

        add_run(session, run_id="run-fwd", spec_yaml="scenario: estimation_tawos\n")
        for p in payloads:
            session.add(Prediction(run_id="run-fwd", **p))

        add_run(session, run_id="run-rev", spec_yaml="scenario: estimation_tawos\n")
        for p in reversed(payloads):
            session.add(Prediction(run_id="run-rev", **p))
        session.commit()

        hash_forward = compute_predictions_hash(session=session, run_id="run-fwd")
        hash_reverse = compute_predictions_hash(session=session, run_id="run-rev")

    assert hash_forward == hash_reverse


def test_compute_hash_format_is_lowercase_hex_64(populated_db):
    with populated_db() as session:
        digest = compute_predictions_hash(session=session, run_id="run-A")
    assert re.fullmatch(r"[a-f0-9]{64}", digest)


def test_compute_hash_missing_run_raises(populated_db):
    with populated_db() as session:
        with pytest.raises(RunNotFoundError):
            compute_predictions_hash(session=session, run_id="run-does-not-exist")


def test_compute_hash_empty_predictions_raises(populated_db):
    with populated_db() as session:
        with pytest.raises(EmptyPredictionsError):
            compute_predictions_hash(session=session, run_id="run-C")


def test_verify_hash_matches_when_correct(populated_db):
    with populated_db() as session:
        digest = compute_predictions_hash(session=session, run_id="run-A")
        assert verify_predictions_hash(session=session, run_id="run-A", expected_hash=digest)


def test_verify_hash_mismatches_when_db_tampered(populated_db):
    with populated_db() as session:
        original = compute_predictions_hash(session=session, run_id="run-A")
    with populated_db() as session:
        session.execute(
            update(Prediction)
            .where(Prediction.run_id == "run-A")
            .where(Prediction.instance_id == "tawos-inst-005")
            .values(confidence=0.99999)
        )
        session.commit()
        assert not verify_predictions_hash(session=session, run_id="run-A", expected_hash=original)
