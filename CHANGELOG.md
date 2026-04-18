# Changelog

All notable changes to PUMA are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions follow [Semantic Versioning](https://semver.org/).

---

## [2.0.0] — 2026-04-18

### Added

**Phase 0 — Repo restructuring**
- `src/puma/` package with `pyproject.toml`, editable install via `PYTHONPATH=/app/src`
- Docker-first development: `Dockerfile`, `docker-compose.yml` (`puma_ollama`, `puma_runner`, `puma_dashboard`)
- `Makefile` targets: `build`, `lint`, `test`, `smoke`

**Phase 1 — Preflight**
- `puma.preflight.detect`: hardware capability detection (CPU, RAM, GPU via nvidia-smi/rocm-smi/metal)
- `puma.preflight.profile`: profile selection (`cpu-lite` → `gpu-high`) with override support
- `puma.preflight.provisioning`: issue checking (disk, Ollama version, VRAM)
- `puma preflight` CLI command

**Phase 2 — Ollama client, cache, datasets, CLI**
- `puma.runtime.client.OllamaClient`: async + sync inference, retry, logprob parsing
- `puma.runtime.cache.InferenceCache`: SQLite-backed prompt hash → response deduplication
- `puma.datasets`: Jira and TAWOS loaders + integrity verification
- `puma models`, `puma datasets`, `puma cache` CLI commands

**Phase 3 — Scenarios, strategies, perturbations**
- 3 benchmark scenarios: `triage_jira`, `estimation_tawos`, `prioritization_jira`
- 11 prompting strategies: zero-shot, zero-shot-cot, one-shot, few-shot-k, cot-few-shot, rcoif, contextual-anchoring, self-consistency, egi
- Jinja2 prompt templates for all 3 scenarios × 7 template files each
- `puma.perturbations.text`: typos, case_change, truncate, tech_noise, reorder_fields
- `puma.adaptation.examples`: stratified deterministic few-shot example selection

**Phase 4 — Metrics, calibration, sustainability**
- `puma.metrics.accuracy`: classification_metrics, regression_metrics, ranking_metrics
- `puma.metrics.calibration`: ECE, MCE, Brier score, class_confidence_from_logprobs, reliability_diagram
- `puma.metrics.robustness`: robustness_score, consistency_rate
- `puma.metrics.fairness`: fairness_report (per-group metrics + fairness gap)
- `puma.metrics.efficiency`: latency percentiles, throughput, parse_ollama_timings
- `puma.metrics.stability`: stability_score, stability_report
- `puma.sustainability.codecarbon_wrapper`: @track_emissions decorator, emissions_summary, gCO₂/F1

**Phase 5 — Orchestrator, storage, run-specs**
- `puma.orchestrator.runspec.RunSpec`: Pydantic v2 with cross-validators, spec_hash(), from_yaml()
- `puma.storage`: SQLAlchemy 2.0 ORM (Run, Instance, Prediction, Metric, Emission, ProfileSnapshot)
- `puma.orchestrator.runner.Runner`: full end-to-end pipeline with dry_run support, Rich progress
- `puma.orchestrator.compare.compare_runs`: markdown table + diffs across runs
- `puma run`, `puma compare`, `puma db` CLI commands

**Phase 6 — Streamlit dashboard**
- `puma.dashboard.data`: read-only SQLite queries (load_runs, load_metrics, load_predictions, …)
- `puma.dashboard.components`: metric_card, comparison_table, reliability_plot, pareto_scatter, fig_to_bytes
- `puma.dashboard.app`: 7 views — Overview, Model Comparison (heatmap), Reliability, Robustness, Fairness, Sustainability Frontier, Instance Drill-down
- Global sidebar filters: runs, date range, models
- `puma dashboard` CLI command (launches Streamlit on :8501)

**Phase 7 — Reports, documentation, CI**
- `puma.reporting.report.generate_report()`: Markdown report with executive summary, metrics table, per-model breakdown, perturbations, sustainability, latency; optional PDF via Pandoc
- `puma report` CLI command
- `docs/`: architecture, metrics reference, scenarios reference, adding models, adding scenarios, troubleshooting
- `CONTRIBUTING.md`: code conventions, commit format, PR process
- `README.md`: badges, 3-command quickstart, full CLI reference
- GitHub Actions: `lint-and-test.yml`, `smoke.yml`, `release.yml`
- `start_puma.sh`: one-shot provisioning script for clean machines

### Changed
- `start_puma.sh` updated to use `puma_runner` (was `puma_evaluator`)
- `detect.py` catches `NotADirectoryError` and `OSError` in subprocess helpers
- Legacy `src/*.py` files excluded from ruff lint scope
- `pytest.ini` updated with `smoke` mark

### Fixed
- `UNIQUE constraint` on `instances` table when re-inserting across perturbation variants
- `test_perfect_calibration` ECE threshold corrected to use truly calibrated data

---

## [1.0.0] — 2025 (pre-restructuring)

Initial evaluation scripts: `evaluate_triage.py`, `evaluate_estimation.py`, `agents/orchestrator.py`.  
Single-file, non-reproducible, not packaged.
