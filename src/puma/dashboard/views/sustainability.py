"""Sustainability Frontier view: quality (F1) vs cost (CO₂)."""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from puma.dashboard.components import fig_to_bytes, pareto_scatter
from puma.dashboard.data import load_sustainability
from puma.dashboard.views._base import DB_PATH, no_data, selected_runs


def render() -> None:
    st.title("🌱 Sustainability Frontier")
    st.caption(
        "Quality vs. carbon cost. Each point is a run; axes show F1 macro against CO₂ (g) "
        "emitted, measured by CodeCarbon. Runs near the top-left are Pareto-efficient "
        "(high quality per gram of CO₂)."
    )

    with st.spinner("Loading cohort data…"):
        sus = load_sustainability(DB_PATH)
    if sus.empty:
        no_data()
        return

    runs_filter = selected_runs()
    if runs_filter:
        sus = sus[sus["run_id"].isin(runs_filter)]

    valid = sus.dropna(subset=["f1_macro", "co2_g"]).copy()
    if valid.empty:
        st.warning(
            "No runs with both `f1_macro` and `co2_kg` available. "
            "CodeCarbon emissions are persisted from Sprint 2 onwards (D15)."
        )
        st.dataframe(sus, use_container_width=True)
    else:
        labels = [f"{(r['model'] or '?')} · {r['run_id'][:20]}" for _, r in valid.iterrows()]
        fig = pareto_scatter(
            xs=valid["co2_g"].tolist(),
            ys=valid["f1_macro"].tolist(),
            labels=labels,
            x_label="CO₂ emitted (g)",
            y_label="F1 macro",
        )
        st.pyplot(fig)
        st.download_button(
            "Download PNG", fig_to_bytes(fig), "sustainability_frontier.png", "image/png"
        )
        plt.close(fig)

        display_cols = [
            c
            for c in [
                "run_id",
                "model",
                "f1_macro",
                "ece",
                "co2_g",
                "kwh",
                "duration_s",
                "gpu_energy",
            ]
            if c in valid.columns
        ]
        st.subheader("Per-run breakdown")
        st.dataframe(valid[display_cols], use_container_width=True)

    n_total = len(sus)
    n_with_emissions = int(sus["co2_kg"].notna().sum()) if "co2_kg" in sus.columns else 0
    if n_with_emissions < n_total:
        st.caption(
            f"ℹ️ {n_with_emissions} of {n_total} runs have emissions data. "  # noqa: RUF001 -- intentional Unicode glyph for UI typography
            "Older runs (pre-Sprint 2 D15) did not persist CodeCarbon output."
        )
