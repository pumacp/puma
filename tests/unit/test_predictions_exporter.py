"""Unit tests for the predictions JSONL exporter (D27).

Covers ``puma.community.integrity.export_predictions_jsonl``: file structure,
the central byte-equality contract with the canonical hash, NULL handling, the
no-trailing-newline guard, and canonical column order / sort enforcement.
"""

from __future__ import annotations

import json
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from puma.community.integrity import (
    _COLUMNS,
    compute_predictions_hash,
    export_predictions_jsonl,
)
from puma.community.verify_cli import hash_predictions_jsonl
from puma.storage.models import Base, Prediction
from tests.community.conftest import _make_instances, add_run

_RUN_ID = "run-exp"


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with factory() as s:
        yield s
    engine.dispose()


def _seed(session, *, n=4, reverse=False, null_value_at=None):
    """Seed a run with ``n`` triage predictions. Returns the instance ids."""
    instance_ids = _make_instances(session, "jira_triage", n)
    add_run(session, run_id=_RUN_ID, spec_yaml="scenario: triage_jira\n")
    order = list(enumerate(instance_ids))
    if reverse:
        order = list(reversed(order))
    for i, iid in order:
        confidence = None if i == null_value_at else 0.5 + i * 0.01
        session.add(
            Prediction(
                run_id=_RUN_ID,
                instance_id=iid,
                model="qwen2.5:3b",
                strategy="contextual-anchoring",
                prompt_hash=f"ph{i:04d}",
                raw_response=f"resp-{i}",
                parsed_label=f"L{i % 3}",
                confidence=confidence,
                latency_ms=100.0 + i,
                tokens_in=100,
                tokens_out=50,
            )
        )
    session.commit()
    return instance_ids


@pytest.mark.unit
class TestPredictionsExporter:
    def test_exporter_writes_jsonl(self, session, tmp_path):
        # Guard: the canonical column identity itself must not drift.
        assert _COLUMNS == ("instance_id", "predicted_label", "predicted_value", "prompt_hash")
        _seed(session, n=3)
        target = tmp_path / "sub.predictions.jsonl"
        written = export_predictions_jsonl(session=session, run_id=_RUN_ID, target=target)
        assert written == 3
        assert target.is_file()
        lines = target.read_text(encoding="utf-8").split("\n")
        assert len(lines) == 3
        for line in lines:
            obj = json.loads(line)
            assert list(obj.keys()) == list(_COLUMNS)

    def test_exporter_byte_equals_hash(self, session, tmp_path):
        """Central contract: the JSONL hashes to the canonical DB hash."""
        _seed(session, n=6)
        target = tmp_path / "sub.predictions.jsonl"
        export_predictions_jsonl(session=session, run_id=_RUN_ID, target=target)
        assert hash_predictions_jsonl(target) == compute_predictions_hash(
            session=session, run_id=_RUN_ID
        )

    def test_exporter_handles_null_predicted_value(self, session, tmp_path):
        _seed(session, n=4, null_value_at=2)
        target = tmp_path / "sub.predictions.jsonl"
        export_predictions_jsonl(session=session, run_id=_RUN_ID, target=target)
        objs = [json.loads(line) for line in target.read_text(encoding="utf-8").split("\n")]
        assert any(o["predicted_value"] is None for o in objs)
        # NULL serializes as JSON null and the hash equivalence still holds.
        assert hash_predictions_jsonl(target) == compute_predictions_hash(
            session=session, run_id=_RUN_ID
        )

    def test_exporter_no_trailing_newline(self, session, tmp_path):
        _seed(session, n=3)
        target = tmp_path / "sub.predictions.jsonl"
        export_predictions_jsonl(session=session, run_id=_RUN_ID, target=target)
        assert not target.read_bytes().endswith(b"\n")

    def test_exporter_column_order_and_sort(self, session, tmp_path):
        ids = _seed(session, n=5, reverse=True)
        target = tmp_path / "sub.predictions.jsonl"
        export_predictions_jsonl(session=session, run_id=_RUN_ID, target=target)
        objs = [json.loads(line) for line in target.read_text(encoding="utf-8").split("\n")]
        for obj in objs:
            assert list(obj.keys()) == list(_COLUMNS)
        # Rows are sorted ascending by instance_id regardless of insertion order.
        assert [o["instance_id"] for o in objs] == sorted(ids)
