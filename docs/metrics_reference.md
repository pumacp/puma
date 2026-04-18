# Metrics Reference

All metric functions live in `src/puma/metrics/`. This document lists every metric with its formula, implementation module, and the scenarios where it applies.

---

## Classification Metrics

**Module**: `puma.metrics.accuracy`  
**Applies to**: `triage_jira`, `prioritization_jira`

| Metric key | Formula | Notes |
|------------|---------|-------|
| `f1_macro` | mean(F1 per class) | Equal weight per class; primary metric for triage |
| `f1_weighted` | Σ (support_c / N) × F1_c | Weighted by class frequency |
| `accuracy` | correct / N | Overall fraction correct |
| `per_class.<label>.precision` | TP / (TP + FP) | — |
| `per_class.<label>.recall` | TP / (TP + FN) | — |
| `per_class.<label>.f1` | 2 · P · R / (P + R) | Harmonic mean |
| `confusion_matrix` | C[i][j] = predicted j when true i | Stored as nested dict |
| `parse_failure_rate` | unparsed / N | Fraction where `parse_response` returned `None` |
| `n_predictions` | integer | Number of predictions included in metrics |

---

## Regression Metrics

**Module**: `puma.metrics.accuracy`  
**Applies to**: `estimation_tawos`

| Metric key | Formula | Notes |
|------------|---------|-------|
| `mae` | mean(\|y − ŷ\|) | Mean Absolute Error; story-point scale |
| `mdae` | median(\|y − ŷ\|) | Robust to outliers |
| `rmse` | √(mean((y − ŷ)²)) | Penalises large errors |
| `mae_by_bin.1-3` | MAE restricted to SP ∈ [1, 3] | Small stories |
| `mae_by_bin.5-8` | MAE restricted to SP ∈ [5, 8] | Medium stories |
| `mae_by_bin.13-21` | MAE restricted to SP ∈ [13, 21] | Large stories |
| `mae_by_bin.34+` | MAE restricted to SP ≥ 34 | Epics |

---

## Ranking Metrics

**Module**: `puma.metrics.accuracy`  
**Applies to**: `prioritization_jira` (future extension)

| Metric key | Formula | Notes |
|------------|---------|-------|
| `ndcg_at_k` | DCG@k / IDCG@k | Normalised Discounted Cumulative Gain |
| `mrr` | mean(1 / rank of first correct) | Mean Reciprocal Rank |

---

## Calibration Metrics

**Module**: `puma.metrics.calibration`  
**Requires**: `logprobs: true` in run-spec + Ollama ≥ 0.12.11

| Metric key | Formula | Notes |
|------------|---------|-------|
| `ece` | Σ_b (n_b / N) × \|acc_b − conf_b\| | Expected Calibration Error; 10 equal-width bins |
| `mce` | max_b \|acc_b − conf_b\| | Maximum Calibration Error |
| `brier_score` | mean((conf − correct)²) | Proper scoring rule |

### Confidence extraction from logprobs

```python
def class_confidence_from_logprobs(
    logprobs: list[TokenLogprob],
    label_tokens: dict[str, list[str]],
) -> dict[str, float]:
    # 1. Take top-logprob candidates from the first generated token
    # 2. Apply stable softmax: exp(lp - max_lp) for numerical stability
    # 3. Sum probabilities for all token variants of each label
    # 4. Normalise to sum to 1.0
```

`label_tokens` maps a label to its possible token representations:
```python
{"Critical": ["Critical", " Critical", "critical", "CRITICAL"]}
```

### Reliability diagram

```python
reliability_diagram(confs, corrects, output_path, n_bins=10)
# Saves a matplotlib PNG: bars = accuracy per bin, diagonal = perfect calibration
```

---

## Robustness Metrics

**Module**: `puma.metrics.robustness`

| Metric key | Formula | Notes |
|------------|---------|-------|
| `robustness_score` | max(0, min(1, 1 − \|M_orig − M_perturbed\|)) | 1 = no degradation; 0 = metric collapsed |
| `consistency_rate` | fraction(pred_orig == pred_perturbed) | Prediction-level agreement |

