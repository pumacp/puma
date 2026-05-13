"""Reliability view: per-model ECE and reliability diagrams from real logprobs."""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from puma.dashboard.components import fig_to_bytes, metric_card, reliability_plot
from puma.dashboard.data import load_predictions_with_gold
from puma.dashboard.views._base import no_data, selected_runs
from puma.metrics.calibration import expected_calibration_error


def render() -> None:
    st.title("🎯 Reliability")
    st.caption(
        "Per-model calibration: Expected Calibration Error (ECE) and reliability diagram "
        "computed from logprob-derived confidences. Requires runs with `logprobs: true`."
    )

    with st.spinner("Loading predictions…"):
        preds = load_predictions_with_gold()
    if preds.empty:
        no_data()
        return

    runs_filter = selected_runs()
    if runs_filter:
        preds = preds[preds["run_id"].isin(runs_filter)]

    with_logprobs = preds[preds["confidence"].notna() & preds["logprobs_json"].notna()]
    if with_logprobs.empty:
        st.info(
            "No predictions with logprob data in the selected runs. "
            "Re-run with `inference.logprobs: true` in your run-spec to populate confidence."
        )
        return

    models_with_lp = sorted(with_logprobs["model"].unique().tolist())
    all_models = sorted(preds["model"].unique().tolist())
    missing = [m for m in all_models if m not in models_with_lp]

    n_bins = st.slider("Reliability bins", min_value=5, max_value=20, value=15)

    for model in models_with_lp:
        sub = with_logprobs[with_logprobs["model"] == model]
        confs = sub["confidence"].astype(float).tolist()
        corrects = (sub["parsed_label"] == sub["gold_label"]).astype(bool).tolist()

        try:
            ece = expected_calibration_error(confs, corrects, n_bins=n_bins)
        except ValueError as exc:
            st.warning(f"{model}: could not compute ECE ({exc})")
            continue

        acc = sum(corrects) / len(corrects)
        with st.expander(
            f"**{model}** — n={len(sub)} · ECE={ece:.4f} · acc={acc:.3f}", expanded=True
        ):
            cols = st.columns([1, 2])
            with cols[0]:
                metric_card("ECE", ece, fmt="{:.4f}")
                metric_card("Accuracy", acc, fmt="{:.4f}")
                metric_card("Mean confidence", float(sum(confs) / len(confs)), fmt="{:.4f}")
                metric_card("Predictions", len(sub), fmt="{}")
            with cols[1]:
                fig = reliability_plot(confs, corrects, n_bins=n_bins)
                st.pyplot(fig)
                st.download_button(
                    "Download PNG",
                    fig_to_bytes(fig),
                    f"reliability_{model.replace(':', '_').replace('/', '_')}.png",
                    "image/png",
                    key=f"dl_rel_{model}",
                )
                plt.close(fig)

    if missing:
        st.info(
            "**Models without logprob data:** "
            + ", ".join(f"`{m}`" for m in missing)
            + ". Re-run with `inference.logprobs: true` to enable calibration analysis."
        )
