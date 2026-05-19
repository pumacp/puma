"""Fairness metrics: per-group accuracy disparity and fairness gap."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from sklearn.metrics import f1_score


def fairness_report(
    y_true: list[str],
    y_pred: list[str],
    groups: list[str],
    metric: str = "accuracy",
) -> dict[str, Any]:
    """Compute per-group performance, disparity, worst-group, and fairness gap.

    Args:
        y_true: Ground-truth labels.
        y_pred: Predicted labels.
        groups: Subgroup membership for each instance (e.g. project_key, language).
        metric: "accuracy" or "f1_macro".

    Returns:
        dict with keys: per_group, global_metric, worst_group, fairness_gap, disparities.
    """
    unique_groups = sorted(set(groups))

    def _metric(yt: list[str], yp: list[str]) -> float:
        if not yt:
            return 0.0
        if metric == "f1_macro":
            labels = sorted(set(yt) | set(yp))
            return float(f1_score(yt, yp, labels=labels, average="macro", zero_division=0))
        return sum(a == b for a, b in zip(yt, yp, strict=True)) / len(yt)

    per_group: dict[str, float] = {}
    for grp in unique_groups:
        indices = [i for i, g in enumerate(groups) if g == grp]
        grp_true = [y_true[i] for i in indices]
        grp_pred = [y_pred[i] for i in indices]
        per_group[grp] = _metric(grp_true, grp_pred)

    global_val = _metric(y_true, y_pred)
    worst_group = min(per_group, key=per_group.__getitem__)
    best_val = max(per_group.values())
    worst_val = per_group[worst_group]

    return {
        "per_group": per_group,
        "global_metric": global_val,
        "worst_group": worst_group,
        "fairness_gap": best_val - worst_val,
        "disparities": {g: abs(v - global_val) for g, v in per_group.items()},
    }


def perturbation_disparity(
    predictions_baseline: Sequence[str] | np.ndarray,
    predictions_perturbed: Sequence[str] | np.ndarray,
    gold: Sequence[str] | np.ndarray,
) -> dict[str, float]:
    """Quantify model sensitivity to a perturbation by paired comparison.

    Compares predictions on the original (baseline) instances against
    predictions on the same instances after a perturbation has been
    applied, holding gold labels constant.

    Args:
        predictions_baseline: predicted labels on un-perturbed instances.
        predictions_perturbed: predicted labels on the same instances
            after perturbation.
        gold: ground-truth labels (un-perturbed).

    Returns:
        - acc_baseline / acc_perturbed: accuracy on each condition.
        - disparity: ``|acc_baseline - acc_perturbed|``.
        - flip_rate: fraction of instances where the prediction changed.
        - flip_to_correct: of the flipped instances, fraction that moved
          from wrong to right.
        - flip_to_incorrect: of the flipped instances, fraction that
          moved from right to wrong.
    """
    base = np.asarray(predictions_baseline)
    pert = np.asarray(predictions_perturbed)
    g = np.asarray(gold)

    if not (base.shape == pert.shape == g.shape):
        raise ValueError(
            f"Shape mismatch: baseline {base.shape}, perturbed {pert.shape}, gold {g.shape}"
        )

    acc_b = float((base == g).mean()) if base.size else 0.0
    acc_p = float((pert == g).mean()) if pert.size else 0.0
    flipped = base != pert
    flip_rate = float(flipped.mean()) if base.size else 0.0

    n_flips = int(flipped.sum())
    if n_flips > 0:
        base_correct_at_flip = base[flipped] == g[flipped]
        pert_correct_at_flip = pert[flipped] == g[flipped]
        flip_to_correct = float(((~base_correct_at_flip) & pert_correct_at_flip).sum() / n_flips)
        flip_to_incorrect = float((base_correct_at_flip & (~pert_correct_at_flip)).sum() / n_flips)
    else:
        flip_to_correct = 0.0
        flip_to_incorrect = 0.0

    return {
        "acc_baseline": acc_b,
        "acc_perturbed": acc_p,
        "disparity": abs(acc_b - acc_p),
        "flip_rate": flip_rate,
        "flip_to_correct": flip_to_correct,
        "flip_to_incorrect": flip_to_incorrect,
    }
