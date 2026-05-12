# Changelog

All notable changes to PUMA are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

- ECE (Expected Calibration Error) end-to-end pipeline (Sprint 3,
  Gate D criterion 1):
  - `puma.metrics.calibration.expected_calibration_error` already
    existed in v2.0.0 (Guo et al. 2017 implementation, equal-width
    bins). 6 new canonical analytical tests added under
    `TestECECanonical` with strict 1e-6 tolerance against hand-
    computable cases (single-sample perfect, maximum miscalibration,
    one-bin known gap, two-bins known value, empty-bins handling,
    binary outcomes in isolated bins).
  - Runner now captures `result.logprobs` from the Ollama client when
    `spec.inference.logprobs=true`, computes per-prediction
    confidence via `class_confidence_from_logprobs` against the
    scenario's label-token map (triage_jira and prioritization_jira;
    regression scenario `estimation_tawos` correctly skipped), and
    persists both `predictions.logprobs_json` and `predictions.confidence`.
    `_compute_metrics` aggregates the per-prediction confidences into
    an `ece` metric persisted under `metrics.metric_name='ece'`.
  - New spec `specs/runs/baseline_triage_with_logprobs.yaml`
    (canonical baseline + `logprobs=true, top_logprobs=5`). Empirical
    smoke on qwen2.5:3b × N=200: F1=0.5831 (within tolerance),
    **ECE=0.3895**, n_with_confidence=200/200. This is the first
    empirically calibrated ECE measurement persisted by PUMA.
  - 3 new integration tests in `tests/integration/test_runner_ece.py`
    (ollama-gated): ECE persisted when logprobs=true, logprobs_json
    + confidence per prediction, ECE absent + columns NULL when
    logprobs=false (regression guard for the v2.0.0 default).
- Multi-seed baseline validation (Sprint 3):
  - Canonical baseline re-run with seeds {42, 123, 456} on
    qwen2.5:3b × triage_jira × N=200. **Zero variance in task metrics
    (F1=0.5831 in all three runs)** — the documented and expected
    result under temperature=0.0 (greedy decoding does not consume
    the RNG). Runtime jitter ~4 % across runs.
  - `docs/results/multi_seed_baseline.md`: full write-up including
    the methodological clarification that the canonical baseline's
    ±0.01 tolerance absorbs warm-vs-cold and version-drift sources,
    *not* seed variance.
- Wilcoxon signed-rank pairwise model comparison (Sprint 3):
  - `puma.metrics.statistical_tests.wilcoxon_signed_rank_models`:
    paired-correctness signed-rank test on two models' predictions
    over the same instance set. Returns `statistic`, `p_value`,
    `n_pairs` (non-tied), `mean_diff`. 4 TDD tests covering
    identical-model null, clearly-different-model alternative,
    required-fields contract, p_value range.
  - `scripts/wilcoxon_topmodels.py`: parameterised driver script
    (`--run-prefix`, `--scenarios`, `--top-k`) that ranks models in
    the DB and runs pairwise Wilcoxon comparisons.
  - `docs/results/wilcoxon_demo.md`: empirical demonstration on a
    mini-comparison (qwen2.5:1.5b vs gemma3:1b on triage_jira × N=50)
    showing that a 0.19-point F1 gap is NOT statistically significant
    at α=0.05 (p=0.1083, n_pairs=19/50). Documents why aggregate
    metric gaps and significance tests can disagree. The B.3 sweep
    predictions are not preserved at per-prediction granularity in
    the local DB at v2.1.0; re-running with persistence to enable
    Wilcoxon-at-scale is left as future work and the driver script
    needs no changes to absorb it.

### Changed

### Fixed

### Removed

## [2.1.0] — 2026-05-10

### Added

- `puma validate-baseline` CLI command — runs the canonical baseline
  spec (`specs/runs/baseline_triage.yaml`) and exits 0 when the resulting
  `f1_macro` is within `--tolerance` of `--expected-f1`, non-zero
  otherwise. Useful as a CI reproducibility guard before tagging a
  release. TDD: 3 unit tests with monkeypatched runner. Closes debt D1.
- Alembic migration `0002_server_default_timestamps` — adds
  `server_default=func.now()` (CURRENT_TIMESTAMP under SQLite) to the
  ORM-managed timestamp columns: `runs.started_at`, `metrics.computed_at`,
  `emissions.recorded_at`. Ensures DB-side defaults for concurrent
  inserts and raw-SQL paths, complementing the existing Python-side
  `default=_now`. Implemented via `op.batch_alter_table(recreate="always")`
  because SQLite does not support direct `ALTER COLUMN`. TDD: 1 new
  integration test (`test_timestamps_have_server_default`); existing
  `test_initial_migration_has_no_pending_changes` continues to pass with
  `compare_server_default=True`. Closes debt D6.
