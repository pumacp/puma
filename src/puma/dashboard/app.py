"""PUMA Streamlit dashboard — 7 views for result exploration."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from puma.dashboard.components import (
    comparison_table,
    fig_to_bytes,
    metric_card,
    pareto_scatter,
    reliability_plot,
)
from puma.dashboard.data import (
    load_metrics,
    load_predictions,
    load_runs,
    metrics_pivot,
    run_summary,
)

DB_PATH = Path("data/puma.db")

st.set_page_config(
    page_title="PUMA Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("PUMA")
st.sidebar.caption("Local LLM Benchmark")

view = st.sidebar.radio(
    "View",
    [
        "Overview",
        "Model Comparison",
        "Reliability",
        "Robustness",
        "Fairness",
        "Sustainability Frontier",
        "Instance Drill-down",
    ],
)

# Global filters
runs_df = load_runs(DB_PATH)

if runs_df.empty:
    selected_runs: list[str] = []
    model_options: list[str] = []
else:
    all_run_ids = runs_df["run_id"].tolist()
    selected_runs = st.sidebar.multiselect(
        "Runs", all_run_ids, default=all_run_ids[:5]
    )

    # Date filter
    if "started_at" in runs_df.columns:
        runs_df["started_at"] = runs_df["started_at"].apply(
            lambda x: str(x)[:10] if x else ""
        )
        dates = sorted(runs_df["started_at"].unique())
        if len(dates) > 1:
            selected_dates = st.sidebar.select_slider(
                "Date range", options=dates, value=(dates[0], dates[-1])
            )
            runs_df = runs_df[
                (runs_df["started_at"] >= selected_dates[0])
                & (runs_df["started_at"] <= selected_dates[1])
            ]

    # Model filter from predictions
    preds_df = load_predictions(DB_PATH)
    if not preds_df.empty and "model" in preds_df.columns:
        model_options = sorted(preds_df["model"].unique().tolist())
        selected_models = st.sidebar.multiselect("Models", model_options, default=model_options)
    else:
        model_options = []
        selected_models = []


# ── View helpers ──────────────────────────────────────────────────────────────

def _no_data() -> None:
    st.info("No run data found. Run `puma run <spec.yaml>` first to generate results.")


# ── View: Overview ────────────────────────────────────────────────────────────

if view == "Overview":
    st.title("Overview")

    summaries = run_summary(DB_PATH)
    if not summaries:
        _no_data()
    else:
        st.caption(f"{len(summaries)} run(s) in database")
        for s in summaries[:20]:
            with st.expander(s.get("run_id", "unknown"), expanded=False):
                cols = st.columns(4)
                with cols[0]:
                    metric_card("Status", s.get("status", "n/a"), fmt="{}")
                with cols[1]:
                    f1 = s.get("f1_macro")
                    metric_card("F1 macro", f1 if f1 is not None else "n/a",
                                fmt="{:.4f}" if isinstance(f1, float) else "{}")
                with cols[2]:
                    acc = s.get("accuracy")
                    metric_card("Accuracy", acc if acc is not None else "n/a",
                                fmt="{:.4f}" if isinstance(acc, float) else "{}")
                with cols[3]:
                    pfr = s.get("parse_failure_rate")
                    metric_card("Parse fail", pfr if pfr is not None else "n/a",
                                fmt="{:.4f}" if isinstance(pfr, float) else "{}")


# ── View: Model Comparison ────────────────────────────────────────────────────

elif view == "Model Comparison":
    st.title("Model Comparison")

    pivot = metrics_pivot(DB_PATH)
    if pivot.empty:
        _no_data()
    else:
        if selected_runs:
            pivot = pivot[pivot.index.isin(selected_runs)]
        st.subheader("Metrics heatmap")

        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 1.2), max(4, len(pivot) * 0.6)))
            data = pivot.values.astype(float)
            im = ax.imshow(data, aspect="auto", cmap="RdYlGn")
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=8)
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels([r[:30] for r in pivot.index], fontsize=7)
            plt.colorbar(im, ax=ax)
            ax.set_title("Run × Metric Heatmap")
            plt.tight_layout()
            st.pyplot(fig)
            st.download_button("Download PNG", fig_to_bytes(fig), "heatmap.png", "image/png")
            plt.close(fig)
        except Exception as exc:
            st.warning(f"Could not render heatmap: {exc}")

        st.subheader("Raw metrics table")
        ct = comparison_table(
            {rid: {c: pivot.loc[rid, c] for c in pivot.columns if not __import__("math").isnan(pivot.loc[rid, c])}
             for rid in pivot.index}
        )
        st.dataframe(ct, use_container_width=True)


# ── View: Reliability ─────────────────────────────────────────────────────────

elif view == "Reliability":
    st.title("Reliability")
    st.info(
        "Reliability diagrams require logprob data (enable `logprobs: true` in run-spec). "
        "Showing placeholder with synthetic data."
    )
    import random

    rng = random.Random(42)
    confs = [min(1.0, max(0.0, rng.gauss(0.75, 0.15))) for _ in range(200)]
    corrects = [c > 0.5 for c in confs]
    fig = reliability_plot(confs, corrects)
    st.pyplot(fig)
    st.download_button("Download PNG", fig_to_bytes(fig), "reliability.png", "image/png")
    import matplotlib.pyplot as plt
    plt.close(fig)


# ── View: Robustness ──────────────────────────────────────────────────────────

elif view == "Robustness":
    st.title("Robustness")

    preds = load_predictions(DB_PATH)
    if preds.empty:
        _no_data()
    else:
        if selected_runs:
            preds = preds[preds["run_id"].isin(selected_runs)]
        if "perturbation" not in preds.columns or "parsed_label" not in preds.columns:
            st.warning("Predictions table missing perturbation columns.")
        else:
            orig = preds[preds["perturbation"].isna()]
            perturbed = preds[preds["perturbation"].notna()]

            st.caption(f"{len(orig)} original, {len(perturbed)} perturbed predictions")

            if not perturbed.empty:
                try:
                    import matplotlib.pyplot as plt

                    groups = perturbed.groupby("perturbation")
                    names, rates = [], []
                    for name, grp in groups:
                        if not orig.empty:
                            orig_sub = orig[orig["instance_id"].isin(grp["instance_id"])]
                            if not orig_sub.empty:
                                match = (
                                    grp.set_index("instance_id")["parsed_label"]
                                    .reindex(orig_sub["instance_id"].values)
                                    == orig_sub.set_index("instance_id")["parsed_label"]
                                ).mean()
                                names.append(name)
                                rates.append(float(match))

                    if names:
                        fig, ax = plt.subplots(figsize=(6, 3))
                        ax.bar(names, rates, color="steelblue")
                        ax.set_ylim(0, 1)
                        ax.set_ylabel("Consistency rate")
                        ax.set_title("Prediction consistency under perturbations")
                        st.pyplot(fig)
                        st.download_button(
                            "Download PNG", fig_to_bytes(fig), "robustness.png", "image/png"
                        )
                        plt.close(fig)
                except Exception as exc:
                    st.warning(f"Could not render robustness plot: {exc}")
            else:
                st.info("No perturbed predictions found. Add perturbations to your run-spec.")


# ── View: Fairness ────────────────────────────────────────────────────────────

elif view == "Fairness":
    st.title("Fairness")
    st.info(
        "Fairness analysis requires a group attribute column in predictions. "
        "Currently showing per-model accuracy breakdown."
    )

    preds = load_predictions(DB_PATH)
    if preds.empty:
        _no_data()
    else:
        if selected_runs:
            preds = preds[preds["run_id"].isin(selected_runs)]
        if "model" in preds.columns and "parsed_label" in preds.columns and "gold_label" in preds.columns:
            preds = preds[preds["parsed_label"].notna()]
            preds["correct"] = preds["parsed_label"] == preds["gold_label"]
            acc_by_model = preds.groupby("model")["correct"].mean().reset_index()
            acc_by_model.columns = ["Model", "Accuracy"]
            st.dataframe(acc_by_model, use_container_width=True)

            if len(acc_by_model) > 1:
                gap = acc_by_model["Accuracy"].max() - acc_by_model["Accuracy"].min()
                st.metric("Fairness gap (max − min accuracy)", f"{gap:.4f}")
        else:
            st.warning("Predictions missing required columns.")


# ── View: Sustainability Frontier ─────────────────────────────────────────────

elif view == "Sustainability Frontier":
    st.title("Sustainability Frontier")

    metrics_df = load_metrics(DB_PATH)
    if metrics_df.empty:
        _no_data()
    else:
        if selected_runs:
            metrics_df = metrics_df[metrics_df["run_id"].isin(selected_runs)]

        pivot = metrics_df.pivot_table(
            index="run_id", columns="metric_name", values="value", aggfunc="first"
        ).reset_index()

        f1_col = next((c for c in pivot.columns if "f1_macro" in c), None)
        lat_col = next((c for c in pivot.columns if "latency" in c.lower()), None)

        if f1_col and lat_col:
            valid = pivot[[f1_col, lat_col, "run_id"]].dropna()
            if not valid.empty:
                fig = pareto_scatter(
                    xs=valid[lat_col].tolist(),
                    ys=valid[f1_col].tolist(),
                    labels=[r[:20] for r in valid["run_id"].tolist()],
                    x_label="Latency (proxy efficiency)",
                    y_label="F1 macro",
                )
                st.pyplot(fig)
                st.download_button(
                    "Download PNG", fig_to_bytes(fig), "frontier.png", "image/png"
                )
                import matplotlib.pyplot as plt
                plt.close(fig)
        else:
            st.info("Need both `f1_macro` and latency metrics. Run a triage_jira benchmark first.")
            st.dataframe(pivot, use_container_width=True)


# ── View: Instance Drill-down ─────────────────────────────────────────────────

elif view == "Instance Drill-down":
    st.title("Instance Drill-down")

    preds = load_predictions(DB_PATH)
    if preds.empty:
        _no_data()
    else:
        if selected_runs:
            preds = preds[preds["run_id"].isin(selected_runs)]

        run_options = preds["run_id"].unique().tolist() if not preds.empty else []
        chosen_run = st.selectbox("Run", run_options)

        if chosen_run:
            run_preds = preds[preds["run_id"] == chosen_run]
            instance_options = run_preds["instance_id"].unique().tolist()
            chosen_instance = st.selectbox("Instance", instance_options)

            if chosen_instance:
                rows = run_preds[run_preds["instance_id"] == chosen_instance]
                for _, pred in rows.iterrows():
                    with st.expander(
                        f"Model: {pred.get('model', '?')} | "
                        f"Strategy: {pred.get('strategy', '?')} | "
                        f"Perturbation: {pred.get('perturbation', 'original')}",
                        expanded=True,
                    ):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Gold label**")
                            st.code(str(pred.get("gold_label", "n/a")))
                            st.markdown("**Parsed label**")
                            st.code(str(pred.get("parsed_label", "n/a")))
                        with col2:
                            st.markdown("**Latency (ms)**")
                            st.code(str(pred.get("latency_ms", "n/a")))
                            st.markdown("**Tokens in / out**")
                            st.code(
                                f"{pred.get('tokens_in', '?')} / {pred.get('tokens_out', '?')}"
                            )

                        st.markdown("**Raw LLM response**")
                        st.text_area(
                            "response",
                            value=str(pred.get("raw_response", "")),
                            height=120,
                            key=f"resp_{pred.get('prompt_hash', '')}",
                            disabled=True,
                        )

                        ph = pred.get("prompt_hash", "")
                        st.markdown(f"**Prompt hash:** `{ph}`")
