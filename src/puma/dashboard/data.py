"""Read-only data access helpers for the PUMA dashboard.

All loaders are cached via ``st.cache_data`` (TTL 60 s). Distinct
``db_path`` arguments produce distinct cache entries, so test fixtures
using ``tmp_path`` are not affected by cached production data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

_DEFAULT_DB = Path("data/puma.db")


def _engine(db_path: Path):
    from sqlalchemy import create_engine

    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


@st.cache_data(ttl=60, show_spinner=False)
def load_runs(db_path: Path = _DEFAULT_DB) -> pd.DataFrame:
    """Return all runs as a DataFrame, newest first."""
    if not db_path.exists():
        return pd.DataFrame(
            columns=["run_id", "spec_hash", "profile", "started_at", "finished_at", "status"]
        )
    engine = _engine(db_path)
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM runs ORDER BY started_at DESC", conn)
    return df


@st.cache_data(ttl=60, show_spinner=False)
def load_metrics(db_path: Path = _DEFAULT_DB, run_ids: list[str] | None = None) -> pd.DataFrame:
    """Return metrics, optionally filtered to specific run_ids."""
    if not db_path.exists():
        return pd.DataFrame(columns=["run_id", "metric_name", "value", "scope"])
    engine = _engine(db_path)
    with engine.connect() as conn:
        if run_ids:
            placeholders = ",".join(f"'{r}'" for r in run_ids)
            df = pd.read_sql(f"SELECT * FROM metrics WHERE run_id IN ({placeholders})", conn)
        else:
            df = pd.read_sql("SELECT * FROM metrics", conn)
    return df


@st.cache_data(ttl=60, show_spinner=False)
def load_predictions(db_path: Path = _DEFAULT_DB, run_id: str | None = None) -> pd.DataFrame:
    """Return predictions for a run, or all predictions."""
    if not db_path.exists():
        return pd.DataFrame()
    engine = _engine(db_path)
    with engine.connect() as conn:
        if run_id:
            df = pd.read_sql("SELECT * FROM predictions WHERE run_id = ?", conn, params=(run_id,))
        else:
            df = pd.read_sql("SELECT * FROM predictions", conn)
    return df


@st.cache_data(ttl=60, show_spinner=False)
def load_predictions_with_gold(
    db_path: Path = _DEFAULT_DB,
    run_id: str | None = None,
    model: str | None = None,
    dataset: str | None = None,
) -> pd.DataFrame:
    """Predictions LEFT JOIN instances — exposes gold_label + input_text.

    `gold_label` and `input_text` live in `instances`, not `predictions`.
    Views that need either column must go through this loader.
    """
    if not db_path.exists():
        return pd.DataFrame()

    sql = """
        SELECT
            p.run_id,
            p.instance_id,
            p.model,
            p.strategy,
            p.parsed_label,
            p.confidence,
            p.logprobs_json,
            p.latency_ms,
            p.tokens_in,
            p.tokens_out,
            p.perturbation,
            p.seed,
            p.prompt_hash,
            p.raw_response,
            i.gold_label,
            i.input_text,
            i.dataset,
            i.source_id
        FROM predictions p
        LEFT JOIN instances i ON p.instance_id = i.instance_id
        WHERE 1=1
    """
    params: dict[str, str] = {}
    if run_id:
        sql += " AND p.run_id = :run_id"
        params["run_id"] = run_id
    if model:
        sql += " AND p.model = :model"
        params["model"] = model
    if dataset:
        sql += " AND i.dataset = :dataset"
        params["dataset"] = dataset

    engine = _engine(db_path)
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


@st.cache_data(ttl=60, show_spinner=False)
def load_profile_snapshots(db_path: Path = _DEFAULT_DB) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    engine = _engine(db_path)
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM profile_snapshots", conn)


@st.cache_data(ttl=60, show_spinner=False)
def metrics_pivot(db_path: Path = _DEFAULT_DB) -> pd.DataFrame:
    """Return a run × metric pivot table (useful for heatmaps)."""  # noqa: RUF002 -- intentional Unicode multiplication sign in formula docstring
    df = load_metrics(db_path)
    if df.empty:
        return pd.DataFrame()
    return df.pivot_table(index="run_id", columns="metric_name", values="value", aggfunc="first")


@st.cache_data(ttl=60, show_spinner=False)
def load_emissions(db_path: Path = _DEFAULT_DB) -> pd.DataFrame:
    """Return CodeCarbon emissions per run (kWh, CO2 kg, energy breakdowns)."""
    if not db_path.exists():
        return pd.DataFrame()
    engine = _engine(db_path)
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM emissions", conn)


@st.cache_data(ttl=60, show_spinner=False)
def load_sustainability(db_path: Path = _DEFAULT_DB) -> pd.DataFrame:
    """Per-run quality × cost view: model + f1_macro + ece + co2 + kwh + duration.

    Joins runs, emissions, metrics (pivoted), and the first model seen in
    predictions per run (puma runs are single-model in v2.1).
    """  # noqa: RUF002 -- intentional Unicode multiplication sign in formula docstring
    if not db_path.exists():
        return pd.DataFrame()

    engine = _engine(db_path)
    with engine.connect() as conn:
        runs = pd.read_sql("SELECT run_id, started_at, profile FROM runs", conn)
        emissions = pd.read_sql(
            "SELECT run_id, kwh, co2_kg, duration_s, gpu_energy, cpu_energy FROM emissions",
            conn,
        )
        metrics = pd.read_sql(
            "SELECT run_id, metric_name, value FROM metrics "
            "WHERE metric_name IN ('f1_macro', 'accuracy', 'ece', 'parse_failure_rate', 'latency.p95')",
            conn,
        )
        models = pd.read_sql(
            "SELECT run_id, MIN(model) AS model FROM predictions GROUP BY run_id",
            conn,
        )

    if runs.empty:
        return pd.DataFrame()

    metrics_pivot = metrics.pivot_table(
        index="run_id", columns="metric_name", values="value", aggfunc="first"
    ).reset_index()

    out = (
        runs.merge(models, on="run_id", how="left")
        .merge(metrics_pivot, on="run_id", how="left")
        .merge(emissions, on="run_id", how="left")
    )
    if "co2_kg" in out.columns:
        out["co2_g"] = out["co2_kg"] * 1000.0
    return out


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
