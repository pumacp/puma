"""Read-only data access helpers for the PUMA dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

_DEFAULT_DB = Path("data/puma.db")


def _engine(db_path: Path):
    from sqlalchemy import create_engine

    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def load_runs(db_path: Path = _DEFAULT_DB) -> pd.DataFrame:
    """Return all runs as a DataFrame, newest first."""
    if not db_path.exists():
        return pd.DataFrame(columns=["run_id", "spec_hash", "profile", "started_at",
                                     "finished_at", "status"])
    engine = _engine(db_path)
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM runs ORDER BY started_at DESC", conn)
    return df


def load_metrics(db_path: Path = _DEFAULT_DB, run_ids: list[str] | None = None) -> pd.DataFrame:
    """Return metrics, optionally filtered to specific run_ids."""
    if not db_path.exists():
        return pd.DataFrame(columns=["run_id", "metric_name", "value", "scope"])
    engine = _engine(db_path)
    with engine.connect() as conn:
        if run_ids:
            placeholders = ",".join(f"'{r}'" for r in run_ids)
            df = pd.read_sql(
                f"SELECT * FROM metrics WHERE run_id IN ({placeholders})", conn
            )
        else:
            df = pd.read_sql("SELECT * FROM metrics", conn)
    return df


def load_predictions(
    db_path: Path = _DEFAULT_DB, run_id: str | None = None
) -> pd.DataFrame:
    """Return predictions for a run, or all predictions."""
    if not db_path.exists():
        return pd.DataFrame()
    engine = _engine(db_path)
    with engine.connect() as conn:
        if run_id:
            df = pd.read_sql(
                "SELECT * FROM predictions WHERE run_id = ?", conn, params=(run_id,)
            )
        else:
            df = pd.read_sql("SELECT * FROM predictions", conn)
    return df


def load_profile_snapshots(db_path: Path = _DEFAULT_DB) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    engine = _engine(db_path)
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM profile_snapshots", conn)


def metrics_pivot(db_path: Path = _DEFAULT_DB) -> pd.DataFrame:
    """Return a run × metric pivot table (useful for heatmaps)."""
    df = load_metrics(db_path)
    if df.empty:
        return pd.DataFrame()
    return df.pivot_table(index="run_id", columns="metric_name", values="value", aggfunc="first")


def run_summary(db_path: Path = _DEFAULT_DB) -> list[dict[str, Any]]:
    """Return one dict per run with key metrics merged."""
    runs = load_runs(db_path)
    metrics = load_metrics(db_path)
    if runs.empty:
        return []
    summaries = []
    for _, row in runs.iterrows():
        m = metrics[metrics["run_id"] == row["run_id"]]
        d: dict[str, Any] = row.to_dict()
        d.update({r["metric_name"]: r["value"] for _, r in m.iterrows()})
        summaries.append(d)
    return summaries
