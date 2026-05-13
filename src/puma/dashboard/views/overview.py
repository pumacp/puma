"""Overview view: cohort summary cards and recent-runs expanders."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from puma.dashboard.components import empty_filtered_state, metric_card
from puma.dashboard.data import load_predictions, load_sustainability
from puma.dashboard.views._base import DB_PATH, no_data, selected_models, selected_runs


def _friendly_run_label(row: pd.Series) -> str:
    """Compact, scannable run identifier: ``model · YYYY-MM-DD · F1=0.XXX``."""
    model = row.get("model") or "?"
    started_at = row.get("started_at")
    date = str(started_at)[:10] if pd.notna(started_at) else "?"
    f1 = row.get("f1_macro")
    f1_str = f"F1={float(f1):.3f}" if pd.notna(f1) else "F1=n/a"
    return f"{model} · {date} · {f1_str}"


def render() -> None:
    st.title("📊 Overview")

    with st.spinner("Loading cohort data…"):
        sus = load_sustainability(DB_PATH)
    if sus.empty:
        no_data()
        return

    runs_filter = selected_runs()
    models_filter = selected_models()
    if runs_filter:
        sus = sus[sus["run_id"].isin(runs_filter)]
    if models_filter:
        sus = sus[sus["model"].isin(models_filter) | sus["model"].isna()]

    if sus.empty:
        empty_filtered_state("Overview")
        return

    st.subheader("Cohort summary")
    cols = st.columns(4)
    with cols[0]:
        metric_card("Runs", len(sus), fmt="{}", help="Number of completed runs matching filters")
        metric_card(
            "Unique models",
            int(sus["model"].dropna().nunique()),
            fmt="{}",
            help="Distinct model tags seen across the filtered runs",
        )
    with cols[1]:
        total_co2 = float(sus["co2_g"].sum()) if "co2_g" in sus.columns else 0.0
        metric_card(
            "Total CO₂ (g)",
            total_co2,
            fmt="{:.4f}",
            help="Cumulative CO₂eq across runs (CodeCarbon — CPU + RAM + GPU)",
        )
        total_kwh = float(sus["kwh"].sum()) if "kwh" in sus.columns else 0.0
        metric_card(
            "Total energy (kWh)",
            total_kwh,
            fmt="{:.6f}",
            help="Cumulative energy across runs (CodeCarbon)",
        )
    with cols[2]:
        avg_ece = sus["ece"].dropna().mean() if "ece" in sus.columns else float("nan")
        metric_card(
            "Avg ECE",
            float(avg_ece) if pd.notna(avg_ece) else "n/a",
            fmt="{:.4f}" if pd.notna(avg_ece) else "{}",
            help=(
                "Average Expected Calibration Error — 0 = perfectly calibrated, "
                "≥0.1 = significantly miscalibrated"
            ),
        )
        avg_p95 = (
            sus["latency.p95"].dropna().mean() if "latency.p95" in sus.columns else float("nan")
        )
        metric_card(
            "Avg latency.p95 (ms)",
            float(avg_p95) if pd.notna(avg_p95) else "n/a",
            fmt="{:.1f}" if pd.notna(avg_p95) else "{}",
            help="Average 95th-percentile inference latency across runs",
        )
    with cols[3]:
        avg_f1 = sus["f1_macro"].dropna().mean() if "f1_macro" in sus.columns else float("nan")
        metric_card(
            "Avg F1 macro",
            float(avg_f1) if pd.notna(avg_f1) else "n/a",
            fmt="{:.4f}" if pd.notna(avg_f1) else "{}",
            help="F1 score averaged across classes, then averaged across runs",
        )
        preds_df = load_predictions(DB_PATH)
        datasets_n = int(preds_df["instance_id"].nunique()) if not preds_df.empty else 0
        metric_card(
            "Unique instances",
            datasets_n,
            fmt="{}",
            help="Distinct evaluation instances seen across all predictions",
        )

    st.subheader("Recent runs")
    st.caption(f"{len(sus)} run(s) match current filters")
    recent = sus.sort_values("started_at", ascending=False).head(20)
    for _, s in recent.iterrows():
        with st.expander(_friendly_run_label(s), expanded=False):
            st.caption(f"`{s.get('run_id', 'unknown')}`")
            rcols = st.columns(5)
            with rcols[0]:
                metric_card("Model", s.get("model") or "?", fmt="{}")
            with rcols[1]:
                f1 = s.get("f1_macro")
                metric_card(
                    "F1 macro",
                    float(f1) if pd.notna(f1) else "n/a",
                    fmt="{:.4f}" if pd.notna(f1) else "{}",
                )
            with rcols[2]:
                ece = s.get("ece")
                metric_card(
                    "ECE",
                    float(ece) if pd.notna(ece) else "n/a",
                    fmt="{:.4f}" if pd.notna(ece) else "{}",
                )
            with rcols[3]:
                co2 = s.get("co2_g")
                metric_card(
                    "CO₂ (g)",
                    float(co2) if pd.notna(co2) else "n/a",
                    fmt="{:.4f}" if pd.notna(co2) else "{}",
                )
            with rcols[4]:
                pfr = s.get("parse_failure_rate")
                metric_card(
                    "Parse fail",
                    float(pfr) if pd.notna(pfr) else "n/a",
                    fmt="{:.4f}" if pd.notna(pfr) else "{}",
                )
