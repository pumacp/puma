"""PUMA Streamlit dashboard — 7 views for result exploration."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from puma.dashboard.components import fig_to_bytes, metric_card, pareto_scatter, reliability_plot
from puma.dashboard.data import (
    load_predictions,
    load_predictions_with_gold,
    load_runs,
    load_sustainability,
    metrics_pivot,
)
from puma.metrics.calibration import expected_calibration_error

DB_PATH = Path("data/puma.db")
LOGO_PATH = Path(__file__).resolve().parents[3] / "assets" / "img" / "PUMA.png"

st.set_page_config(
    page_title="PUMA Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), width=160)
st.sidebar.title("PUMA")
st.sidebar.caption("Project Understanding & Management with Agents")

dark_mode = st.sidebar.toggle("🌙 Dark mode", value=False)
if dark_mode:
    st.markdown(
        """
        <style>
        .stApp { background-color: #1A1A2E; color: #E5E7EB; }
        [data-testid="stSidebar"] { background-color: #16213E; }
        [data-testid="stSidebar"] * { color: #E5E7EB !important; }
        .stMarkdown, .stMarkdown p, .stMarkdown li, .stCaption,
        .stExpander, .stExpander * { color: #E5E7EB; }
        [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #E5E7EB; }
        .stDataFrame, .stDataFrame * { color: #1A2E2A; }
        h1, h2, h3, h4 { color: #5EE6C2 !important; }
        a { color: #82E9D9; }
        [data-testid="stAlert"] { background-color: #0F3460; color: #E5E7EB; }
        </style>
        """,
        unsafe_allow_html=True,
    )

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
    selected_runs = st.sidebar.multiselect("Runs", all_run_ids, default=all_run_ids[:5])

    # Date filter
    if "started_at" in runs_df.columns:
        runs_df["started_at"] = runs_df["started_at"].apply(lambda x: str(x)[:10] if x else "")
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

    sus = load_sustainability(DB_PATH)
    if sus.empty:
        _no_data()
    else:
        if selected_runs:
            sus = sus[sus["run_id"].isin(selected_runs)]
        if selected_models:
            sus = sus[sus["model"].isin(selected_models) | sus["model"].isna()]

        st.subheader("Cohort summary")
        cols = st.columns(4)
        with cols[0]:
            metric_card("Runs", len(sus), fmt="{}")
            metric_card("Unique models", int(sus["model"].dropna().nunique()), fmt="{}")
        with cols[1]:
            total_co2 = float(sus["co2_g"].sum()) if "co2_g" in sus.columns else 0.0
            metric_card("Total CO₂ (g)", total_co2, fmt="{:.4f}")
            total_kwh = float(sus["kwh"].sum()) if "kwh" in sus.columns else 0.0
            metric_card("Total energy (kWh)", total_kwh, fmt="{:.6f}")
        with cols[2]:
            avg_ece = sus["ece"].dropna().mean() if "ece" in sus.columns else float("nan")
            metric_card(
                "Avg ECE",
                float(avg_ece) if pd.notna(avg_ece) else "n/a",
                fmt="{:.4f}" if pd.notna(avg_ece) else "{}",
            )
            avg_p95 = (
                sus["latency.p95"].dropna().mean() if "latency.p95" in sus.columns else float("nan")
            )
            metric_card(
                "Avg latency.p95 (ms)",
                float(avg_p95) if pd.notna(avg_p95) else "n/a",
                fmt="{:.1f}" if pd.notna(avg_p95) else "{}",
            )
        with cols[3]:
            avg_f1 = sus["f1_macro"].dropna().mean() if "f1_macro" in sus.columns else float("nan")
            metric_card(
                "Avg F1 macro",
                float(avg_f1) if pd.notna(avg_f1) else "n/a",
                fmt="{:.4f}" if pd.notna(avg_f1) else "{}",
            )
            datasets_n = (
                int(load_predictions(DB_PATH)["instance_id"].nunique())
                if not load_predictions(DB_PATH).empty
                else 0
            )
            metric_card("Unique instances", datasets_n, fmt="{}")

        st.subheader("Recent runs")
        st.caption(f"{len(sus)} run(s) match current filters")
        recent = sus.sort_values("started_at", ascending=False).head(20)
        for _, s in recent.iterrows():
            run_id = s.get("run_id", "unknown")
            with st.expander(run_id, expanded=False):
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


# ── View: Model Comparison ────────────────────────────────────────────────────

elif view == "Model Comparison":
    st.title("Model Comparison")
    st.caption(
        "Per-model performance aggregated across seeds (mean ± std), plus a run × metric "  # noqa: RUF001 -- intentional Unicode multiplication sign for UI typography
        "heatmap and Wilcoxon pairwise comparison when the artifact is available."
    )

    sus = load_sustainability(DB_PATH)
    if sus.empty:
        _no_data()
    else:
        if selected_runs:
            sus = sus[sus["run_id"].isin(selected_runs)]

        sus_m = sus.dropna(subset=["model"]).copy()

        st.subheader("Aggregate by model")
        if sus_m.empty:
            st.info("No runs with an associated model found.")
        else:
            agg_cols = [
                c
                for c in ["f1_macro", "accuracy", "ece", "parse_failure_rate"]
                if c in sus_m.columns
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
            st.dataframe(pd.DataFrame(display_rows), use_container_width=True)

        st.subheader("Run × metric heatmap")  # noqa: RUF001 -- intentional Unicode multiplication sign for UI typography
        pivot = metrics_pivot(DB_PATH)
        if not pivot.empty:
            if selected_runs:
                pivot = pivot[pivot.index.isin(selected_runs)]
            try:
                import matplotlib.pyplot as plt

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


# ── View: Reliability ─────────────────────────────────────────────────────────

elif view == "Reliability":
    st.title("Reliability")
    st.caption(
        "Per-model calibration: Expected Calibration Error (ECE) and reliability diagram "
        "computed from logprob-derived confidences. Requires runs with `logprobs: true`."
    )

    preds = load_predictions_with_gold()
    if preds.empty:
        _no_data()
    else:
        if selected_runs:
            preds = preds[preds["run_id"].isin(selected_runs)]

        with_logprobs = preds[preds["confidence"].notna() & preds["logprobs_json"].notna()]
        if with_logprobs.empty:
            st.info(
                "No predictions with logprob data in the selected runs. "
                "Re-run with `inference.logprobs: true` in your run-spec to populate confidence."
            )
        else:
            models_with_lp = sorted(with_logprobs["model"].unique().tolist())
            all_models = sorted(preds["model"].unique().tolist())
            missing = [m for m in all_models if m not in models_with_lp]

            n_bins = st.slider("Reliability bins", min_value=5, max_value=20, value=15)

            import matplotlib.pyplot as plt

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


# ── View: Robustness ──────────────────────────────────────────────────────────

elif view == "Robustness":
    st.title("Robustness")
    st.caption(
        "Per-model behaviour under controlled input perturbations. Each row pairs "
        "the un-perturbed baseline against a perturbed version on the same instances "
        "and reports accuracy, prediction flip rate, and the direction of those flips."
    )

    preds = load_predictions_with_gold()
    if selected_runs:
        preds = preds[preds["run_id"].isin(selected_runs)]

    pert_rows = preds[preds["perturbation"].notna()]
    if pert_rows.empty:
        st.info(
            "**No perturbed predictions in the selected runs.** Run "
            "`puma run specs/runs/sweep_bias_perturbations.yaml` to populate this view."
        )
    else:
        from puma.metrics.fairness import perturbation_disparity

        rows: list[dict] = []
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
        else:
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

            import matplotlib.pyplot as plt

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


# ── View: Fairness ────────────────────────────────────────────────────────────

elif view == "Fairness":
    st.title("Fairness")
    st.caption(
        "Bias evaluation via gender-prefix signal injection. The triage_jira corpus "
        "has 0% gendered terms (technical incident text), so we inject identity "
        "prefixes — `John Smith reported:` vs `Mary Smith reported:` — and measure "
        "whether the same instance is classified differently."
    )

    preds = load_predictions_with_gold()
    if selected_runs:
        preds = preds[preds["run_id"].isin(selected_runs)]

    gender_perts = ["gender_swap_prefix_male", "gender_swap_prefix_female"]
    gender_rows = preds[preds["perturbation"].isin(gender_perts)]
    if gender_rows.empty:
        st.info(
            "**No gender-prefix perturbation runs in the selected runs.** Run "
            "`puma run specs/runs/sweep_bias_perturbations.yaml` to populate this view."
        )
    else:
        from puma.metrics.fairness import perturbation_disparity

        st.subheader("Prefix vs un-perturbed baseline")
        baseline_rows: list[dict] = []
        directional_rows: list[dict] = []
        for model in sorted(preds["model"].dropna().unique()):
            base = preds[(preds["model"] == model) & preds["perturbation"].isna()]
            base_lookup = dict(zip(base["instance_id"], base["parsed_label"], strict=False))
            gold_lookup = dict(zip(base["instance_id"], base["gold_label"], strict=False))
            sub_by_pert: dict[str, dict] = {}
            for pert in gender_perts:
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

            if all(p in sub_by_pert for p in gender_perts):
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

        st.caption("Methodology and full discussion: `docs/results/bias_evaluation.md`.")


# ── View: Sustainability Frontier ─────────────────────────────────────────────

elif view == "Sustainability Frontier":
    st.title("Sustainability Frontier")
    st.caption(
        "Quality vs. carbon cost. Each point is a run; axes show F1 macro against CO₂ (g) "
        "emitted, measured by CodeCarbon. Runs near the top-left are Pareto-efficient "
        "(high quality per gram of CO₂)."
    )

    sus = load_sustainability(DB_PATH)
    if sus.empty:
        _no_data()
    else:
        if selected_runs:
            sus = sus[sus["run_id"].isin(selected_runs)]

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
            import matplotlib.pyplot as plt

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


# ── View: Instance Drill-down ─────────────────────────────────────────────────

elif view == "Instance Drill-down":
    st.title("Instance Drill-down")
    st.caption(
        "Per-instance inspection: gold label, parsed prediction, parse status, "
        "logprob-derived confidence, and the top-K alternatives at the first token."
    )

    preds = load_predictions_with_gold()
    if preds.empty:
        _no_data()
    else:
        if selected_runs:
            preds = preds[preds["run_id"].isin(selected_runs)]

        run_options = preds["run_id"].unique().tolist()
        chosen_run = st.selectbox("Run", run_options)

        if chosen_run:
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

            instance_options = filtered["instance_id"].unique().tolist()
            if not instance_options:
                st.info("No instances match the current filters.")
            else:
                chosen_instance = st.selectbox("Inspect instance", instance_options)
                if chosen_instance:
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
                                st.code(
                                    f"{pred.get('tokens_in', '?')} / {pred.get('tokens_out', '?')}"
                                )
                                st.markdown("**Prompt hash**")
                                st.code(pred.get("prompt_hash", "n/a"))

                            lp = pred.get("logprobs_json")
                            if pd.notna(lp):
                                import json

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
                                                "prob": f"{__import__('math').exp(t.get('logprob', 0.0)):.4f}",
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
