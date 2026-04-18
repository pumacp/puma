"""Unit tests for basic accuracy metric calculations."""

import pytest
from sklearn.metrics import confusion_matrix, f1_score


@pytest.mark.unit
class TestSklearnMetrics:
    def test_f1_macro_basic(self):
        y_true = ["A", "B", "A", "B"]
        y_pred = ["A", "B", "B", "B"]
        f1 = f1_score(y_true, y_pred, average="macro")
        assert 0.4 <= f1 <= 1.0

    def test_confusion_matrix_shape(self):
        y_true = ["A", "B", "A", "B"]
        y_pred = ["A", "B", "B", "B"]
        cm = confusion_matrix(y_true, y_pred)
        assert cm.shape == (2, 2)
        assert cm[0][0] == 1
        assert cm[1][1] == 2
