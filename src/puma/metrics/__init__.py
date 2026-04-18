"""Multi-dimensional metrics: accuracy, calibration, robustness, fairness, efficiency, stability, sustainability."""

from puma.metrics.accuracy import classification_metrics, ranking_metrics, regression_metrics
from puma.metrics.calibration import (
    brier_score,
    class_confidence_from_logprobs,
    expected_calibration_error,
    maximum_calibration_error,
)
from puma.metrics.efficiency import parse_ollama_timings, percentiles, throughput
from puma.metrics.fairness import fairness_report
from puma.metrics.robustness import consistency_rate, robustness_score
from puma.metrics.stability import stability_report, stability_score

__all__ = [
    "classification_metrics",
    "regression_metrics",
    "ranking_metrics",
    "expected_calibration_error",
    "maximum_calibration_error",
    "brier_score",
    "class_confidence_from_logprobs",
    "robustness_score",
    "consistency_rate",
    "fairness_report",
    "percentiles",
    "throughput",
    "parse_ollama_timings",
    "stability_score",
    "stability_report",
]
