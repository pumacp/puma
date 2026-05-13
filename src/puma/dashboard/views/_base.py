"""Shared helpers for dashboard view modules."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

DB_PATH = Path("data/puma.db")


def no_data() -> None:
    """Render a placeholder message when the database has no runs."""
    st.info("No run data found. Run `puma run <spec.yaml>` first to generate results.")


def selected_runs() -> list[str]:
    """Sidebar-selected run IDs, or empty if the sidebar has not initialised yet."""
    return st.session_state.get("selected_runs", [])


def selected_models() -> list[str]:
    """Sidebar-selected model names, or empty if the sidebar has not initialised yet."""
    return st.session_state.get("selected_models", [])
