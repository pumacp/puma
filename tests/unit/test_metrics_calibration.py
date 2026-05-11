"""Unit tests for puma.metrics.calibration — ECE, MCE, Brier score."""

from __future__ import annotations

import math

import pytest

from puma.metrics.calibration import (
    brier_score,
    class_confidence_from_logprobs,
    expected_calibration_error,
    maximum_calibration_error,
)
from puma.runtime.client import TokenLogprob


@pytest.mark.unit
class TestECE:
    def test_perfect_calibration(self):
        # 80 items at 0.8 confidence, exactly 80% correct → bin gap = 0
        # 20 items at 0.2 confidence, exactly 20% correct → bin gap = 0
        confs = [0.8] * 80 + [0.2] * 20
        corrects = [True] * 64 + [False] * 16 + [True] * 4 + [False] * 16
        ece = expected_calibration_error(confs, corrects)
        assert ece < 0.01

    def test_worst_calibration(self):
        confs = [0.9] * 100
        corrects = [False] * 100
        ece = expected_calibration_error(confs, corrects)
        assert ece > 0.5

    def test_output_in_range(self):
        import random

        rng = random.Random(42)
        confs = [rng.random() for _ in range(200)]
        corrects = [rng.random() > 0.5 for _ in range(200)]
        ece = expected_calibration_error(confs, corrects)
        assert 0.0 <= ece <= 1.0

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            expected_calibration_error([], [])

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="mismatch"):
            expected_calibration_error([0.5, 0.6], [True])


@pytest.mark.unit
class TestECECanonical:
    """Analytical Guo et al. 2017 cases with strict 1e-6 tolerance.

    Reference:
        Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017).
        On calibration of modern neural networks. ICML 2017.

    ECE = sum_m (|B_m| / n) * |acc(B_m) - conf(B_m)|
    """

    TOLERANCE = 1e-6

    def test_single_sample_perfect_confidence_returns_zero(self):
        """A single sample with conf=1.0 and correct: ECE = 0 exactly."""
        ece = expected_calibration_error([1.0], [True], n_bins=10)
        assert ece == pytest.approx(0.0, abs=self.TOLERANCE)

    def test_maximum_miscalibration_equals_one(self):
        """All samples conf=1.0, all incorrect: ECE = 1.0 exactly.

        Only one bin (the [0.9, 1.0] bin) is populated. n=5 samples,
        accuracy=0.0, confidence=1.0. ECE = (5/5) * |0.0 - 1.0| = 1.0.
        """
        confs = [1.0] * 5
        corrects = [False] * 5
        ece = expected_calibration_error(confs, corrects, n_bins=10)
        assert ece == pytest.approx(1.0, abs=self.TOLERANCE)

    def test_one_bin_known_gap(self):
        """10 samples all at conf=0.9, 5 correct.

        Single populated bin: |B_m|=10, n=10, conf=0.9, acc=0.5.
        ECE = (10/10) * |0.5 - 0.9| = 0.4 exactly.
        """
        confs = [0.9] * 10
        corrects = [True] * 5 + [False] * 5
        ece = expected_calibration_error(confs, corrects, n_bins=10)
        assert ece == pytest.approx(0.4, abs=self.TOLERANCE)

    def test_two_bins_known_value(self):
        """Two distinct populated bins, hand-computable.

        Bin A (conf=0.2): 5 samples, 1 correct → acc=0.2, conf=0.2,
            gap=0.0, weight=5/10=0.5.
        Bin B (conf=0.8): 5 samples, 3 correct → acc=0.6, conf=0.8,
            gap=0.2, weight=5/10=0.5.
        ECE = 0.5*0.0 + 0.5*0.2 = 0.1 exactly.
        """
        confs = [0.2] * 5 + [0.8] * 5
        corrects = [False, False, False, False, True, True, True, True, False, False]
        ece = expected_calibration_error(confs, corrects, n_bins=10)
        assert ece == pytest.approx(0.1, abs=self.TOLERANCE)

    def test_empty_bins_do_not_contribute(self):
        """Most bins empty, one bin populated and perfectly calibrated.

        All 10 samples land in the [0.9, 1.0] bin (conf=0.95, 9 of 10
        correct = acc=0.9). The 9 empty bins below must be skipped
        (not produce NaN or division-by-zero). Only the populated bin
        contributes: weight=10/10=1.0, gap=|0.9 - 0.95|=0.05.
        Expected ECE = 0.05.
        """
        confs = [0.95] * 10
        corrects = [True] * 9 + [False] * 1
        ece = expected_calibration_error(confs, corrects, n_bins=10)
        assert ece == pytest.approx(0.05, abs=self.TOLERANCE)

    def test_two_isolated_bins_with_binary_outcomes(self):
        """One sample in bin 0 (conf=0.05, incorrect) and one in bin 9
        (conf=0.95, correct). Each contributes its own conf-vs-acc gap.

        Bin 0: |B|=1, conf=0.05, acc=0.0, gap=0.05, weight=0.5.
        Bin 9: |B|=1, conf=0.95, acc=1.0, gap=0.05, weight=0.5.
        ECE = 0.5*0.05 + 0.5*0.05 = 0.05.
        """
        confs = [0.05, 0.95]
        corrects = [False, True]
        ece = expected_calibration_error(confs, corrects, n_bins=10)
        assert ece == pytest.approx(0.05, abs=self.TOLERANCE)


