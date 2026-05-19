"""Reusable Streamlit components for the PUMA dashboard."""

from __future__ import annotations

import io
from itertools import pairwise
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from matplotlib.figure import Figure


def metric_card(
    label: str,
    value: Any,
    delta: Any = None,
    fmt: str = "{:.4f}",
    help: str | None = None,
) -> None:
    """Render a single st.metric card, formatting floats.

    Args:
        help: optional tooltip shown on hover (Streamlit's ``help=`` arg).
    """
    import streamlit as st

    display = fmt.format(value) if isinstance(value, float) else str(value)
    delta_str = (
        fmt.format(delta)
        if isinstance(delta, float)
        else (str(delta) if delta is not None else None)
    )
    st.metric(label=label, value=display, delta=delta_str, help=help)


def empty_filtered_state(view_name: str, has_data_in_db: bool = True) -> None:
    """Render a consistent message when filters or DB yield no data.

    Args:
        view_name: human-readable view name, e.g. "Reliability".
        has_data_in_db: True if the database has rows but filters exclude
            them; False if the DB itself is empty.
    """
    import streamlit as st

    if has_data_in_db:
        st.info(
            f"ℹ️ No data matches the current filters in **{view_name}**.\n\n"  # noqa: RUF001 -- intentional Unicode glyph for UI typography
            "Try:\n"
            "- Expanding the date range\n"
            "- Selecting more runs/models in the sidebar\n"
            "- Clearing filters to see all data"
        )
    else:
        st.info(
            f"ℹ️ No data available for **{view_name}** in the database.\n\n"  # noqa: RUF001 -- intentional Unicode glyph for UI typography
            "Populate the DB first, e.g.:\n"
            "```\npuma run specs/runs/baseline_triage_with_logprobs.yaml\n```"
        )


def download_csv_button(
    df: pd.DataFrame,
    file_name: str,
    label: str = "📥 Download CSV",
    key: str | None = None,
) -> None:
    """Render a download button for ``df`` serialised to CSV."""
    import streamlit as st

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=file_name,
        mime="text/csv",
        key=key,
    )


def comparison_table(run_metrics: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Turn {run_id: {metric: value}} into a display DataFrame."""
    if not run_metrics:
        return pd.DataFrame()
    df = pd.DataFrame(run_metrics).T
    df.index.name = "run_id"
    return df.reset_index()


def reliability_plot(confs: list[float], corrects: list[bool], n_bins: int = 10) -> Figure:
    """Return a matplotlib Figure for a reliability diagram."""
    import matplotlib.pyplot as plt
    import numpy as np

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_accs, bin_confs, bin_counts = [], [], []
    for lo, hi in pairwise(bins):
        mask = [(lo <= c < hi) for c in confs]
        if sum(mask) == 0:
            continue
        bin_confs.append(float(np.mean([c for c, m in zip(confs, mask, strict=False) if m])))
        bin_accs.append(float(np.mean([int(a) for a, m in zip(corrects, mask, strict=False) if m])))
        bin_counts.append(sum(mask))

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "k--", label="Perfect calibration")
    ax.bar(bin_confs, bin_accs, width=1.0 / n_bins, alpha=0.6, label="Accuracy per bin")
    ax.set_xlabel("Confidence")
    ax.set_ylabel("Accuracy")
    ax.set_title("Reliability Diagram")
    ax.legend()
    return fig


def pareto_scatter(
    xs: list[float],
    ys: list[float],
    labels: list[str],
    x_label: str = "Efficiency",
    y_label: str = "Quality",
) -> Figure:
    """Return a matplotlib Figure for a Pareto / efficiency-quality scatter."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(xs, ys, s=80, zorder=3)
    for x, y, lbl in zip(xs, ys, labels, strict=False):
        ax.annotate(lbl, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title("Sustainability Frontier")
    ax.grid(alpha=0.3)
    return fig


def fig_to_bytes(fig: Figure, fmt: str = "png") -> bytes:
    """Serialize a matplotlib Figure to bytes for st.download_button."""
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, bbox_inches="tight")
    buf.seek(0)
    return buf.read()
