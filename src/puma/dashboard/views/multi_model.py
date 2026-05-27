"""Multi-model comparison view: side-by-side metrics, latency, carbon, reproducibility.

Complements the statistical "Model Comparison" view (aggregate ± std, heatmap,
Wilcoxon). This view answers "how do these N models compare on *this* scenario?"
with delta metrics, per-metric bar charts, and a reproducibility check — all read
from persisted SQLite results (no live inference).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from puma.dashboard.components import download_csv_button
from puma.dashboard.data import get_multi_model_results, load_predictions_with_gold
from puma.dashboard.views._base import DB_PATH, no_data

# Primary metric per scenario: (metric column, label, better-direction).
_PRIMARY: dict[str, tuple[str, str, str]] = {
    "triage_jira": ("f1_macro", "F1-macro", "high"),
    "estimation_tawos": ("mae", "MAE", "low"),
}

_CHARTS = [
    ("f1_macro", "F1-macro (higher is better)"),
    ("mae", "MAE (lower is better)"),
    ("p95_latency_ms", "Latency p95 (ms)"),
    ("total_carbon_gco2eq", "Carbon (gCO₂eq)"),
]


def render() -> None:
    st.title("🔬 Multi-model comparison")
    st.caption(
        "Side-by-side comparison of models on one scenario — metrics, latency, carbon, "
        "and reproducibility. Reads persisted results only (no live inference)."
    )

    base = load_predictions_with_gold(DB_PATH)
    if base.empty:
        no_data()
        return

    scenarios = sorted(base["dataset"].dropna().unique())
    if not scenarios:
        no_data()
        return

    scenario = st.sidebar.selectbox("Scenario", scenarios)
    models_in_scenario = sorted(base.loc[base["dataset"] == scenario, "model"].dropna().unique())
    if len(models_in_scenario) < 2:
        st.info(
            f"Need at least 2 models with results for `{scenario}` to compare "
            f"(found {len(models_in_scenario)})."
        )
        return

    chosen = st.sidebar.multiselect(
        "Models (2-5)",
        models_in_scenario,
        default=models_in_scenario[:2],
        max_selections=5,
    )
    if len(chosen) < 2:
        st.info("Select at least 2 models to compare.")
        return

    df = get_multi_model_results(scenario, chosen, DB_PATH)
    st.subheader(f"Comparing {len(chosen)} models on `{scenario}`")

    # --- headline metric per model, with delta vs the first selected model ---
    primary, label, direction = _PRIMARY.get(scenario, ("f1_macro", "F1-macro", "high"))
    baseline = df[primary].iloc[0]
    cols = st.columns(len(chosen))
    for col, model in zip(cols, chosen, strict=True):
        value = df.loc[model, primary]
        if pd.isna(value):
            col.metric(f"{model} · {label}", "—")
            continue
        delta = (
            None if (model == chosen[0] or pd.isna(baseline)) else float(value) - float(baseline)
        )
        col.metric(
            f"{model} · {label}",
            f"{float(value):.4f}",
            delta=(f"{delta:+.4f}" if delta is not None else None),
            delta_color=("inverse" if direction == "low" else "normal"),
        )

    # --- per-metric bar charts ---
    st.subheader("Metric comparison")
    chart_cols = st.columns(2)
    for i, (metric_col, title) in enumerate(_CHARTS):
        series = df[metric_col].dropna()
        with chart_cols[i % 2]:
            st.caption(title)
            if series.empty:
                st.write("— (no data for this scenario)")
            else:
                st.bar_chart(series)

    # --- full table + download ---
    st.subheader("Full metrics")
    st.dataframe(df, use_container_width=True)
    download_csv_button(
        df.reset_index(), file_name=f"multi_model_{scenario}.csv", key="dl_multi_model"
    )

    # --- reproducibility ---
    st.subheader("Reproducibility")
    st.caption(
        "Per-run fingerprint over `(instance_id, predicted_label)`. One value across a "
        "model's runs ⇒ deterministic; `varies (n)` ⇒ n distinct prediction sets."
    )
    for model in chosen:
        fingerprint = df.loc[model, "predictions_summary_hash"]
        n_runs = df.loc[model, "run_count"]
        if pd.isna(fingerprint) or fingerprint is None:
            st.write(f"- **{model}** — no runs for this scenario")
        elif str(fingerprint).startswith("varies"):
            st.write(f"- **{model}** — ⚠ {fingerprint} across {int(n_runs)} runs")
        else:
            st.write(f"- **{model}** — ✓ deterministic (`{fingerprint}`, {int(n_runs)} run(s))")
