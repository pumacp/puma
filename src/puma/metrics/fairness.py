"""Fairness metrics: per-group accuracy disparity and fairness gap."""

from __future__ import annotations

from sklearn.metrics import f1_score


def fairness_report(
    y_true: list[str],
    y_pred: list[str],
    groups: list[str],
    metric: str = "accuracy",
) -> dict:
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
