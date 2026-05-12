"""Statistical tests for model comparison.

Reference:
    Wilcoxon, F. (1945). Individual comparisons by ranking methods.
    Biometrics Bulletin, 1(6), 80-83.
    Demšar, J. (2006). Statistical comparisons of classifiers over
    multiple data sets. JMLR 7, 1-30.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import ArrayLike
from scipy import stats


def wilcoxon_signed_rank_models(
    preds_a: ArrayLike,
    preds_b: ArrayLike,
    gold: ArrayLike,
) -> dict[str, Any]:
    """Wilcoxon signed-rank test on two models' paired correctness.

    For each instance, compute whether each model's prediction equals
    the gold label (1) or not (0). The paired difference
    ``correct_a - correct_b`` is fed to ``scipy.stats.wilcoxon`` which
    tests whether the median of paired differences is zero (two-sided).

    Parameters
    ----------
    preds_a, preds_b : array-like
        Predicted labels from model A and B on the *same* instance set,
        in the *same* order.
    gold : array-like
        Ground-truth labels for that instance set.

    Returns
    -------
    dict with keys:
        - ``statistic`` (float): Wilcoxon test statistic. Zero when all
          paired differences are zero (no information).
        - ``p_value`` (float): two-sided p-value in [0, 1]. One when
          all differences are zero.
        - ``n_pairs`` (int): number of non-tied pairs used in the test
          (pairs with ``correct_a == correct_b`` are dropped).
        - ``mean_diff`` (float): mean of ``correct_a - correct_b``
          over the full sample (kept including ties for context).
    """
    a = np.asarray(preds_a)
    b = np.asarray(preds_b)
    g = np.asarray(gold)

    if not (a.shape == b.shape == g.shape):
        raise ValueError(f"Shape mismatch: preds_a {a.shape}, preds_b {b.shape}, gold {g.shape}")
    if a.size == 0:
        return {"statistic": 0.0, "p_value": 1.0, "n_pairs": 0, "mean_diff": 0.0}

    correct_a = (a == g).astype(int)
    correct_b = (b == g).astype(int)
    diff = correct_a - correct_b
    n_nonzero = int((diff != 0).sum())
    mean_diff = float(diff.mean())

    if n_nonzero == 0:
        return {"statistic": 0.0, "p_value": 1.0, "n_pairs": 0, "mean_diff": mean_diff}

    result = stats.wilcoxon(correct_a, correct_b, zero_method="wilcox")
    return {
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "n_pairs": n_nonzero,
        "mean_diff": mean_diff,
    }
