"""Unit tests for puma.metrics.accuracy — numeric correctness vs sklearn."""

from __future__ import annotations

import pytest
from sklearn.metrics import f1_score, mean_absolute_error

from puma.metrics.accuracy import (
    classification_metrics,
    regression_metrics,
)


@pytest.mark.unit
class TestClassificationMetrics:
    Y_TRUE = ["Critical", "Major", "Minor", "Trivial", "Critical", "Major"]
    Y_PRED = ["Critical", "Major", "Minor", "Major", "Critical", "Trivial"]
    LABELS = ["Critical", "Major", "Minor", "Trivial"]

    def test_f1_macro_matches_sklearn(self):
        result = classification_metrics(self.Y_TRUE, self.Y_PRED, self.LABELS)
        expected = f1_score(self.Y_TRUE, self.Y_PRED, labels=self.LABELS, average="macro")
        assert abs(result["f1_macro"] - expected) < 1e-9

    def test_f1_weighted_present(self):
        result = classification_metrics(self.Y_TRUE, self.Y_PRED, self.LABELS)
        assert 0.0 <= result["f1_weighted"] <= 1.0

    def test_accuracy_present(self):
        result = classification_metrics(self.Y_TRUE, self.Y_PRED, self.LABELS)
        assert 0.0 <= result["accuracy"] <= 1.0

    def test_confusion_matrix_shape(self):
        result = classification_metrics(self.Y_TRUE, self.Y_PRED, self.LABELS)
        cm = result["confusion_matrix"]
        assert len(cm) == len(self.LABELS)
        assert all(len(row) == len(self.LABELS) for row in cm)

    def test_per_class_keys(self):
        result = classification_metrics(self.Y_TRUE, self.Y_PRED, self.LABELS)
        assert "per_class" in result

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            classification_metrics([], [], self.LABELS)

    def test_perfect_f1(self):
        labels = ["A", "B"]
        result = classification_metrics(["A", "B", "A"], ["A", "B", "A"], labels)
        assert abs(result["f1_macro"] - 1.0) < 1e-9


@pytest.mark.unit
class TestRegressionMetrics:
    Y_TRUE = [1.0, 3.0, 5.0, 8.0, 13.0]
    Y_PRED = [2.0, 3.0, 5.0, 8.0, 13.0]

    def test_mae_matches_sklearn(self):
        result = regression_metrics(self.Y_TRUE, self.Y_PRED)
        expected = mean_absolute_error(self.Y_TRUE, self.Y_PRED)
        assert abs(result["mae"] - expected) < 1e-9

    def test_mdae_present(self):
        result = regression_metrics(self.Y_TRUE, self.Y_PRED)
        assert result["mdae"] >= 0.0

    def test_rmse_present(self):
        result = regression_metrics(self.Y_TRUE, self.Y_PRED)
        assert result["rmse"] >= 0.0

    def test_rmse_gte_mae(self):
        result = regression_metrics(self.Y_TRUE, self.Y_PRED)
        assert result["rmse"] >= result["mae"] - 1e-9

    def test_perfect_predictions(self):
        perfect = [1.0, 3.0, 5.0]
        result = regression_metrics(perfect, perfect)
        assert result["mae"] == 0.0
        assert result["rmse"] == 0.0

    def test_bins_keys_present(self):
        result = regression_metrics(self.Y_TRUE, self.Y_PRED)
        assert "mae_by_bin" in result

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            regression_metrics([], [])
