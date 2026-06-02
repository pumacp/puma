"""Deterministic predictions hash for PUMA Community submissions.

Computes a SHA-256 over a canonical CSV serialization of the predictions joined
to instances for a given run. The hash is stable across machines, Python
versions, and database row-insertion order. This module is strictly read-only
with respect to the database: only SELECT statements are issued.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from puma.storage.models import Instance, Prediction, Run

log = logging.getLogger("puma.community.integrity")


class IntegrityError(Exception):
    """Base class for integrity failures."""


class RunNotFoundError(IntegrityError):
    """The supplied run_id is not present in the runs table."""


class EmptyPredictionsError(IntegrityError):
    """The supplied run_id has no predictions to hash."""


_COLUMNS: tuple[str, ...] = (
    "instance_id",
    "predicted_label",
    "predicted_value",
    "prompt_hash",
)


def _serialize_value(value: Any) -> str:
    """Canonical serialization of a single CSV cell.

    Floats use six decimal places (no scientific notation). ``None`` becomes
    the empty string. Everything else is coerced via ``str()``.
    """
    if value is None:
        return ""
    if isinstance(value, float):
        return format(value, ".6f")
    return str(value)


def compute_predictions_hash(*, session: Session, run_id: str) -> str:
    """Return the deterministic SHA-256 hash of a run's predictions.

    Columns (alphabetical, fixed): ``instance_id``, ``predicted_label``,
    ``predicted_value``, ``prompt_hash``. ``predicted_label`` is sourced from
    ``Prediction.parsed_label``; ``predicted_value`` from ``Prediction.confidence``.
    Rows are ordered by ``instance_id`` ASCENDING so the hash is independent of
    insertion order. CSV is RFC 4180 with LF line endings and no trailing
    newline; the UTF-8-encoded bytes feed ``hashlib.sha256``.
    """
    run_exists = session.execute(
        select(Run.run_id).where(Run.run_id == run_id)
    ).scalar_one_or_none()
    if run_exists is None:
        raise RunNotFoundError(f"run_id {run_id!r} not found")

    stmt = (
        select(
            Instance.instance_id,
            Prediction.parsed_label,
            Prediction.confidence,
            Prediction.prompt_hash,
        )
        .join(Instance, Prediction.instance_id == Instance.instance_id)
        .where(Prediction.run_id == run_id)
        .order_by(Instance.instance_id.asc())
    )
    rows = session.execute(stmt).all()
    if not rows:
        raise EmptyPredictionsError(f"run_id {run_id!r} has no predictions to hash")

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    for row in rows:
        writer.writerow([_serialize_value(v) for v in row])
    csv_text = buf.getvalue().rstrip("\n")
    return hashlib.sha256(csv_text.encode("utf-8")).hexdigest()


def verify_predictions_hash(*, session: Session, run_id: str, expected_hash: str) -> bool:
    """Recompute the run's hash and compare to ``expected_hash`` (case-insensitive)."""
    return compute_predictions_hash(session=session, run_id=run_id) == expected_hash.lower()


def export_predictions_jsonl(*, session: Session, run_id: str, target: Path) -> int:
    """Write a run's predictions to a canonical JSONL file at ``target`` (D27).

    Productizes the predictions artifact that ``puma community verify-hash`` and
    ``validate --strict`` consume. Each line is a JSON object whose keys are
    exactly ``_COLUMNS`` (``instance_id``, ``predicted_label``,
    ``predicted_value``, ``prompt_hash``) in that order, drawn from the SAME
    SELECT (same join, same ``instance_id``-ascending order) that
    :func:`compute_predictions_hash` uses. There is no trailing newline after
    the final record.

    Contract: the file this writes hashes — via
    :func:`puma.community.verify_cli.hash_predictions_jsonl` — to the exact
    value :func:`compute_predictions_hash` returns for the same ``run_id``.
    The exporter and the canonical hash share the ``_COLUMNS`` contract; the
    equivalence is enforced by ``tests/unit/test_predictions_exporter.py``.
    This function does not modify the hash semantics, the schema, or the
    Verifier — it is purely a producer for a format the codebase already
    consumes. Returns the number of records written.
    """
    run_exists = session.execute(
        select(Run.run_id).where(Run.run_id == run_id)
    ).scalar_one_or_none()
    if run_exists is None:
        raise RunNotFoundError(f"run_id {run_id!r} not found")

    stmt = (
        select(
            Instance.instance_id,
            Prediction.parsed_label,
            Prediction.confidence,
            Prediction.prompt_hash,
        )
        .join(Instance, Prediction.instance_id == Instance.instance_id)
        .where(Prediction.run_id == run_id)
        .order_by(Instance.instance_id.asc())
    )
    rows = session.execute(stmt).all()
    if not rows:
        raise EmptyPredictionsError(f"run_id {run_id!r} has no predictions to export")

    lines = [
        json.dumps(
            dict(zip(_COLUMNS, tuple(row), strict=True)),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=False,
        )
        for row in rows
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return len(rows)


__all__ = [
    "EmptyPredictionsError",
    "IntegrityError",
    "RunNotFoundError",
    "compute_predictions_hash",
    "export_predictions_jsonl",
    "verify_predictions_hash",
]
