"""Unit tests for puma.metrics.statistical_tests — Wilcoxon signed-rank.

Reference:
    Wilcoxon, F. (1945). Individual comparisons by ranking methods.
    Biometrics Bulletin, 1(6), 80-83.
    Demšar, J. (2006). Statistical comparisons of classifiers over
    multiple data sets. JMLR 7, 1-30.
"""

from __future__ import annotations

import numpy as np
import pytest

from puma.metrics.statistical_tests import wilcoxon_signed_rank_models


@pytest.mark.unit
class TestWilcoxonSignedRank:
    def test_identical_models_not_significant(self) -> None:
        """Two identical prediction streams produce zero differences;
        the test cannot reject the null hypothesis."""
        preds_a = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0])
        preds_b = preds_a.copy()
        gold = np.array([1, 0, 1, 1, 0, 0, 0, 1, 1, 1])
        result = wilcoxon_signed_rank_models(preds_a, preds_b, gold)
        assert result["p_value"] >= 0.05
        assert result["n_pairs"] == 0
        assert result["mean_diff"] == pytest.approx(0.0, abs=1e-9)

    def test_clearly_different_models_significant(self) -> None:
        """Model A perfect, Model B always wrong: clearly significant.

        With n=10 paired differences all equal to +1, the Wilcoxon
        signed-rank test yields a small p-value (<0.05)."""
        gold = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0])
        preds_a = gold.copy()
        preds_b = 1 - gold
        result = wilcoxon_signed_rank_models(preds_a, preds_b, gold)
        assert result["p_value"] < 0.05
        assert result["n_pairs"] == 10
        assert result["mean_diff"] == pytest.approx(1.0, abs=1e-9)

    def test_returns_required_fields(self) -> None:
        """Result must always carry p_value, statistic, n_pairs, mean_diff."""
        gold = np.array([1, 0, 1, 0, 1])
        preds_a = np.array([1, 0, 1, 1, 1])  # 4/5 correct
        preds_b = np.array([1, 1, 0, 0, 1])  # 2/5 correct
        result = wilcoxon_signed_rank_models(preds_a, preds_b, gold)
        for key in ("p_value", "statistic", "n_pairs", "mean_diff"):
            assert key in result, f"missing key: {key}"
        assert result["n_pairs"] >= 1

    def test_p_value_in_unit_interval(self) -> None:
        """p_value is a probability — must lie in [0, 1]."""
        rng = np.random.default_rng(42)
        gold = rng.integers(0, 2, 50)
        preds_a = rng.integers(0, 2, 50)
        preds_b = rng.integers(0, 2, 50)
        result = wilcoxon_signed_rank_models(preds_a, preds_b, gold)
        assert 0.0 <= result["p_value"] <= 1.0
