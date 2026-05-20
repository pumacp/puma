# Metrics and Sustainability

PUMA computes seven metric families for every run and pairs them with a
sustainability footprint. The combination is what makes PUMA useful for
research and engineering decisions: pure quality numbers tell only half the
story when energy and latency vary by an order of magnitude across
configurations.

## The seven metric families

1. **Accuracy** — for classification scenarios, F1-macro, precision/recall
   per class, and a full confusion matrix. For regression scenarios, MAE,
   MdAE, and R². Computed from the predictions table once a run finishes.
2. **Calibration** — Expected Calibration Error (ECE) over the model's
   confidence values. Only meaningful when the model exposes logprobs
   (most Ollama models do).
3. **Efficiency** — latency percentiles (p50, p90, p99), tokens generated per
   second, and the total wall-clock time per run.
4. **Stability** — how much the metrics shift across N repeated runs with
   different seeds. Reported as the coefficient of variation.
5. **Robustness** — accuracy under controlled input perturbations: typo
   injection, paraphrasing, and unicode confusable swaps.
6. **Fairness** — disparity across input subgroups (e.g., by project, by
   issue length). Reported as max-min gap per metric.
7. **Sustainability** — gCO₂eq per run, energy kWh, country-grid emissions
   intensity, all sourced via [CodeCarbon](https://codecarbon.io).

## Reading the dashboard

The Streamlit dashboard (run `docker compose up -d puma_dashboard`, then open
`http://localhost:8501`) has eight views:

- **Overview** — a leaderboard across all logged runs.
- **Accuracy** — drill-down into per-class metrics and confusion matrices.
- **Calibration** — reliability diagrams and ECE timelines.
- **Efficiency** — latency distributions and tokens/second by model.
- **Robustness** — accuracy curves under each perturbation.
- **Fairness** — subgroup heatmaps.
- **Sustainability** — gCO₂eq, energy kWh, and energy-per-correct-prediction.
- **🤝 Community** — the entry point for publishing your results to
  [PUMA Community](https://github.com/pumacp/puma-community).

## Carbon footprint

CodeCarbon tracks energy at the process level and converts to gCO₂eq using
the configured country grid. Typical reference values:

- A 10-instance `triage_jira` run on `qwen2.5:3b` on `cpu-standard`:
  ≈ 0.3 gCO₂eq, ≈ 90 s wall-clock.
- The same 10-instance run on `qwen2.5:7b` on `gpu-entry`: ≈ 0.05 gCO₂eq,
  ≈ 25 s.
- A full 200-instance sweep across six models on `gpu-mid`: ≈ 15 gCO₂eq.

Comparing models without comparing footprints overlooks an entire dimension
of the engineering decision; PUMA makes both visible side by side.
