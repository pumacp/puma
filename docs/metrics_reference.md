# Metrics Reference

## Classification (triage_jira, prioritization_jira)

| Metric | Formula | Notes |
|--------|---------|-------|
| `f1_macro` | mean of per-class F1 | Equal weight per class; robust to imbalance |
| `f1_weighted` | weighted mean of per-class F1 | Weight = class support |
| `accuracy` | correct / total | Overall fraction correct |
| `per_class.<label>.precision` | TP / (TP + FP) | Per-label |
| `per_class.<label>.recall` | TP / (TP + FN) | Per-label |
| `per_class.<label>.f1` | 2 · P · R / (P + R) | Per-label |
| `parse_failure_rate` | unparsed / total | Fraction where parse_response returned None |

## Regression (estimation_tawos)

| Metric | Formula | Notes |
|--------|---------|-------|
| `mae` | mean \|y - ŷ\| | Mean Absolute Error; story-point scale |
| `mdae` | median \|y - ŷ\| | Robust to outliers |
| `rmse` | √(mean (y - ŷ)²) | Penalises large errors |
| `mae_by_bin` | MAE grouped by SP range | Ranges: 1–3, 5–8, 13–21, 34+ |

## Calibration

| Metric | Formula | Notes |
|--------|---------|-------|
| `ece` | Σ_b (n_b/N) \|acc_b − conf_b\| | Expected Calibration Error; equal-width bins |
| `mce` | max_b \|acc_b − conf_b\| | Maximum Calibration Error |
| `brier_score` | mean (conf − correct)² | Proper scoring rule |

## Efficiency

| Metric | Definition |
|--------|-----------|
| `latency.p50` | Median inference latency (ms) |
| `latency.p95` | 95th-percentile latency (ms) |
| `latency.p99` | 99th-percentile latency (ms) |
| `latency.mean` | Mean latency (ms) |
| `throughput` | Instances per minute |

## Robustness

| Metric | Formula |
|--------|---------|
| `robustness_score` | max(0, 1 − \|metric_orig − metric_perturbed\|) |
| `consistency_rate` | fraction(preds_orig == preds_perturbed) |

## Sustainability

| Metric | Units |
|--------|-------|
| `co2_kg` | kg CO₂ equivalent |
| `kwh` | kWh consumed |
| `gco2_per_f1_point` | g CO₂ / Δ F1 point |

## References

- Macro F1: Opitz & Burst (2019), *Macro F1 and Macro F1*
- ECE: Guo et al. (2017), *On Calibration of Modern Neural Networks*
- NDCG: Järvelin & Kekäläinen (2002)
- CodeCarbon: Lacoste et al. (2019)