- `puma.scenarios._reasoning.strip_reasoning` helper — strips
  `<think>...</think>` reasoning blocks (closed, unclosed, and stray-tag
  variants) before scenario parsers run. Fixes false-positive matches
  inside reasoning text for models like `deepseek-r1` (e.g. the literal
  word "critical" appearing inside chain-of-thought). Wired into the
  three scenario parsers (`triage_jira.parse_prediction`,
  `estimation_tawos.parse_story_points`, `prioritization_jira.parse_response`).
  TDD: 8 unit tests covering the helper and all three scenarios.
  Closes debt D17.
- `puma.runtime.client.client_for_model` factory — looks the model up in
  the catalog and threads `ModelEntry.timeout_s` into `OllamaClient`.
  Detected mid-sprint while smoke-testing the D17 fix: a 20-instance
  `deepseek-r1:7b` run on triage_jira produced 3 consecutive
  `500 | 2m0s` Ollama responses because the orchestrator instantiated
  `OllamaClient(timeout_s=120.0)` regardless of the per-model value
  declared in `config/models_catalog.yaml`. The factory now resolves
  the catalog entry per model; the runner builds one client per model
  inside the inference loop. Unknown tags fall back to 120 s.
  `config/models_catalog.yaml`: `gemma3:12b` timeout bumped 180→1800s
  (B.3 evidence: 631 s / 590 s on triage / estimation respectively);
  `deepseek-r1:7b` timeout was already 300 s (no bump needed).
  TDD: 5 unit tests in `tests/unit/test_client_timeout_propagation.py`.
  Closes debt D21 (folded into this sprint as task S1.5.bis).
  End-to-end smoke (post D17 + D21): a 20-instance `deepseek-r1:7b` run
  on `triage_jira` with `contextual-anchoring` finished cleanly in
  ~41 minutes; `parse_failure_rate` dropped from 0.80 (pre-Sprint
  observation) to 0.15; F1-macro 0.6042; zero timeout errors at the
  Ollama layer (per-request latencies 1m18s–3m2s, all under the new
  300 s cap). Confirms the parser fix and timeout propagation work
  together for reasoning models.
- `docs/CONTRIBUTING.md` — host-only pre-commit setup instructions for
  cross-container development workflow (pipx + manual run; CI as safety
  net). Closes debt D10.
- `puma.preflight.catalog` module exposing `ModelEntry`,
  `load_catalog()`, `models_for_profile(profile_name)`, and
  `get_model_by_tag(tag)` as the single-source-of-truth API for model
  metadata.
- `docs/HARDWARE.md`: hardware specification of the reference development
  machine (MSI GS66 Stealth 10SE: i7-10750H, 32 GB DDR4 2667 MHz, RTX
  2060 Mobile 6 GB GDDR6, NVMe 1 TB) with sections on profile detection,
  sustained-load thermal behavior, memory bandwidth, VRAM constraints,
  CodeCarbon accuracy on this hardware, and reproducibility scope.
  Includes empirical observations from Phase B sweep (mistral:7b 10–18×
  duration variance) and CPU-offload behavior of large models.
- `docs/known_debt.md`: consolidated tracker of methodological findings
  detected during v2.0.0 release validation (8 closed) and open
  technical debt classified by severity. A "Resolved technical debt"
  section was added in Sprint 2 with full diagnostic write-ups for
  D15 (CodeCarbon measurement-and-infrastructure coupling) and D18
  (gemma4 family Ollama-detokenizer breakage under CPU offload).
- `docs/results/phase_b_analysis.md`: comparative analysis of the
  Phase B sweep (9 models × 3 scenarios × 100 instances on `gpu-entry`
  profile, 27 runs, 6 h 41 m wall clock, 11.75 g CO₂). Reports
  per-scenario performance tables, cost-effectiveness ranking
  (quality per g CO₂), sustainability efficiency aggregate, the
  "60.5 % wasted compute" finding for `gemma4:e2b`, intra-family
  non-monotonicity evidence, and per-task practical recommendations.
- `scripts/generate_phase_b_plots.py`: reproducible figure generation
  from `data/puma.db`; produces three PNGs in `docs/results/figures/`
  embedded in the analysis document (performance bar chart per
  scenario, quality-vs-CO₂ Pareto scatter, duration variability
  boxplot).
