# Changelog

All notable changes to PUMA are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [2.0.0] — 2026-05-10

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

**Release validation phase (cleanup, baseline, infrastructure hardening)**
- Three canonical run specs at `specs/runs/`: `baseline_triage.yaml` (canonical reference, contextual-anchoring × 200 instances), `smoke_triage_zeroshot.yaml` (auxiliary, F1=0.3898), `smoke_triage_zeroshot_cot.yaml` (auxiliary, F1=0.4659)
- Alembic-managed schema migrations infrastructure (`alembic.ini`, `alembic/env.py`, `0001_initial_schema`); SQLAlchemy `MetaData` configured with naming convention for explicit constraint names
- Pre-commit hooks (`.pre-commit-config.yaml`): ruff, ruff-format, isort, basic hygiene (trailing-whitespace, end-of-file-fixer, check-yaml/toml/merge-conflict/added-large-files, debug-statements)
- CI workflows extended to trigger on push/PR to `develop` (was `main` only)
- 10 integration tests for Alembic migrations covering 10 acceptance criteria (`tests/integration/test_alembic_migrations.py`)
- Specification document `specs/storage-migrations.spec.md` (v0.2.0 published) documenting the Alembic integration with decisions S1 and I3

### Changed
- `start_puma.sh` updated to use `puma_runner` (was `puma_evaluator`)
- `detect.py` catches `NotADirectoryError` and `OSError` in subprocess helpers
- Legacy `src/*.py` files excluded from ruff lint scope
- `pytest.ini` updated with `smoke` mark
- `init_db` delegates schema creation to Alembic migrations rather than direct `Base.metadata.create_all` (decision I3, see `specs/storage-migrations.spec.md`); explicit error if `alembic.ini` is missing (no silent fallback)
- `puma db` CLI: refactored from single argument-dispatch (`db <action>`) to sub-Typer with explicit `migrate`, `downgrade`, `history`, `status` subcommands (decision S1: `status` preserved as subcommand)
- Datasets: small processed CSVs (`jira_balanced_200.csv`, `tawos_clean.csv`, `tawos_raw.csv`, ~12 MB total) tracked in repo; SQL dumps and large artifacts remain gitignored
- Repository hygiene: removed build artifacts and legacy prototype code from versioning (~31k lines deleted): `__pycache__/`, `*.pyc`, `agents/`, `src/{cleanup,data_prep,evaluate_*,history,rag_index,statistical_analysis}.py`, `reports/`
- Internal operational documents (`CLAUDE_CODE_INSTRUCTIONS.md`, audit reports) relocated to `docs/internal/` (gitignored)
- `README.md` updated with positive independence statement asserting that PUMA is a self-contained benchmarking framework with evaluation methodology developed independently

### Fixed
- `UNIQUE constraint` on `instances` table when re-inserting across perturbation variants
- `test_perfect_calibration` ECE threshold corrected to use truly calibrated data
- Release workflow: added `permissions: contents: write` so `softprops/action-gh-release@v2` can publish releases (pre-existing bug since v0.10.0-rc.1)
- Ruff version alignment: pinned to exact same version (`==0.15.12`) in `.pre-commit-config.yaml`, `requirements-dev.txt`, and `pyproject.toml` to prevent rule-default drift between local pre-commit and CI (manifested as 74 PT023 violations)
- Dataset availability in CI: tracked CSVs make `actions/checkout` sufficient; no per-job regeneration required

### Empirically Characterized Reference Baseline

Configuration: `qwen2.5:3b`, `contextual-anchoring` strategy, `seed=42`, `temperature=0.0`, 200 balanced instances on `triage_jira`.

- F1-macro: 0.5867 ± 0.01 (reproducible across N=5 reruns)
- Reproducibility: bit-exact in warm state; cold-vs-warm drift ≤0.006 within stated tolerance
- Carbon footprint: ~3 gCO₂eq per run (CodeCarbon)

### Empirical Findings During Release Validation

The following methodological observations were detected during this release's validation phase and are documented as part of the project's methodological rigor:

- The reference F1 = 0.5867 was empirically characterized to correspond to the `contextual-anchoring` strategy (zero-shot extended with PM domain context), not pure zero-shot which yields F1 = 0.3898
- Tooling-CI version drift: pre-commit pinned to ruff v0.4.4 while CI installed latest by default, causing rule-default divergence (PT023, SIM300). Mitigated via exact pinning on both sides
- Dataset regeneration scope mismatch: `scripts/download_datasets.py` processes a local SQL dump rather than fetching, so the "regenerable in CI" promise was only partial. Mitigated by re-tracking processed CSVs
- Release workflow `GITHUB_TOKEN` permission gap (default read-only since GitHub's 2024 security changes) prevented automated GitHub Release creation. Fixed in this release

### Known Limitations and Accepted Technical Debt

The following items are tracked for future releases:

- `--validate-baseline` CLI flag declared in spec but not yet implemented
- `adaptation.cot` field declared in `runspec.py` but inert (CoT is activated via the separate `zero-shot-cot` strategy, not via the field)
- Cold-vs-warm reproducibility needs formal documentation in user-facing docs
- Investigation of Ollama/CUDA deterministic-mode flags pending (`CUBLAS_WORKSPACE_CONFIG`, etc.)
- 8 ruff codes suppressed in tests pending future refactor (B011, PT011, RUF012, SIM117, SIM118, PT018, UP038, RUF002)
- mypy not yet integrated as pre-commit hook (gradual adoption); strict mode is preserved in `pyproject.toml` for `puma.metrics`, `puma.runtime`, `puma.preflight`
- Pre-commit not installed as local git hook (cross-container workflow incompatibility; documented for developers working host-only)
- `scripts/download_datasets.py` is mis-named (processes local SQL zip rather than downloads); rename pending
- TAWOS dataset regeneration requires manual upload of source SQL dump; automated fetch from a stable mirror pending
- Git history prior to commit `1abd831` retains references to internal operational documents (decided-no-action: history rewrite is disproportionate for non-artifact documents)
- `version = "2.0.0-dev"` in `pyproject.toml` causes wheel to be emitted as `puma-2.0.0.dev0-py3-none-any.whl`; release versioning to be standardized before the next release
- `fairness` metric family is scaffolding only in v2.0.0; full implementation (including bias perturbations such as gender_swap) planned for a future release

---

## [1.0.0] — 2025 (pre-restructuring)

Initial evaluation scripts: `evaluate_triage.py`, `evaluate_estimation.py`, `agents/orchestrator.py`.
Single-file, non-reproducible, not packaged.

[Unreleased]: https://github.com/pumacp/puma/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/pumacp/puma/releases/tag/v2.0.0
