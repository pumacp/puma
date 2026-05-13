"""Unit tests for perturbation_disparity in puma.metrics.fairness.

Compares baseline vs perturbed predictions on the same instance set
against the gold labels to surface (a) absolute accuracy change and
(b) per-instance prediction flips (raw + split by flip direction).
"""

from __future__ import annotations

import numpy as np
import pytest

from puma.metrics.fairness import perturbation_disparity


@pytest.mark.unit
class TestPerturbationDisparityShape:
    def test_returns_expected_keys(self) -> None:
        gold = np.array(["A", "A", "B", "B"])
        base = np.array(["A", "A", "B", "B"])
        out = perturbation_disparity(base, base, gold)
        assert set(out.keys()) == {
            "acc_baseline",
            "acc_perturbed",
            "disparity",
            "flip_rate",
            "flip_to_correct",
            "flip_to_incorrect",
        }


@pytest.mark.unit
class TestNoChange:
    def test_identical_predictions_zero_everything(self) -> None:
        gold = np.array(["A", "B", "A", "B"])
        preds = np.array(["A", "B", "A", "B"])
        out = perturbation_disparity(preds, preds, gold)
        assert out["acc_baseline"] == 1.0
        assert out["acc_perturbed"] == 1.0
        assert out["disparity"] == 0.0
        assert out["flip_rate"] == 0.0
        assert out["flip_to_correct"] == 0.0
        assert out["flip_to_incorrect"] == 0.0


@pytest.mark.unit
class TestFlipDirections:
    def test_all_flips_to_correct(self) -> None:
        # Baseline wrong everywhere; perturbed right everywhere.
        gold = np.array(["A", "A", "A", "A"])
        base = np.array(["B", "B", "B", "B"])
        pert = np.array(["A", "A", "A", "A"])
        out = perturbation_disparity(base, pert, gold)
        assert out["acc_baseline"] == 0.0
        assert out["acc_perturbed"] == 1.0
        assert out["disparity"] == 1.0
        assert out["flip_rate"] == 1.0
        assert out["flip_to_correct"] == 1.0
        assert out["flip_to_incorrect"] == 0.0

    def test_all_flips_to_incorrect(self) -> None:
        # Baseline right everywhere; perturbed wrong everywhere.
        gold = np.array(["A", "A", "A", "A"])
        base = np.array(["A", "A", "A", "A"])
        pert = np.array(["B", "B", "B", "B"])
        out = perturbation_disparity(base, pert, gold)
        assert out["acc_baseline"] == 1.0
        assert out["acc_perturbed"] == 0.0
        assert out["disparity"] == 1.0
        assert out["flip_rate"] == 1.0
        assert out["flip_to_correct"] == 0.0
        assert out["flip_to_incorrect"] == 1.0

    def test_mixed_flip_directions(self) -> None:
        # 2 of 4 flip, 1 to correct, 1 to incorrect, 2 unchanged.
        gold = np.array(["A", "A", "A", "A"])
        base = np.array(["B", "A", "B", "A"])  # 50% correct
        pert = np.array(["A", "B", "B", "A"])  # 50% correct
        out = perturbation_disparity(base, pert, gold)
        assert out["acc_baseline"] == 0.5
        assert out["acc_perturbed"] == 0.5
        assert out["disparity"] == 0.0
        assert out["flip_rate"] == 0.5  # 2/4 flipped
        # Of the 2 flips, 1 to correct (idx 0), 1 to incorrect (idx 1)
        assert out["flip_to_correct"] == 0.5
        assert out["flip_to_incorrect"] == 0.5


@pytest.mark.unit
class TestEdgeCases:
    def test_zero_flips_does_not_divide_by_zero(self) -> None:
        gold = np.array(["A", "A"])
        base = np.array(["B", "B"])
        pert = np.array(["B", "B"])  # no flips
        out = perturbation_disparity(base, pert, gold)
        assert out["flip_rate"] == 0.0
        assert out["flip_to_correct"] == 0.0
        assert out["flip_to_incorrect"] == 0.0

    def test_accepts_list_input(self) -> None:
        # Convenience for callers that hand off Python lists.
        out = perturbation_disparity(["A", "B"], ["A", "B"], ["A", "B"])
        assert out["disparity"] == 0.0

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError):
            perturbation_disparity(["A"], ["A", "B"], ["A"])