@pytest.mark.unit
class TestMCE:
    def test_output_ge_ece(self):
        confs = [0.9] * 50 + [0.1] * 50
        corrects = [True] * 30 + [False] * 20 + [True] * 10 + [False] * 40
        ece = expected_calibration_error(confs, corrects)
        mce = maximum_calibration_error(confs, corrects)
        assert mce >= ece - 1e-9

    def test_output_in_range(self):
        confs = [0.7, 0.8, 0.6, 0.9]
        corrects = [True, True, False, True]
        mce = maximum_calibration_error(confs, corrects)
        assert 0.0 <= mce <= 1.0


@pytest.mark.unit
class TestBrierScore:
    def test_perfect_score_is_zero(self):
        confs = [1.0, 1.0, 0.0, 0.0]
        corrects = [True, True, False, False]
        assert abs(brier_score(confs, corrects)) < 1e-9

    def test_worst_score_is_one(self):
        confs = [1.0, 1.0]
        corrects = [False, False]
        assert abs(brier_score(confs, corrects) - 1.0) < 1e-9

    def test_output_in_range(self):
        confs = [0.3, 0.7, 0.5]
        corrects = [True, False, True]
        bs = brier_score(confs, corrects)
        assert 0.0 <= bs <= 1.0


@pytest.mark.unit
class TestClassConfidenceFromLogprobs:
    def _make_token_logprob(
        self, token: str, logprob: float, top: list[tuple[str, float]]
    ) -> TokenLogprob:
        top_lps = [TokenLogprob(token=t, logprob=lp, top_logprobs=[]) for t, lp in top]
        return TokenLogprob(token=token, logprob=logprob, top_logprobs=top_lps)

    def test_sums_to_one(self):
        first = self._make_token_logprob(
            "Critical", math.log(0.6), [("Major", math.log(0.3)), ("Minor", math.log(0.1))]
        )
        label_tokens = {
            "Critical": ["Critical", "critical"],
            "Major": ["Major", "major"],
            "Minor": ["Minor", "minor"],
            "Trivial": ["Trivial", "trivial"],
        }
        result = class_confidence_from_logprobs([first], label_tokens)
        total = sum(result.values())
        assert abs(total - 1.0) < 1e-6

    def test_dominant_class_has_highest_prob(self):
        first = self._make_token_logprob(
            "Critical", math.log(0.7), [("Major", math.log(0.2)), ("Minor", math.log(0.1))]
        )
        label_tokens = {
            "Critical": ["Critical"],
            "Major": ["Major"],
            "Minor": ["Minor"],
            "Trivial": ["Trivial"],
        }
        result = class_confidence_from_logprobs([first], label_tokens)
        assert result["Critical"] == max(result.values())

    def test_empty_logprobs_returns_empty(self):
        result = class_confidence_from_logprobs([], {"A": ["A"]})
        assert result == {}
