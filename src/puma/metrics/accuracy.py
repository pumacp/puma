"""Accuracy metrics: classification (F1, confusion matrix) and regression (MAE, RMSE)."""

from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    precision_recall_fscore_support,
)

SP_BINS: dict[str, tuple[float, float]] = {
    "1-3": (1, 3),
    "5-8": (5, 8),
    "13-21": (13, 21),
    "34+": (34, float("inf")),
}


def classification_metrics(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str],
) -> dict:
    """Compute F1-macro, F1-weighted, accuracy, confusion matrix, per-class metrics."""
    if not y_true:
        raise ValueError("classification_metrics: empty y_true/y_pred")

    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    per_class = {
        lbl: {"precision": float(prec[i]), "recall": float(rec[i]), "f1": float(f1[i])}
        for i, lbl in enumerate(labels)
    }

    return {
        "f1_macro": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "labels": labels,
        "per_class": per_class,
        "n_samples": len(y_true),
    }


def regression_metrics(
    y_true: list[float],
    y_pred: list[float],
) -> dict:
    """Compute MAE, MdAE, RMSE, and MAE by story-point bin."""
    if not y_true:
        raise ValueError("regression_metrics: empty y_true/y_pred")

    arr_true = np.array(y_true, dtype=float)
    arr_pred = np.array(y_pred, dtype=float)
    errors = np.abs(arr_true - arr_pred)

    mae_by_bin: dict[str, float | None] = {}
    for bin_name, (lo, hi) in SP_BINS.items():
        mask = (arr_true >= lo) & (arr_true <= hi)
        if mask.sum() > 0:
            mae_by_bin[bin_name] = float(np.mean(errors[mask]))
        else:
            mae_by_bin[bin_name] = None

    return {
        "mae": float(mean_absolute_error(arr_true, arr_pred)),
        "mdae": float(np.median(errors)),
        "rmse": float(math.sqrt(float(np.mean(errors**2)))),
        "mae_by_bin": mae_by_bin,
        "n_samples": len(y_true),
    }


def ranking_metrics(
    y_true_rankings: list[list[str]],
    y_pred_rankings: list[list[str]],
    k: int = 10,
) -> dict:
    """Compute NDCG@k and MRR for pairwise ranking predictions."""
    ndcg_scores = []
    mrr_scores = []

    for true_rank, pred_rank in zip(y_true_rankings, y_pred_rankings, strict=True):
        # NDCG@k
        dcg = sum(
            (1.0 / math.log2(i + 2))
            for i, item in enumerate(pred_rank[:k])
            if item in true_rank
        )
        idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(true_rank), k)))
        ndcg_scores.append(dcg / idcg if idcg > 0 else 0.0)

        # MRR
        for rank, item in enumerate(pred_rank, 1):
            if item in true_rank:
                mrr_scores.append(1.0 / rank)
                break
        else:
            mrr_scores.append(0.0)

    return {
        f"ndcg_at_{k}": float(np.mean(ndcg_scores)) if ndcg_scores else 0.0,
        "mrr": float(np.mean(mrr_scores)) if mrr_scores else 0.0,
        "n_queries": len(y_true_rankings),
    }
