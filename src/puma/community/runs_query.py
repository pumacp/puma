"""Read-only runs query for ``puma share-results``.

Surfaces a typed ``ShareableRunSummary`` over PUMA's academic SQLite. Strictly
read-only — only SELECT statements are issued. The module reuses
``session_scope()`` from :mod:`puma.storage.db` so the rest of PUMA's
configuration (DB path, Alembic migrations) applies transparently.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from puma.storage.db import session_scope
from puma.storage.models import Emission, Metric, Prediction, Run

log = logging.getLogger("puma.community.runs_query")


@dataclass(frozen=True)
class ShareableRunSummary:
    run_id: str
    scenario: str
    model: str
    strategy: str
    n_predictions: int
    started_at: str
    finished_at: str | None
    has_metrics: bool
    has_emissions: bool


def _parse_scenario(spec_yaml: str | None) -> str:
    if not spec_yaml:
        return "unknown"
    try:
        parsed = yaml.safe_load(spec_yaml) or {}
    except yaml.YAMLError:
        return "unknown"
    if not isinstance(parsed, dict):
        return "unknown"
    return str(parsed.get("scenario") or "unknown")


def _summarise(session: Session, run: Run) -> ShareableRunSummary | None:
    """Build a ``ShareableRunSummary`` from a Run, or ``None`` if data is missing."""
    pred = session.execute(
        select(Prediction.model, Prediction.strategy)
        .where(Prediction.run_id == run.run_id)
        .limit(1)
    ).first()
    if pred is None:
        return None
    n_pred = session.execute(
        select(func.count(Prediction.pred_id)).where(Prediction.run_id == run.run_id)
    ).scalar_one()
    has_metrics = bool(
        session.execute(
            select(func.count(Metric.metric_id)).where(Metric.run_id == run.run_id)
        ).scalar_one()
    )
    has_emissions = bool(
        session.execute(
            select(func.count(Emission.emission_id)).where(Emission.run_id == run.run_id)
        ).scalar_one()
    )
    return ShareableRunSummary(
        run_id=run.run_id,
        scenario=_parse_scenario(run.spec_yaml),
        model=pred[0],
        strategy=pred[1],
        n_predictions=int(n_pred),
        started_at=run.started_at.isoformat() if run.started_at else "",
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        has_metrics=has_metrics,
        has_emissions=has_emissions,
    )


def list_shareable_runs(*, min_predictions: int = 10) -> list[ShareableRunSummary]:
    """Return summaries of runs eligible to share.

    A run is shareable when ``status == "done"``, it has at least ``min_predictions``
    predictions, and both a ``Metric`` row and an ``Emission`` row exist for it.
    """
    out: list[ShareableRunSummary] = []
    with session_scope() as session:
        runs = session.execute(select(Run).where(Run.status == "done")).scalars().all()
        for run in runs:
            summary = _summarise(session, run)
            if summary is None:
                continue
            if summary.n_predictions < min_predictions:
                continue
            if not summary.has_metrics or not summary.has_emissions:
                continue
            out.append(summary)
    out.sort(key=lambda s: s.finished_at or "", reverse=True)
    return out


def get_run_summary(run_id: str) -> ShareableRunSummary | None:
    """Return the summary for ``run_id`` if it exists and status is ``"done"``."""
    with session_scope() as session:
        run = session.execute(
            select(Run).where(Run.run_id == run_id, Run.status == "done")
        ).scalar_one_or_none()
        if run is None:
            return None
        return _summarise(session, run)


__all__ = ["ShareableRunSummary", "get_run_summary", "list_shareable_runs"]
