"""Robustness view: paired baseline-vs-perturbed comparison by model."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from puma.dashboard.components import download_csv_button, fig_to_bytes
from puma.dashboard.data import load_predictions_with_gold
from puma.dashboard.views._base import selected_runs
from puma.metrics.fairness import perturbation_disparity


def render() -> None:
    st.title("🛡️ Robustness")
    st.caption(
        "Per-model behaviour under controlled input perturbations. Each row pairs "
        "the un-perturbed baseline against a perturbed version on the same instances "
        "and reports accuracy, prediction flip rate, and the direction of those flips."
    )

    with st.spinner("Loading predictions…"):
        preds = load_predictions_with_gold()
    runs_filter = selected_runs()
    if runs_filter:
        preds = preds[preds["run_id"].isin(runs_filter)]

    pert_rows = preds[preds["perturbation"].notna()]
    if pert_rows.empty:
        st.info(
            "**No perturbed predictions in the selected runs.** Run "
            "`puma run specs/runs/sweep_bias_perturbations.yaml` to populate this view."
        )
        return

    rows: list[dict[str, Any]] = []
    for model in sorted(preds["model"].dropna().unique()):
        base = preds[(preds["model"] == model) & preds["perturbation"].isna()]
        base_lookup = dict(zip(base["instance_id"], base["parsed_label"], strict=False))
        gold_lookup = dict(zip(base["instance_id"], base["gold_label"], strict=False))
        for pert in sorted(pert_rows[pert_rows["model"] == model]["perturbation"].unique()):
            sub = pert_rows[(pert_rows["model"] == model) & (pert_rows["perturbation"] == pert)]
            shared = sorted(set(sub["instance_id"]) & set(base_lookup))
            if not shared:
                continue
            base_preds_l = [base_lookup[i] for i in shared]
            pert_preds_l = [sub.set_index("instance_id").loc[i, "parsed_label"] for i in shared]
            gold_l = [gold_lookup[i] for i in shared]
            metrics = perturbation_disparity(base_preds_l, pert_preds_l, gold_l)
            rows.append(
                {
                    "model": model,
                    "perturbation": pert,
                    "n": len(shared),
                    **metrics,
                }
            )

    if not rows:
        st.warning("No baseline/perturbation pairs to compare.")
        return

    df = pd.DataFrame(rows)
    display = df.copy()
    for c in (
        "acc_baseline",
        "acc_perturbed",
        "disparity",
        "flip_rate",
        "flip_to_correct",
        "flip_to_incorrect",
    ):
        if c in display.columns:
            display[c] = display[c].map(lambda v: f"{v:.4f}")
    st.dataframe(display, use_container_width=True, hide_index=True)
    download_csv_button(df, file_name="robustness.csv", key="dl_robustness")

    fig, ax = plt.subplots(figsize=(8, 4))
    models = sorted(df["model"].unique())
    perturbations = sorted(df["perturbation"].unique())
    x = range(len(perturbations))
    width = 0.8 / max(1, len(models))
    for i, m in enumerate(models):
        row = df[df["model"] == m].set_index("perturbation")
        values = [row.loc[p, "flip_rate"] if p in row.index else 0.0 for p in perturbations]
        ax.bar([xi + i * width for xi in x], values, width=width, label=m)
    ax.set_xticks([xi + width * (len(models) - 1) / 2 for xi in x])
    ax.set_xticklabels(perturbations, rotation=20, ha="right", fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Flip rate")
    ax.set_title("Prediction flip rate under perturbation")
    ax.legend(fontsize=8)
    plt.tight_layout()
    st.pyplot(fig)
    st.download_button("Download PNG", fig_to_bytes(fig), "robustness.png", "image/png")
    plt.close(fig)

    st.caption(
        "Higher `flip_rate` ⇒ the model changed more of its predictions when "
        "the perturbation was applied. `flip_to_incorrect` close to 1 means "
        "the perturbation degrades performance more than it helps."
    )
