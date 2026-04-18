"""Unit tests for robustness, fairness, efficiency, stability, sustainability metrics."""

from __future__ import annotations

import pytest

from puma.metrics.efficiency import percentiles, throughput
from puma.metrics.fairness import fairness_report
from puma.metrics.robustness import consistency_rate, robustness_score
from puma.metrics.stability import stability_score
from puma.sustainability.codecarbon_wrapper import gco2_per_f1_point, gco2_per_mae_unit


@pytest.mark.unit
class TestRobustness:
    def test_score_perfect(self):
        assert robustness_score(0.80, 0.80) == pytest.approx(1.0)

    def test_score_zero_when_full_drop(self):
        assert robustness_score(1.0, 0.0) == pytest.approx(0.0)

    def test_score_in_range(self):
        s = robustness_score(0.70, 0.65)
        assert 0.0 <= s <= 1.0

    def test_consistency_perfect(self):
        preds = ["A", "B", "C"]
        assert consistency_rate(preds, preds) == pytest.approx(1.0)

    def test_consistency_zero(self):
        assert consistency_rate(["A", "A"], ["B", "B"]) == pytest.approx(0.0)

    def test_consistency_partial(self):
        rate = consistency_rate(["A", "B", "A", "B"], ["A", "B", "B", "A"])
        assert rate == pytest.approx(0.5)

    def test_consistency_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            consistency_rate([], [])


@pytest.mark.unit
class TestFairness:
    PREDS = ["A", "A", "B", "B", "A", "B"]
    TRUTHS = ["A", "A", "B", "A", "A", "B"]
    GROUPS = ["g1", "g1", "g1", "g2", "g2", "g2"]

    def test_returns_dict_with_groups(self):
        result = fairness_report(self.TRUTHS, self.PREDS, self.GROUPS)
        assert "g1" in result["per_group"]
        assert "g2" in result["per_group"]

    def test_fairness_gap_non_negative(self):
        result = fairness_report(self.TRUTHS, self.PREDS, self.GROUPS)
        assert result["fairness_gap"] >= 0.0

    def test_worst_group_key_present(self):
        result = fairness_report(self.TRUTHS, self.PREDS, self.GROUPS)
        assert result["worst_group"] in ["g1", "g2"]

    def test_single_group_gap_zero(self):
        result = fairness_report(["A", "B"], ["A", "B"], ["g1", "g1"])
        assert result["fairness_gap"] == pytest.approx(0.0)


@pytest.mark.unit
class TestEfficiency:
    def test_percentiles_p50_p95_p99(self):
        latencies = list(range(1, 101))
        result = percentiles(latencies)
        assert "p50" in result
        assert "p95" in result
        assert "p99" in result
        assert result["p50"] <= result["p95"] <= result["p99"]

    def test_throughput_calculation(self):
        tp = throughput(n_instances=60, duration_s=60.0)
        assert tp == pytest.approx(60.0)

    def test_throughput_zero_duration_raises(self):
        with pytest.raises(ValueError, match="positive"):
            throughput(60, 0.0)

    def test_percentiles_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            percentiles([])


@pytest.mark.unit
class TestStability:
    def test_perfect_stability(self):
        scores = [0.8, 0.8, 0.8, 0.8]
        assert stability_score(scores) == pytest.approx(1.0)

    def test_lower_stability_when_high_variance(self):
        s1 = stability_score([0.8, 0.8, 0.8])
        s2 = stability_score([0.5, 0.8, 1.0])
        assert s1 > s2

    def test_single_value_returns_one(self):
        assert stability_score([0.75]) == pytest.approx(1.0)

    def test_output_at_most_one(self):
        assert stability_score([0.1, 0.9]) <= 1.0

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            stability_score([])


@pytest.mark.unit
class TestSustainabilityMetrics:
    def test_gco2_per_f1_nonzero_f1(self):
        result = gco2_per_f1_point(emissions_g=100.0, f1=0.5)
        assert result == pytest.approx(200.0)

    def test_gco2_per_f1_zero_f1_returns_none(self):
        assert gco2_per_f1_point(100.0, 0.0) is None

    def test_gco2_per_mae_nonzero_mae(self):
        result = gco2_per_mae_unit(emissions_g=50.0, mae=2.5)
        assert result == pytest.approx(20.0)

    def test_gco2_per_mae_zero_mae_returns_none(self):
        assert gco2_per_mae_unit(50.0, 0.0) is None
