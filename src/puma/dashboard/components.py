"""Reusable Streamlit components for the PUMA dashboard."""

from __future__ import annotations

import io
from typing import Any

import pandas as pd


def metric_card(label: str, value: Any, delta: Any = None, fmt: str = "{:.4f}") -> None:
    """Render a single st.metric card, formatting floats."""
    import streamlit as st

    display = fmt.format(value) if isinstance(value, float) else str(value)
    delta_str = fmt.format(delta) if isinstance(delta, float) else (str(delta) if delta is not None else None)
    st.metric(label=label, value=display, delta=delta_str)


def comparison_table(run_metrics: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Turn {run_id: {metric: value}} into a display DataFrame."""
    if not run_metrics:
        return pd.DataFrame()
    df = pd.DataFrame(run_metrics).T
    df.index.name = "run_id"
    return df.reset_index()


def reliability_plot(confs: list[float], corrects: list[bool], n_bins: int = 10):
    """Return a matplotlib Figure for a reliability diagram."""
    import matplotlib.pyplot as plt
    import numpy as np

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_accs, bin_confs, bin_counts = [], [], []
    for lo, hi in zip(bins[:-1], bins[1:], strict=False):
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
):
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


def fig_to_bytes(fig, fmt: str = "png") -> bytes:
    """Serialize a matplotlib Figure to bytes for st.download_button."""
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, bbox_inches="tight")
    buf.seek(0)
    return buf.read()
