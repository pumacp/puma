"""Instance Drill-down view: per-prediction inspection with logprobs."""

from __future__ import annotations

import json
import math

import pandas as pd
import streamlit as st

from puma.dashboard.components import download_csv_button, empty_filtered_state
from puma.dashboard.data import load_predictions_with_gold
from puma.dashboard.views._base import no_data, selected_runs


def render() -> None:
    st.title("🔍 Instance Drill-down")
    st.caption(
        "Per-instance inspection: gold label, parsed prediction, parse status, "
        "logprob-derived confidence, and the top-K alternatives at the first token."
    )

    with st.spinner("Loading predictions…"):
        preds = load_predictions_with_gold()
    if preds.empty:
        no_data()
        return

    runs_filter = selected_runs()
    if runs_filter:
        preds = preds[preds["run_id"].isin(runs_filter)]

    run_options = preds["run_id"].unique().tolist()
    if not run_options:
        empty_filtered_state("Instance Drill-down")
        return

    chosen_run = st.selectbox("Run", run_options)
    if not chosen_run:
        return

    run_preds = preds[preds["run_id"] == chosen_run].copy()
    run_preds["correct"] = run_preds["parsed_label"] == run_preds["gold_label"]
    run_preds["parse_failure"] = run_preds["parsed_label"].isna()

    fcols = st.columns(3)
    with fcols[0]:
        filter_outcome = st.selectbox(
            "Outcome filter", ["all", "correct only", "incorrect only", "parse failures"]
        )
    with fcols[1]:
        model_opts = sorted(run_preds["model"].dropna().unique().tolist())
        filter_model = st.selectbox("Model filter", ["all", *model_opts])
    with fcols[2]:
        show_only_with_logprobs = st.checkbox("Only with logprobs", value=False)

    filtered = run_preds
    if filter_outcome == "correct only":
        filtered = filtered[filtered["correct"]]
    elif filter_outcome == "incorrect only":
        filtered = filtered[~filtered["correct"] & ~filtered["parse_failure"]]
    elif filter_outcome == "parse failures":
        filtered = filtered[filtered["parse_failure"]]
    if filter_model != "all":
        filtered = filtered[filtered["model"] == filter_model]
    if show_only_with_logprobs:
        filtered = filtered[filtered["logprobs_json"].notna()]

    st.caption(
        f"{len(filtered)} of {len(run_preds)} predictions shown · "
        f"correct={int(filtered['correct'].sum())} · "
        f"parse failures={int(filtered['parse_failure'].sum())}"
    )

    summary_cols = [
        c
        for c in [
            "instance_id",
            "model",
            "gold_label",
            "parsed_label",
            "correct",
            "parse_failure",
            "confidence",
            "latency_ms",
        ]
        if c in filtered.columns
    ]
    st.dataframe(filtered[summary_cols], use_container_width=True, height=240)
    if not filtered.empty:
        download_csv_button(
            filtered[summary_cols],
            file_name=f"instances_{chosen_run[:20]}.csv",
            key="dl_instances",
        )

    instance_options = filtered["instance_id"].unique().tolist()
    if not instance_options:
        st.info("No instances match the current filters.")
        return

    chosen_instance = st.selectbox("Inspect instance", instance_options)
    if not chosen_instance:
        return

    rows = filtered[filtered["instance_id"] == chosen_instance]
    first = rows.iloc[0]
    input_text = first.get("input_text", "")
    if pd.isna(input_text) or input_text == "":
        st.info(
            "ℹ️ **Input text not persisted for this dataset.**\n\n"  # noqa: RUF001 -- intentional Unicode glyph for UI typography
            "The current `triage_jira` dataset records only `instance_id` and "
            "`gold_label` — not the original ticket description. The view below "
            "shows the model's prediction, ground truth, parser output, and "
            "(when available) logprob-derived confidence.\n\n"
            "Persisting full ticket text for instance-level traceability is "
            "tracked as future work (see `docs/known_debt.md` D22)."
        )
    else:
        st.markdown("**Input text:**")
        st.text_area(
            "input",
            value=str(input_text),
            height=150,
            disabled=True,
            key=f"input_{chosen_instance}",
        )

    for _i, (_, pred) in enumerate(rows.iterrows()):
        ok = "✅" if pred["correct"] else ("⚠️" if pred["parse_failure"] else "❌")
        with st.expander(
            f"{ok} {pred.get('model', '?')} · "
            f"strategy={pred.get('strategy', '?')} · "
            f"perturbation={pred.get('perturbation') or 'original'} · "
            f"seed={pred.get('seed', '?')}",
            expanded=True,
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Gold label**")
                st.code(str(pred.get("gold_label", "n/a")))
                st.markdown("**Parsed label**")
                st.code(
                    str(pred.get("parsed_label"))
                    if pd.notna(pred.get("parsed_label"))
                    else "(parse failure)"
                )
                conf = pred.get("confidence")
                st.markdown("**Confidence**")
                st.code(f"{conf:.4f}" if pd.notna(conf) else "n/a")
            with col2:
                st.markdown("**Latency (ms)**")
                lat = pred.get("latency_ms")
                st.code(f"{lat:.1f}" if pd.notna(lat) else "n/a")
                st.markdown("**Tokens in / out**")
                st.code(f"{pred.get('tokens_in', '?')} / {pred.get('tokens_out', '?')}")
                st.markdown("**Prompt hash**")
                st.code(pred.get("prompt_hash", "n/a"))

            lp = pred.get("logprobs_json")
            if pd.notna(lp):
                st.markdown("**Top-K logprobs (first generated token):**")
                try:
                    data = json.loads(lp)
                    if data and isinstance(data, list):
                        first_tok = data[0]
                        top = first_tok.get("top_logprobs", [])
                        rows_view = [
                            {
                                "token": repr(t.get("token", "")),
                                "logprob": f"{t.get('logprob', 0.0):.4f}",
                                "prob": f"{math.exp(t.get('logprob', 0.0)):.4f}",
                            }
                            for t in top[:5]
                        ]
                        if rows_view:
                            st.dataframe(
                                pd.DataFrame(rows_view),
                                use_container_width=True,
                                hide_index=True,
                            )
                except (ValueError, KeyError, TypeError) as exc:
                    st.warning(f"Could not parse logprobs_json: {exc}")

            raw = pred.get("raw_response", "")
            if raw:
                st.markdown("**Raw LLM response**")
                st.text_area(
                    "response",
                    value=str(raw),
                    height=80,
                    key=f"resp_{_i}_{pred.get('prompt_hash', '')}",
                    disabled=True,
                )
