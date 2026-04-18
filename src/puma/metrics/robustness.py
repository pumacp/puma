"""Robustness metrics: robustness_score and consistency_rate."""

from __future__ import annotations


def robustness_score(metric_orig: float, metric_perturbed: float) -> float:
    """Robustness score = 1 - |metric_original - metric_perturbed|, clamped to [0, 1]."""
    return max(0.0, min(1.0, 1.0 - abs(metric_orig - metric_perturbed)))


def consistency_rate(
    preds_orig: list[str | float | None],
    preds_perturbed: list[str | float | None],
) -> float:
    """Fraction of instances where original and perturbed predictions agree."""
    if not preds_orig:
        raise ValueError("consistency_rate: empty prediction lists")
    if len(preds_orig) != len(preds_perturbed):
        raise ValueError("consistency_rate: mismatched lengths")
    matches = sum(a == b for a, b in zip(preds_orig, preds_perturbed, strict=True))
    return matches / len(preds_orig)
