"""Model Comparison view: per-model mean±std + heatmap + Wilcoxon."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from puma.dashboard.components import download_csv_button, empty_filtered_state, fig_to_bytes
from puma.dashboard.data import load_sustainability, metrics_pivot
from puma.dashboard.views._base import DB_PATH, no_data, selected_runs


def render() -> None:
    st.title("🆚 Model Comparison")
    st.caption(
        "Per-model performance aggregated across seeds (mean ± std), plus a run × metric "  # noqa: RUF001 -- intentional Unicode multiplication sign for UI typography
        "heatmap and Wilcoxon pairwise comparison when the artifact is available."
    )

    with st.spinner("Loading cohort data…"):
        sus = load_sustainability(DB_PATH)
    if sus.empty:
        no_data()
        return

    runs_filter = selected_runs()
    if runs_filter:
        sus = sus[sus["run_id"].isin(runs_filter)]

    if sus.empty:
        empty_filtered_state("Model Comparison")
        return

    sus_m = sus.dropna(subset=["model"]).copy()

    st.subheader("Aggregate by model")
    if sus_m.empty:
        st.info("No runs with an associated model found.")
    else:
        agg_cols = [
            c for c in ["f1_macro", "accuracy", "ece", "parse_failure_rate"] if c in sus_m.columns
        ]
        agg = sus_m.groupby("model")[agg_cols].agg(["mean", "std", "count"])
        agg.columns = [f"{m}_{stat}" for m, stat in agg.columns]
        agg = agg.reset_index()

        display_rows = []
        for _, r in agg.iterrows():
            row = {"model": r["model"]}
            for col in agg_cols:
                mean = r.get(f"{col}_mean")
                std = r.get(f"{col}_std")
                n = r.get(f"{col}_count")
                if pd.isna(mean):
                    row[col] = "—"
                elif n == 1 or pd.isna(std):
                    row[col] = f"{mean:.4f} (n=1)"
                else:
                    row[col] = f"{mean:.4f} ± {std:.4f} (n={int(n)})"
            display_rows.append(row)
        agg_df = pd.DataFrame(display_rows)
        st.dataframe(agg_df, use_container_width=True, hide_index=True)
        download_csv_button(
            agg_df, file_name="model_comparison_aggregate.csv", key="dl_model_comparison_agg"
        )

    st.subheader("Run × metric heatmap")  # noqa: RUF001 -- intentional Unicode multiplication sign for UI typography
    pivot = metrics_pivot(DB_PATH)
    if not pivot.empty:
        if runs_filter:
            pivot = pivot[pivot.index.isin(runs_filter)]
        try:
            fig, ax = plt.subplots(
                figsize=(max(8, len(pivot.columns) * 1.2), max(4, len(pivot) * 0.6))
            )
            data = pivot.values.astype(float)
            im = ax.imshow(data, aspect="auto", cmap="RdYlGn")
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=8)
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels([r[:30] for r in pivot.index], fontsize=7)
            plt.colorbar(im, ax=ax)
            ax.set_title("Run × Metric Heatmap")  # noqa: RUF001 -- intentional Unicode multiplication sign for UI typography
            plt.tight_layout()
            st.pyplot(fig)
            st.download_button("Download PNG", fig_to_bytes(fig), "heatmap.png", "image/png")
            plt.close(fig)
        except Exception as exc:
            st.warning(f"Could not render heatmap: {exc}")

    st.subheader("Wilcoxon signed-rank pairwise test")
    wilcoxon_path = Path("docs/results/wilcoxon_demo.md")
    if wilcoxon_path.exists():
        content = wilcoxon_path.read_text(encoding="utf-8")
        marker = "## Results"
        if marker in content:
            content = content[content.index(marker) :]
        st.markdown(content)
    else:
        st.info(
            "No Wilcoxon artifact found at `docs/results/wilcoxon_demo.md`. "
            "Generate one with:\n\n"
            "```bash\n"
            "docker exec puma_runner python /app/scripts/wilcoxon_topmodels.py "
            "--run-prefix wilcoxon_ --top-k 2 --scenarios triage_jira\n"
            "```"
        )
