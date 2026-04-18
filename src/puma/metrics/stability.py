"""Stability metrics: variance across seeds, coefficient of variation."""

from __future__ import annotations

import numpy as np


def stability_score(metric_values: list[float]) -> float:
    """Stability = 1 - (stddev / mean), clamped to [0, 1].

    Returns 1.0 for a single value or zero variance.
    """
    if not metric_values:
        raise ValueError("stability_score: empty input")
    if len(metric_values) == 1:
        return 1.0
    arr = np.array(metric_values, dtype=float)
    mean = float(np.mean(arr))
    if mean == 0.0:
        return 0.0 if float(np.std(arr)) > 0 else 1.0
    cv = float(np.std(arr)) / abs(mean)
    return max(0.0, min(1.0, 1.0 - cv))


def stability_report(metric_values: list[float]) -> dict:
    """Full stability report: mean, stddev, cv, stability score."""
    if not metric_values:
        raise ValueError("stability_report: empty input")
    arr = np.array(metric_values, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    return {
        "mean": mean,
        "stddev": std,
        "cv": std / abs(mean) if mean != 0.0 else float("inf"),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "stability": stability_score(metric_values),
        "n_seeds": len(metric_values),
    }
