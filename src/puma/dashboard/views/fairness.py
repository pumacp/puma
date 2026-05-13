"""Fairness view: gender-prefix signal injection bias evaluation."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from puma.dashboard.components import download_csv_button
from puma.dashboard.data import load_predictions_with_gold
from puma.dashboard.views._base import selected_runs
from puma.metrics.fairness import perturbation_disparity

GENDER_PERTURBATIONS = ["gender_swap_prefix_male", "gender_swap_prefix_female"]


def render() -> None:
    st.title("⚖️ Fairness")
    st.caption(
        "Bias evaluation via gender-prefix signal injection. The triage_jira corpus "
        "has 0% gendered terms (technical incident text), so we inject identity "
        "prefixes — `John Smith reported:` vs `Mary Smith reported:` — and measure "
        "whether the same instance is classified differently."
    )

    with st.spinner("Loading predictions…"):
        preds = load_predictions_with_gold()
    runs_filter = selected_runs()
    if runs_filter:
        preds = preds[preds["run_id"].isin(runs_filter)]

    gender_rows = preds[preds["perturbation"].isin(GENDER_PERTURBATIONS)]
    if gender_rows.empty:
        st.info(
            "**No gender-prefix perturbation runs in the selected runs.** Run "
            "`puma run specs/runs/sweep_bias_perturbations.yaml` to populate this view."
        )
        return

    st.subheader("Prefix vs un-perturbed baseline")
    baseline_rows: list[dict] = []
    directional_rows: list[dict] = []
    for model in sorted(preds["model"].dropna().unique()):
        base = preds[(preds["model"] == model) & preds["perturbation"].isna()]
        base_lookup = dict(zip(base["instance_id"], base["parsed_label"], strict=False))
        gold_lookup = dict(zip(base["instance_id"], base["gold_label"], strict=False))
        sub_by_pert: dict[str, dict] = {}
        for pert in GENDER_PERTURBATIONS:
            sub = gender_rows[
                (gender_rows["model"] == model) & (gender_rows["perturbation"] == pert)
            ]
            if sub.empty:
                continue
            sub_by_pert[pert] = dict(zip(sub["instance_id"], sub["parsed_label"], strict=False))

        for pert, sub_lookup in sub_by_pert.items():
            shared = sorted(set(sub_lookup) & set(base_lookup))
            if not shared:
                continue
            metrics = perturbation_disparity(
                [base_lookup[i] for i in shared],
                [sub_lookup[i] for i in shared],
                [gold_lookup[i] for i in shared],
            )
            baseline_rows.append(
                {"model": model, "perturbation": pert, "n": len(shared), **metrics}
            )

        if all(p in sub_by_pert for p in GENDER_PERTURBATIONS):
            male = sub_by_pert["gender_swap_prefix_male"]
            female = sub_by_pert["gender_swap_prefix_female"]
            shared = sorted(set(male) & set(female) & set(gold_lookup))
            if shared:
                metrics = perturbation_disparity(
                    [male[i] for i in shared],
                    [female[i] for i in shared],
                    [gold_lookup[i] for i in shared],
                )
                directional_rows.append(
                    {
                        "model": model,
                        "comparison": "male vs female",
                        "n": len(shared),
                        **metrics,
                    }
                )

    if baseline_rows:
        df = pd.DataFrame(baseline_rows)
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
        download_csv_button(df, file_name="fairness_baseline.csv", key="dl_fairness_baseline")

    if directional_rows:
        st.subheader("Directional bias (male prefix vs female prefix)")
        st.caption(
            "Pairs the male and female prefix conditions on the same instance. "
            "A non-zero `flip_rate` means the model classified the same ticket "
            "differently depending on the reporter's gender alone."
        )
        df = pd.DataFrame(directional_rows)
        for c in (
            "acc_baseline",
            "acc_perturbed",
            "disparity",
            "flip_rate",
            "flip_to_correct",
            "flip_to_incorrect",
        ):
            if c in df.columns:
                df[c] = df[c].map(lambda v: f"{v:.4f}")
        df = df.rename(columns={"acc_baseline": "acc_male", "acc_perturbed": "acc_female"})
        st.dataframe(df, use_container_width=True, hide_index=True)
        download_csv_button(df, file_name="fairness_directional.csv", key="dl_fairness_dir")

    st.caption("Methodology and full discussion: `docs/results/bias_evaluation.md`.")
