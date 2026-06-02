"""PUMA Streamlit dashboard router.

Each top-level view lives in its own module under
``src/puma/dashboard/views/`` and exposes a ``render()`` entry point.
This file handles page config, sidebar (logo, dark-mode toggle,
filters), session-state filter publication, and dispatch.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from puma.dashboard.data import load_predictions, load_runs
from puma.dashboard.views import (
    community,
    fairness,
    instance_drilldown,
    model_comparison,
    multi_model,
    overview,
    reliability,
    robustness,
    sustainability,
)

DB_PATH = Path("data/puma.db")
LOGO_PATH = Path(__file__).resolve().parents[3] / "assets" / "img" / "PUMA.png"

VIEWS = {
    "📊 Overview": overview.render,
    "🆚 Model Comparison": model_comparison.render,
    "🔬 Multi-model": multi_model.render,
    "🎯 Reliability": reliability.render,
    "🛡️ Robustness": robustness.render,
    "⚖️ Fairness": fairness.render,
    "🌱 Sustainability Frontier": sustainability.render,
    "🔍 Instance Drill-down": instance_drilldown.render,
    "🤝 Community": community.render,
}

st.set_page_config(
    page_title="PUMA Dashboard",
    page_icon="🐾",
    layout="wide",
)

# ── Sidebar: branding ─────────────────────────────────────────────────────────

if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), width=160)
st.sidebar.title("PUMA")
st.sidebar.caption("Project Understanding & Management with Agents")

# ── Sidebar: dark mode ────────────────────────────────────────────────────────

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
        .stDataFrame, .stDataFrame * { color: #E5E7EB !important; }
        .stDataFrame [data-baseweb="table-cell"],
        .stDataFrame [role="row"],
        .stDataFrame thead,
        .stDataFrame tbody { background-color: #16213E !important; }
        h1, h2, h3, h4 { color: #5EE6C2 !important; }
        a { color: #82E9D9; }
        [data-testid="stAlert"] { background-color: #0F3460; color: #E5E7EB; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ── Sidebar: navigation ───────────────────────────────────────────────────────

selected_view = st.sidebar.radio("View", list(VIEWS.keys()))

if st.sidebar.button("📖 Show tour"):
    st.session_state["tour_dismissed"] = False
    st.rerun()

# ── Onboarding tour (first visit only) ────────────────────────────────────────

if not st.session_state.get("tour_dismissed", False):
    with st.expander("👋 Welcome to PUMA Dashboard — Quick tour", expanded=True):
        st.markdown(
            """
            **PUMA Dashboard** helps you explore evaluation results from local LLM
            agents on ICT Project Management tasks (issue triage, story-point
            estimation, backlog prioritization).

            #### Views

            | View | Purpose |
            |---|---|
            | 📊 **Overview** | Cohort stats across runs (CO₂, ECE, F1, latency) |
            | 🆚 **Model Comparison** | Mean ± std across seeds + heatmap + Wilcoxon |
            | 🎯 **Reliability** | Calibration (ECE) and reliability diagrams |
            | 🛡️ **Robustness** | Performance under input perturbations |
            | ⚖️ **Fairness** | Bias via gender-prefix signal injection |
            | 🌱 **Sustainability Frontier** | F1 vs CO₂ Pareto |
            | 🔍 **Instance Drill-down** | Per-prediction inspection + top-K logprobs |

            #### Tips

            - **Start with Overview** for context, then drill down with the
              sidebar filters (Runs, Date range, Models).
            - **Hover** any metric to see its definition (tooltip).
            - Tables expose a **📥 Download CSV** button for offline analysis.
            - **🌙 Dark mode** toggle in the sidebar for evening review.
            - You can re-open this tour anytime via **📖 Show tour** in the sidebar.

            Built with Streamlit · 100 % local · no telemetry.
            """
        )
        if st.button("Got it, don't show again", key="tour_dismiss"):
            st.session_state["tour_dismissed"] = True
            st.rerun()

# ── Sidebar: filters (published to session_state) ─────────────────────────────

runs_df = load_runs(DB_PATH)

if runs_df.empty:
    st.session_state["selected_runs"] = []
    st.session_state["selected_models"] = []
else:
    all_run_ids = runs_df["run_id"].tolist()
    st.session_state["selected_runs"] = st.sidebar.multiselect(
        "Runs", all_run_ids, default=all_run_ids[:5]
    )

    # Date filter (UI only; views can derive their own date filter if needed)
    if "started_at" in runs_df.columns:
        runs_df["started_at"] = runs_df["started_at"].apply(lambda x: str(x)[:10] if x else "")
        dates = sorted(runs_df["started_at"].unique())
        if len(dates) > 1:
            st.sidebar.select_slider("Date range", options=dates, value=(dates[0], dates[-1]))

    preds_df = load_predictions(DB_PATH)
    if not preds_df.empty and "model" in preds_df.columns:
        model_options = sorted(preds_df["model"].unique().tolist())
        st.session_state["selected_models"] = st.sidebar.multiselect(
            "Models", model_options, default=model_options
        )
    else:
        st.session_state["selected_models"] = []

# ── Dispatch ──────────────────────────────────────────────────────────────────

VIEWS[selected_view]()