- `docs/results/figures/`: three PNGs supporting the Phase B analysis.
- `.githooks/commit-msg`: client-side hook that strips
  `Co-Authored-By:` trailers from commit messages, preventing
  accumulation of AI-tool attribution artifacts that the project's
  git identity convention does not carry. Repo enables it via
  `git config core.hooksPath .githooks`; setup documented in
  `docs/CONTRIBUTING.md`.
- `tests/integration/test_codecarbon_gpu_detection.py`: 3 integration
  tests gated on the `requires_gpu` marker — pynvml init inside the
  runner container, `EmissionsTracker._total_gpu_energy > 0` after
  `stop()`, and a real `Runner(dry_run=True)` end-to-end producing an
  emissions row with `gpu_energy > 0`. Tests automatically skip on
  hosts without an NVIDIA GPU (e.g. CI runners).
- `requires_gpu` pytest marker registered in `pytest.ini` and
  `pyproject.toml` (`[tool.pytest.ini_options]`).

### Changed

- `scripts/download_datasets.py` renamed to `scripts/prepare_datasets.py`
  to reflect actual behavior (it processes a local TAWOS SQL dump, does
  not download). References updated across `src/puma/datasets/tawos.py`,
  `data/README.md`, `docs/user_guide.md`, `docs/troubleshooting.md`, and
  the future Phase D directives in `docs/internal/claude-code-prompts/PROMPT-D-tecnico.md`.
  Historical mentions retained in `docs/known_debt.md` (F4) and
  `docs/baseline_inventory.md` (pre-Phase-0 snapshot). Closes debt D13.
- `pyproject.toml` version bumped from `2.0.0-dev` to `2.1.0-dev` —
  development now targets the next minor release. Closes debt D18-cleanup.
- CodeCarbon `tracking_mode` changed from `"process"` to `"machine"` in
  `src/puma/orchestrator/runner.py` and
  `src/puma/sustainability/codecarbon_wrapper.py`. Rationale: PUMA's
  multi-container architecture splits orchestration (`puma_runner`) from
  inference (`puma_ollama`); `tracking_mode="process"` measures only the
  orchestrator's own energy, missing the GPU work that happens in the
  inference container. `tracking_mode="machine"` captures whole-machine
  consumption, which on the documented sweep convention (AC power, idle
  host, no other GPU consumers) attributes correctly to PUMA. Pre-D15
  emissions rows (including the 27 from the B.3 sweep) report only
  CPU+RAM energy and underreport total consumption; post-D15 rows
  include GPU. Closes debt D15.
- `docker-compose.yml`: `puma_runner` now declares the same CDI GPU
  passthrough block as `puma_ollama` (`driver: cdi`,
  `device_ids: [nvidia.com/gpu=all]`), allowing pynvml / nvidia-smi
  access from within the runner container so CodeCarbon can enumerate
  GPU devices. Coupled with the `tracking_mode` change above to close
  debt D15.
- `gemma4` family (`gemma4:e2b`, `gemma4:e4b`, `gemma4:26b-a4b`)
  removed from `gpu-entry` `profiles_compatible` in
  `config/models_catalog.yaml`. Empirical evidence from the B.3 sweep
  (parse_failure_rate 0.98–1.00 across 3 scenarios for `gemma4:e2b`,
  60.5 % of total sweep CO₂ consumed for zero usable predictions)
  plus targeted diagnostic in S2.2 (`raw_response=''` despite
  non-zero `eval_count`; simple prompts decode correctly while
  structured PUMA prompts produce empty responses) confirmed the
  fault lies at Ollama's detokenizer under CPU offload, not at the
  PUMA scenario parser. No MoE-aware parser would help since there
  is no content returned to parse. The three gemma4 tags remain in
  the catalog and remain available for `gpu-mid` / `gpu-high`
  profiles where the model fits in VRAM. New unit test
  `test_gemma4_family_excluded_from_gpu_entry` in
  `tests/unit/test_catalog_metadata.py` guards the exclusion. Full
  diagnostic preserved in `docs/known_debt.md` (Resolved technical
  debt section, D18 entry). Closes debt D18.
- Coverage target adjusted from 70 % (Gate A, v2.0.0 scope) to 57 %
  for the v2.1.0 release scope. Rationale: the gap is concentrated in
  UI / reporting modules (`puma.dashboard.*` 0 %,
  `puma.reporting.report` 0 %, `puma.orchestrator.compare` 0 %) which
  are scheduled for refactoring in the planned Phase C ("Dashboard
  profesional") milestone. Critical pipeline modules (`puma.metrics`,
  `puma.runtime`, `puma.storage`, `puma.preflight`, `puma.scenarios`)
  remain individually well-covered and have been empirically
  validated through the B.3 sweep (27 successful runs across
  9 models × 3 scenarios) and Sprints 1 + 2 TDD tests
  (16 new tests covering catalog SoT, codecarbon wiring, reasoning
  parser, timeout propagation, GPU detection, baseline validation,
  timestamps, and gemma4 exclusion).

