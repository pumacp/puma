"""Read-only data access helpers for the PUMA dashboard.

All loaders are cached via ``st.cache_data`` (TTL 60 s). Distinct
``db_path`` arguments produce distinct cache entries, so test fixtures
using ``tmp_path`` are not affected by cached production data.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import Engine

_DEFAULT_DB = Path("data/puma.db")


def _engine(db_path: Path) -> Engine:
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


_MULTI_MODEL_COLUMNS = [
    "f1_macro",
    "mae",
    "accuracy",
    "p50_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "total_carbon_gco2eq",
    "predictions_summary_hash",
    "run_count",
]


def _metric_mean(frame: pd.DataFrame, name: str) -> float:
    """Mean of a single ``metric_name`` across the rows in ``frame`` (NaN if absent)."""
    vals = frame.loc[frame["metric_name"] == name, "value"]
    return float(vals.mean()) if not vals.empty else float("nan")


def get_multi_model_results(
    scenario_id: str,
    model_ids: list[str],
    db_path: Path = _DEFAULT_DB,
) -> pd.DataFrame:
    """Aggregate per-model results for a single scenario, for side-by-side comparison.

    Reads persisted SQLite results only (no live inference). Returns a DataFrame
    indexed by ``model`` (one row per requested model, preserving order) with the
    columns in :data:`_MULTI_MODEL_COLUMNS`. A model with no runs for the scenario
    yields a row of ``NaN``/``0`` (``run_count == 0``) rather than raising.

    ``predictions_summary_hash`` is a per-run reproducibility fingerprint over the
    ordered ``(instance_id, parsed_label)`` pairs: when every run of a model on the
    scenario shares one fingerprint the value is that hash (deterministic); when
    they diverge it is ``"varies (<n>)"``.
    """
    empty = pd.DataFrame(columns=_MULTI_MODEL_COLUMNS, index=pd.Index([], name="model"))
    if not db_path.exists():
        return empty

    engine = _engine(db_path)
    with engine.connect() as conn:
        run_model = pd.read_sql(
            "SELECT DISTINCT p.run_id, p.model FROM predictions p "
            "JOIN instances i ON p.instance_id = i.instance_id WHERE i.dataset = :scn",
            conn,
            params={"scn": scenario_id},
        )
        metrics = pd.read_sql("SELECT run_id, metric_name, value FROM metrics", conn)
        emissions = pd.read_sql("SELECT run_id, co2_kg FROM emissions", conn)
        preds = pd.read_sql(
            "SELECT p.run_id, p.instance_id, p.parsed_label FROM predictions p "
            "JOIN instances i ON p.instance_id = i.instance_id WHERE i.dataset = :scn",
            conn,
            params={"scn": scenario_id},
        )

    def _fingerprint(run_id: str) -> str:
        pr = preds[preds["run_id"] == run_id].sort_values("instance_id")
        payload = "\n".join(
            f"{a}|{b}" for a, b in zip(pr["instance_id"], pr["parsed_label"], strict=True)
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    rows: list[dict[str, Any]] = []
    for model in model_ids:
        run_ids = run_model.loc[run_model["model"] == model, "run_id"].unique().tolist()
        if not run_ids:
            rows.append({"model": model, "run_count": 0, "predictions_summary_hash": None})
            continue

        mm = metrics[metrics["run_id"].isin(run_ids)]
        carbon = emissions.loc[emissions["run_id"].isin(run_ids), "co2_kg"]
        fingerprints = {_fingerprint(r) for r in run_ids}
        fp = next(iter(fingerprints)) if len(fingerprints) == 1 else f"varies ({len(fingerprints)})"

        rows.append(
            {
                "model": model,
                "f1_macro": _metric_mean(mm, "f1_macro"),
                "mae": _metric_mean(mm, "mae"),
                "accuracy": _metric_mean(mm, "accuracy"),
                "p50_latency_ms": _metric_mean(mm, "latency.p50"),
                "p95_latency_ms": _metric_mean(mm, "latency.p95"),
                "p99_latency_ms": _metric_mean(mm, "latency.p99"),
                "total_carbon_gco2eq": (
                    float(carbon.mean() * 1000.0) if not carbon.empty else float("nan")
                ),
                "predictions_summary_hash": fp,
                "run_count": len(run_ids),
            }
        )

    df = pd.DataFrame(rows).set_index("model")
    # Guarantee all documented columns exist even if every model row was empty.
    for col in _MULTI_MODEL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[_MULTI_MODEL_COLUMNS]


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