These require at least one perturbation in the run-spec. Computed pairwise between `original` and each named perturbation.

---

## Fairness Metrics

**Module**: `puma.metrics.fairness`

| Metric key | Formula | Notes |
|------------|---------|-------|
| `per_group.<g>.accuracy` | accuracy within group g | Requires group column in predictions |
| `global_metric` | overall accuracy | Across all groups |
| `worst_group` | group with lowest accuracy | — |
| `fairness_gap` | max(acc) − min(acc) | Across groups; 0 = perfectly fair |
| `disparities.<g>` | per_group[g] − global_metric | Positive = above average; negative = below |

---

## Efficiency Metrics

**Module**: `puma.metrics.efficiency`

| Metric key | Formula | Notes |
|------------|---------|-------|
| `latency.p50` | 50th percentile of latency_ms | Median latency |
| `latency.p95` | 95th percentile | Tail latency |
| `latency.p99` | 99th percentile | Worst-case latency |
| `latency.mean` | mean(latency_ms) | — |
| `latency.min` | min(latency_ms) | — |
| `latency.max` | max(latency_ms) | — |
| `throughput` | (n_instances / duration_s) × 60 | Instances per minute |

### Ollama timing breakdown

```python
parse_ollama_timings(raw_response_dict) → {
    "total_ms": total_duration_ns / 1e6,
    "load_ms":  load_duration_ns  / 1e6,
    "eval_ms":  eval_duration_ns  / 1e6,
    "tokens_per_sec": eval_count / (eval_duration_ns / 1e9),
}
```

---

## Stability Metrics

**Module**: `puma.metrics.stability`  
**Requires**: `repeat > 1` in run-spec

| Metric key | Formula | Notes |
|------------|---------|-------|
| `stability_score` | max(0, 1 − stddev/mean) | 1 = perfectly stable; 0 = high variance |
| `stability.mean` | mean of metric across repeats | — |
| `stability.stddev` | standard deviation | — |
| `stability.cv` | stddev / mean | Coefficient of variation |
| `stability.n_seeds` | number of repeats | — |

---

## Sustainability Metrics

**Module**: `puma.sustainability.codecarbon_wrapper`  
**Requires**: `sustainability.codecarbon: true` in run-spec

| Metric key | Units | Notes |
|------------|-------|-------|
| `co2_kg` | kg CO₂ equivalent | From CodeCarbon offline tracker |
| `kwh` | kWh | Energy consumed by the process |
| `duration_s` | seconds | Total tracked duration |
| `gco2_per_f1_point` | g CO₂ / Δ F1% | Quality-adjusted cost: `co2_g / (f1 × 100)` |
| `gco2_per_mae_unit` | g CO₂ / Δ MAE | For regression tasks |

CodeCarbon is always configured with `tracking_mode="process"` (no cloud reporting).

---

## How metrics are stored

After `Runner.run()` completes, all metrics are flattened and stored in the `metrics` table:

```
run_id              metric_name           value
smoke_triage_v1...  f1_macro              0.6218
smoke_triage_v1...  accuracy              0.6500
smoke_triage_v1...  latency.p95           432.1
smoke_triage_v1...  parse_failure_rate    0.0500
```

Nested metrics (e.g., `latency.p95`, `per_class.Critical.f1`) are stored with dot-separated keys. The `metrics_pivot()` function in `puma.dashboard.data` converts this to a run × metric DataFrame for the heatmap view.

---

## References

- Macro F1: Opitz & Burst (2019), *Macro F1 and Macro F1*
- ECE: Guo et al. (2017), *On Calibration of Modern Neural Networks* (ICML)
- NDCG: Järvelin & Kekäläinen (2002), *Cumulated gain-based evaluation of IR techniques* (TOIS)
- Brier Score: Brier (1950), *Verification of forecasts expressed in terms of probability*
- CodeCarbon: Lacoste et al. (2019), *Quantifying the Carbon Emissions of Machine Learning*