### Fixed

- CodeCarbon integration: v2.0.0 declared CodeCarbon as a first-class
  sustainability metric, but the orchestrator never invoked the
  `EmissionsTracker`. The infrastructure (`puma.sustainability` module,
  `Emission` ORM, `emissions` table) was complete but the runner never
  consulted the `spec.sustainability.codecarbon` flag. Now wired: runs
  with the flag enabled persist an emissions row per run with `kwh`,
  `co2_kg`, `duration_s`, and `cpu_energy` / `gpu_energy` / `ram_energy`
  breakdowns. Lazy import of `codecarbon` keeps it out of the hot path
  when tracking is disabled. Closes empirical finding #6 (F6) from
  v2.0.0 release validation.
- Model catalog size: corrected `gguf_size_gb` for `gemma4:e2b` from
  2.0 GB (effective parameters) to 7.2 GB (actual GGUF size on disk;
  includes all MoE experts, not just active ones). The previous value
  caused `check_provisioning` to underestimate disk requirements by
  ~5.2 GB per profile that includes this model. Added explanatory notes
  to `gemma4:e4b` and `gemma4:26b-a4b` indicating their `gguf_size_gb`
  values are unverified estimates pending local pull. Closes F8.
- Catalog / profiles SoT drift: 17 `(profile, tag)` drift pairs had
  silently accumulated between `config/profiles.yaml.models[]` and
  `config/models_catalog.yaml.profiles_compatible[]`. The new
  `puma.preflight.catalog.models_for_profile()` derives the dispatch
  list from a single source. Closes F7.
- Closes 9 of 15 known technical debt items (D1, D6, D10, D13, D15,
  D17, D18, D18-cleanup, D21). See `docs/known_debt.md` for individual
  entries; Sprint 1 closures remain inline with strikethrough
  notation in the open-debt tables, and the involved Sprint 2
  resolutions (D15, D18) are written up in detail in the
  "Resolved technical debt" section.

### Removed

- `Profile.models` field from `puma.preflight.profile.Profile` and
  the `models[]` list from `config/profiles.yaml`. The catalog
  (`config/models_catalog.yaml.profiles_compatible[]`) is now the
  single source of truth for `(profile → models)` dispatch; callers
  in `puma.preflight.provisioning` and `puma.preflight.report` were
  updated to consume the new
  `puma.preflight.catalog.models_for_profile()` API.

### Highlights

- **Multi-model evaluation sweep** completed (9 models × 3 PMO
  scenarios × 100 instances; 2,700 inferences; ~67.5 Wh / 11.75 g
  CO₂ total compute budget). Best performers vary by task; small
  models are competitive with larger ones in several PMO scenarios.
  Full analysis in `docs/results/phase_b_analysis.md`; reproducible
  plots via `scripts/generate_phase_b_plots.py`.
- **CodeCarbon GPU energy tracking** now functional inside the
  `puma_runner` container (was systematically zero in v2.0.0). Fix
  required two coupled changes — CDI passthrough in
  `docker-compose.yml` plus `tracking_mode="machine"` in the
  orchestrator and the codecarbon wrapper. First non-zero
  `gpu_energy` row recorded in this release (D15).
- **Catalog single source of truth**: `profiles_compatible[]` in the
  catalog drives both provisioning and dispatch; the duplicated
  `models[]` field in `profiles.yaml` is gone; 17 drift pairs
  resolved (F7).
- **gemma4 family exclusion from gpu-entry** documented after
  empirical diagnostic confirmed the failure mode is at Ollama's
  detokenizer under CPU offload, not at the PUMA scenario parser
  (D18). Models remain available for `gpu-mid` / `gpu-high`.
- **23 technical debt items tracked**; 9 resolved in this release
  (60 %). Detailed evidence and diagnostic chains preserved for
  academic traceability in `docs/known_debt.md`.
- **Hardware specification** of the reference development machine
  documented in `docs/HARDWARE.md` with reproducibility scope
  (cold-vs-warm baseline drift, thermal observations, VRAM
  constraints).
- **Commit-message hygiene hook** (`.githooks/commit-msg`) prevents
  accumulation of co-authoring trailers from development tooling.

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
