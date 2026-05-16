# Changelog

All notable changes to PUMA are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [2.6.0] — 2026-05-16

### Added

Sprint 9 (Apple Silicon M3/M4/M5 detection + native runtime mode;
empirical validation pending until Mac hardware joins the validation
set):

- **9 Apple Silicon profile identifiers** in `config/profiles.yaml`:
  `apple-silicon-m3`, `-m3-pro`, `-m3-max`, `-m4`, `-m4-pro`,
  `-m4-max`, `-m5`, `-m5-pro`, `-m5-max`, `-m5-ultra`. All declare
  `empirical_validation: pending`. The requirements schema is
  extended additively (non-breaking) with `apple_silicon_required`,
  `chip_brand_match`, and `min_unified_memory_gb` fields; the
  existing 5 NVIDIA/CPU profiles ignore them at load time.
- **New module `src/puma/preflight/apple_silicon.py`**: platform-
  isolated detection via `sysctl machdep.cpu.brand_string` and
  `sysctl hw.memsize`. Public entry points
  (`is_apple_silicon`, `get_chip_brand`, `get_unified_memory_gb`,
  `detect_apple_silicon_profile`, `get_apple_silicon_info`) return
  `None` on non-macOS hosts without invoking subprocess — safe to
  import everywhere; fully mockable on Linux CI (P9).
  `CHIP_BRAND_TO_PROFILE` maps the 10 catalogued chip brands to
  profile identifiers; unrecognised brands return `None` so dispatch
  falls through (forward-compat for future M-series).
- **SystemCapabilities + Profile dispatch extended** for Apple
  Silicon. `SystemCapabilities` gains optional `chip_brand` and
  `unified_memory_gb` fields populated from sysctl in
  `detect_capabilities`. `Profile` gains optional
  `apple_silicon_required`, `chip_brand_match`,
  `min_unified_memory_gb` (defaults preserve v2.5.0 behaviour).
  `select_profile()` runs a new `_match_apple_silicon_profile`
  branch BEFORE the existing GPU/CPU dispatch — on Linux+NVIDIA
  hosts where `caps.chip_brand is None`, the branch is a no-op and
  the dispatch is byte-identical to v2.5.0.
- **`start_puma.sh --native` flag** for macOS Mode B (Ollama with
  Metal, no Docker). Refuses to run on non-Darwin with a clear
  error; warns on Intel Mac; verifies `ollama` in PATH and starts
  `ollama serve` in background if not already running; creates
  `.venv` and installs `puma` in editable mode if absent; exports
  `PUMA_OLLAMA_HOST` and `PUMA_NATIVE_MODE` env vars; prints
  next-step commands. The Docker-mode path on Linux is unchanged.
- **New script `stop_puma_native.sh`** — companion teardown that
  SIGTERMs the native `ollama serve` process (escalates to SIGKILL
  after 2s if needed) and prints the venv-deactivate hint. No-op on
  Linux.
- **`get_tracking_mode_and_warnings()` in
  `puma.sustainability.codecarbon_wrapper`**: platform-aware
  CodeCarbon `tracking_mode` resolver. Returns `("machine", [])` on
  Linux — byte-identical to v2.5.0 behaviour and the D15 fix that
  PUMA's split-container architecture relies upon. On macOS Apple
  Silicon, probes `powermetrics` availability without `sudo`;
  returns `("machine", [])` when configured, or
  `("process", [<single-warning>])` on the default macOS state.
  The decorator `track_emissions` and `Runner.run` both now thread
  this helper.
- **`docs/CROSS_ARCH_REPRODUCIBILITY.md`**: documents the open
  empirical question of bit-exact F1/MAE/logprobs between x86_64
  Linux (validation environment) and arm64 macOS (Mode B).
  Theoretical expectations (F1/MAE bit-exact under Q4_K_M integer
  quantisation; logprobs differ by FP rounding) plus H0/H1/H2/H3
  hypotheses and a 6-step testing protocol for when Mac hardware
  becomes available.
- **`docs/MACOS_NOTES.md` extended** with "Energy tracking on macOS
  (Mode B / native)" section: documents the three behaviours
  (passwordless powermetrics → machine; default → process with
  warning; `--no-emissions` → off), with a `NOPASSWD` sudoers
  snippet for advanced users and an explanation of why
  `tracking_mode="machine"` is needed (D15 cross-container reasoning
  applies in reverse to native Mode B).
- **Cross-links** from `docs/HARDWARE.md` (Apple Silicon row of the
  gpu-entry tolerance table) and `docs/CATALOG_HISTORY.md` (new
  `catalog_version 2.6.0` section) to
  `docs/CROSS_ARCH_REPRODUCIBILITY.md`.
- **48 new tests** (354 → 402 passing):
  `tests/unit/test_apple_silicon.py` (28 tests covering every
  public entry point with mocks for Darwin/arm64 gate, sysctl
  success + 3 failure modes, parametrised mapping for all 10 chip
  brands, forward-compat for unmapped chips, `get_apple_silicon_info`
  dict shape, `CHIP_BRAND_TO_PROFILE` consistency);
  `tests/unit/test_codecarbon_macos.py` (7 tests for the
  tracking_mode helper and powermetrics probe — Linux short-circuit,
  macOS sudo present/absent, probe failure modes);
  `tests/unit/test_catalog_metadata.py` (+5: VALID_PROFILES
  inclusion, profiles.yaml definitions for all 9 apple-silicon-*,
  chip_brand_match uniqueness, gemma4 exclusion from every
  apple-silicon-*, qwen2.5:3b anchor on apple-silicon-m4-pro);
  `tests/unit/test_preflight_profile.py` (+7: auto-dispatch for
  M4/M4 Pro/M5 Max, fall-through cases for insufficient unified
  memory, unmapped chips, non-Apple chip brands; +1 manual override
  test for apple-silicon-m4).

### Changed

- `catalog_version` bumped: **2.5.0 → 2.6.0**.
- `tests/unit/test_catalog_metadata.py::VALID_PROFILES`: extended
  with the 9 apple-silicon-* identifiers. The existing invariant
  test `test_model_metadata_is_internally_consistent` is unchanged
  in semantics; it now accepts the new identifiers when they appear
  in any model's `profiles_compatible[]`.
- `config/profiles.yaml`: schema extended additively with
  `apple_silicon_required`, `chip_brand_match`,
  `min_unified_memory_gb` fields. The existing 5 NVIDIA/CPU
  profiles leave them at their defaults and are unaffected.
- `config/models_catalog.yaml`: conservative `profiles_compatible[]`
  additions per a memory-headroom rule (≈ 2× GGUF + OS overhead):
  `qwen2.5:1.5b` and `gemma3:1b` → compatible with all 10
  apple-silicon-*; `qwen2.5:3b` and `gemma3:4b` → skip m3 base
  (8 GB tight); 7B–8B models (`qwen2.5:7b`, `mistral:7b`,
  `llama3.1:8b`, `deepseek-r1:7b`) → Pro/Max/Ultra only;
  14B models (`qwen2.5:14b`, `deepseek-r1:14b`) → Max/Ultra only;
  `gemma3:12b` → ≥ 24 GB unified memory (Pro/Max/Ultra of m3-max,
  m4-pro+, m5-pro+); `gemma3:27b` → Max/Ultra only.
- `src/puma/orchestrator/runner.py`: the CodeCarbon initialisation
  block now calls `get_tracking_mode_and_warnings()` and logs any
  fallback warning via structlog. The `machine` path is unchanged
  on Linux+NVIDIA.

### Preserved (regression guards)

- The `gemma4` family stays excluded from `gpu-entry` per D18/F8.
  `test_gemma4_family_excluded_from_gpu_entry` is preserved
  unchanged.
- The `gemma4` family is additionally excluded from **every**
  `apple-silicon-*` profile. New invariant test
  `test_gemma4_family_not_compatible_with_any_apple_silicon`
  extends the P6 rule to Apple Silicon dispatch. Re-enabling any
  `(gemma4, apple-silicon-*)` pair requires new empirical evidence
  on Mac hardware and an explicit debt entry.
- **Linux + NVIDIA dispatch byte-identical to v2.5.0** —
  `select_profile()`'s new branch returns `None` from
  `_match_apple_silicon_profile()` when `caps.chip_brand` is None
  (i.e., on Linux);
  `get_tracking_mode_and_warnings()` returns `("machine", [])` on
  Linux. No existing CI invocation of `puma validate-baseline`
  changes behaviour.
- `puma validate-baseline` triage_jira: **PASS f1=0.5831,
  delta=-0.0036** (within ±0.01 tolerance).
- `puma validate-baseline` estimation_tawos: **PASS mae=5.7150,
  delta=+0.0000** (bit-exact).
- All 354 previously-passing tests continue to pass; +48 new for a
  total of **402** under `-m "not ollama"`.

### Empirical validation status

ALL `apple-silicon-*` profiles declare
`empirical_validation: pending`. PUMA's validation hardware is the
RTX 2060 Mobile 6 GB (`gpu-entry`); no Apple Silicon hardware is in
the validation set as of v2.6.0. The dispatch infrastructure shipped
here enables empirical validation when Mac hardware becomes
available; the testing protocol (H0/H1 task metrics, H2/H3 logprob
deltas; 6-step procedure) is documented in
`docs/CROSS_ARCH_REPRODUCIBILITY.md` § Testing protocol.

### Highlights

- **Apple Silicon catalogued end-to-end** without weakening any
  existing guarantee. The two compatibility sources of truth
  (`config/profiles.yaml` for `select_profile`, model
  `profiles_compatible[]` for dispatch) are now extended; the
  Linux path is unchanged.
- **Cross-arch reproducibility framed as an open empirical
  question.** The plus side of catalogue-without-validation is
  honesty: v2.6.0 ships a testable hypothesis (`f1` and `mae` are
  expected bit-exact across architectures; logprobs are not) and a
  protocol to close it out, instead of asserting compatibility
  without evidence.
- **macOS Mode B with one command.** `./start_puma.sh --native`
  boots Ollama natively (Metal accelerated) and a Python venv,
  then exits. No Docker installation required on the user's
  machine.
- **CodeCarbon survives on macOS.** v2.5.0's machine-mode default
  would silently fail on macOS without `sudo`. v2.6.0 falls back
  to process-mode with a warning that points back to the docs —
  imprecise but non-zero data.
- **48 new tests, zero regressions.** Every Apple Silicon code
  path is exercised through `unittest.mock` on Linux CI; the
  Sprint can move forward without Mac hardware while keeping the
  test suite honest.

## [2.5.0] — 2026-05-16

### Added

Sprint 8 (hardening — six post-v2.4.0 inconsistencies I5–I10 resolved;
gemma4 family stays empirically excluded from gpu-entry):

- `docs/MACOS_NOTES.md`: canonical macOS operational reference. Two
  operational modes documented — Docker Desktop (CPU-only inside the
  Linux VM, no Metal exposure, current default) and Native Ollama
  (Metal acceleration, planned for first-class support in v2.6.0).
  Performance expectations table marks every Apple-native row as
  *estimated, unvalidated*, and an explicit cross-architecture
  reproducibility caveat is recorded for x86_64 vs arm64. Resolves
  inconsistency **I5**.
- `docs/CATALOG_HISTORY.md`: versioned catalog changelog. The
  `config/models_catalog.yaml` now carries a `catalog_version`
  field at the YAML root (starting at `"2.5.0"`) plus a
  `catalog_changelog_path` pointer. Loader unchanged (the existing
  `raw.get("models", [])` already ignored extra root fields). New
  unit test `test_catalog_has_version_field` enforces the fields.
  Resolves inconsistency **I7**.
- `docs/baseline_references.md`: canonical empirical baselines now
  have a documented single source of truth. Records the v2.0.0 F1
  reference (0.5867 on triage), the v2.5.0 MAE reference (5.7150 SP
  on the new estimation canonical spec), and the fresh-Ollama-state
  validation protocol that prevents cross-scenario KV-cache
  contamination. Resolves inconsistency **I9**.
- `specs/runs/baseline_estimation_canonical.yaml`: canonical
  estimation baseline (qwen2.5:3b × zero-shot × N=200 × seed=42 ×
  T=0.0). The reference MAE of 5.7150 SP was established
  empirically in this release and verified bit-exact across four
  consecutive runs on the validation hardware (RTX 2060 Mobile
  6 GB, `gpu-entry`).
- `docs/TESTING.md`: per-module coverage breakdown with explicit
  rationale for sub-40 % modules (Streamlit dashboard views,
  reporting, CodeCarbon vendor branches). Distinguishes the
  default CI suite (`-m "not ollama"`) from the new
  Ollama-integration job (push to main/develop only). Resolves
  inconsistency **I10**.
- `.github/workflows/lint-and-test.yml`: new
  `integration-tests-ollama` job that installs Ollama, pulls
  `qwen2.5:1.5b`, and runs every `@pytest.mark.ollama` test on
  pushes to `main`/`develop` only. The job is marked
  `continue-on-error: true` so a transient Ollama failure does not
  gate the merge queue — its purpose is regression detection on
  the integration branches, not PR gating. Resolves inconsistency
  **I8**.
- `puma validate-baseline --expected-mae`: new flag mutually
  exclusive with `--expected-f1`. When supplied without `--spec`,
  the command auto-selects the canonical estimation spec. Tests
  cover the F1 path (preserved), the MAE PASS/FAIL paths,
  mutual-exclusivity (exit 2), missing-metric (exit 2), and a
  regression guard on the MAE-path default-spec resolution.
  Resolves inconsistency **I9**.
- `docs/HARDWARE.md`: new section "gpu-entry profile — hardware
  equivalence and tolerance" documenting expected tolerance bands
  for RTX 2060 / 3050 / 3060 / 4050 / 4060 Mobile and an Apple
  M-series cross-arch row pointing to `MACOS_NOTES.md`. F1 is
  expected bit-exact (±0.000) on any NVIDIA gpu-entry hardware
  under T=0.0 + seed=42; latency and energy ranges are documented
  but not validated cross-machine. Resolves inconsistency **I6**.

### Changed

- `config/models_catalog.yaml`: now versioned at the YAML root
  with `catalog_version: "2.5.0"` and `catalog_changelog_path`.
  The list-of-dicts shape under `models:` is unchanged. No catalog
  entries were modified in this release.
- `docs/troubleshooting.md`: corrected the misleading note that
  claimed Metal acceleration works automatically inside the Ollama
  container on macOS. Docker Desktop's Linux VM does not expose
  Metal. Now links to `docs/MACOS_NOTES.md`.
- `README.md`: GPU-requirement row now states "NVIDIA (validated).
  AMD ROCm and Apple Metal not yet detected; macOS Docker runs
  CPU-only" with a link to `MACOS_NOTES.md`. Tests-passing badge
  updated to 354.
- `src/puma/cli.py::validate_baseline`: signature extended with
  `--expected-mae` (`float | None`). When neither flag is
  provided, the historical default behaviour (F1 = 0.5867 on the
  triage baseline) is preserved unchanged. No existing CI
  invocation breaks.
- `tests/unit/test_cli_validate_baseline.py`: 3 → 8 tests
  (3 existing + 5 new for the MAE path, mutual exclusivity,
  missing metric, and default-spec resolution).
- `tests/unit/test_catalog_metadata.py`: 4 → 5 tests with the new
  `test_catalog_has_version_field`. The pre-existing
  `test_gemma4_family_excluded_from_gpu_entry` regression guard is
  preserved unchanged per the gemma4 status-clarification decision.

### Highlights

- **Six inconsistencies resolved (I5–I10).** None required
  weakening a regression-guard test or re-introducing a
  previously-rejected `(model, profile)` pair. F8 (gemma4:e2b
  measured at 7.2 GB) and D18 (empty `raw_response` on
  `gpu-entry`) remain closed and documented in
  `docs/CATALOG_HISTORY.md`.
- **Estimation canonical baseline established.** v2.5.0 publishes
  the first empirical MAE reference for `puma validate-baseline`
  on `estimation_tawos`: **5.7150 SP** on `qwen2.5:3b × zero-shot
  × N=200`, bit-exact across four verification runs. Documented
  with its establishing `run_id` in
  `docs/baseline_references.md`.
- **Cross-scenario state contamination finding.** Running
  `triage_jira` between an Ollama restart and the estimation
  validation perturbs the model's KV-cache state and shifts MAE
  to ≈6.3150 SP — a regression well outside the ±0.05 tolerance.
  The fresh-Ollama-state validation protocol that prevents this
  is documented alongside the reference in
  `baseline_references.md`.
- **Tests: 354 passing.** +6 over v2.4.0; baseline reproducibility
  preserved (`validate-baseline` triage PASS `f1=0.5831,
  delta=-0.0036`); new `validate-baseline` MAE path PASS
  `mae=5.7150, delta=+0.0000`.
- **Catalog now versioned.** Future entries follow the convention
  documented in `docs/CATALOG_HISTORY.md`: bump
  `catalog_version`, mark new entries `empirical_validation:
  pending` until validation, never re-enable a previously-excluded
  `(model, profile)` pair without new evidence.
- **CI gains a real Ollama integration suite.** The four
  `@pytest.mark.ollama` tests previously had no CI coverage; the
  new push-only job runs them on every integration-branch push.

## [2.4.0] — 2026-05-13

### Added

Sprint 7 (CLI completeness for Anexo F):
- `docs/anexo_F_cli_reference.md`: source-of-truth document defining
  Section A (implemented commands) and Section B (proposed extensions).
  Resolves the gap between the academic Anexo F and the actual
  repository state by making the implementation status of each command
  explicit and verifiable via `puma <comando> --help`.
- Six new CLI commands implementing Section A.2 of the Anexo F:
  - `puma prepare-datasets` (A.2.1): subprocess wrapper of
    `scripts/prepare_datasets.py` with `--dataset`, `--force-redownload`,
    `--verify` flags. `--force-redownload` removes existing CSVs so
    the script regenerates; `--verify` emits SHA-256 hashes.
  - `puma wilcoxon` (A.2.2): Wilcoxon signed-rank pairwise comparison
    between two named `run_id`s. NEW analysis using
    `puma.metrics.statistical_tests.wilcoxon_signed_rank_models` from
    Sprint 3; the existing `scripts/wilcoxon_topmodels.py` keeps its
    top-K workflow. Outputs Markdown with statistic, p-value,
    significance marker (`***`/`**`/`*`/`n.s.`), effect size `r`
    approximated from `|Z| / √N`.
  - `puma bias-analysis` (A.2.3): bias evaluation report from perturbed
    runs already in the DB. NEW analysis using
    `puma.dashboard.data.load_predictions_with_gold` and
    `puma.metrics.fairness.perturbation_disparity`; `--models` /
    `--perturbations` filters; writes Markdown to `--output`.
  - `puma generate-plots` (A.2.4): subprocess wrapper of
    `scripts/generate_phase_b_plots.py` for `--source phase_b`.
    `--source bias_eval` and `multi_seed` documented but exit 2 with
    deferred-implementation message.
  - `puma list-runs` (A.2.5): SQL pivot of `runs ⋈ metrics` with
    `--scenario`, `--model`, `--last-n`, `--since` (ISO or `24h`/`7d`
    relative) filters, `--json` output, exit 2 on no-rows-match.
  - `puma list-ollama-models` (A.2.6): parses `docker exec puma_ollama
    ollama list` subprocess output. `--json` output.
- `tests/cli/`: 27 new TDD tests covering the six new commands (4-7
  tests per command: `--help`, happy path, error paths, JSON output).

### Changed

- `src/puma/cli.py`: 363 → 777 LOC. New commands implemented inline
  following the existing monolithic pattern. Refactor to a
  `src/puma/cli/commands/` package was considered and deferred —
  with six commands the monolith remains the cleaner option; the
  refactor would be justified if/when Section B extensions land.

### Highlights

- **Anexo F implementation gap resolved.** Section A (implemented) and
  Section B (proposed extensions) are now explicitly distinguished in
  `docs/anexo_F_cli_reference.md`. Section A is operationally verified
  via `puma <comando> --help` and the `tests/cli/` suite.
- **Six high-value CLI commands.** Wrappers of existing scripts
  (`prepare-datasets`, `wilcoxon`, `bias-analysis`, `generate-plots`)
  and inspection commands (`list-runs`, `list-ollama-models`) cover
  the workflows that demand most frequent operator access.
- **Tests: 348 passing.** +30 over v2.3.0; baseline reproducibility
  preserved (`validate-baseline` PASS `f1=0.5831, delta=-0.0036`).
- **17 Section B extensions documented as design space** without
  implementation: 5 Bash auxiliary scripts (`stop_puma.sh`,
  `restart_puma.sh`, `clean_puma.sh`, `status_puma.sh`, `logs_puma.sh`)
  and 12 further CLI commands (Ollama management, sweep wrappers,
  DB tooling, code-quality wrappers). Decision rationale recorded in
  `docs/anexo_F_cli_reference.md` § B: priority for high-value /
  low-cost commands over cosmetic wrappers of standard tooling.

## [2.3.0] — 2026-05-13

### Added

Sprint 6 (dashboard polish, Phase C close):
- `src/puma/dashboard/views/`: 7 modular view modules — one per
  dashboard view — each exposing a `render()` entry point. Modules
  are independently importable and testable; the router consumes
  them via a `VIEWS` dict.
- `src/puma/dashboard/views/_base.py`: shared helpers for view
  modules (`DB_PATH`, `no_data`, session-state filter accessors).
- First-visit guided tour: expander listing the 7 views and tips
  (download CSV, dark mode, tooltips). Persistent dismiss via
  `st.session_state["tour_dismissed"]`; "📖 Show tour" button in
  sidebar to re-open.
- CSV download buttons on 4 data tables (Model Comparison aggregate,
  Robustness, Fairness baseline + directional, Instance Drill-down).
- Tooltips (`help=`) on ≈ 12 metric cards (ECE, CO₂, kWh, latency p95,
  F1, parse failure, etc.).
- `components.empty_filtered_state`: unified message component for
  views with no data after filtering, with separate copy for empty-DB
  vs. empty-after-filter cases.
- `components.download_csv_button`: small helper that wraps
  `df.to_csv` + `st.download_button` with a default 📥 label.
- 5 new dashboard smoke tests (view module imports, router structure,
  polish helpers, cache decorator presence). Suite grew from 6 → 11
  dashboard tests; project total 313 → 318.

Phase E.bis / E.ter (documentation structure):
- `INDEX.md` (root, uppercase): project status, phases, releases,
  debt tracking, architecture entry points.
- `docs/overview.md` (new location): preserves the 256 LOC of
  architectural content from the legacy lowercase `index.md`.
- `docs/RELEASES/v2.3.0.md`: this release's notes.

### Changed

Sprint 6:
- `src/puma/dashboard/app.py`: refactored from 803 LOC monolithic to
  168 LOC router (-79 %). View logic delegated to `views/` modules;
  filters published to `st.session_state` by the router and read by
  each view's `render()` (which now takes no args).
- `@st.cache_data(ttl=60, show_spinner=False)` applied to 7
  frequently-called data loaders (`load_runs`, `load_metrics`,
  `load_predictions`, `load_predictions_with_gold`, `load_emissions`,
  `load_sustainability`, `load_profile_snapshots`, `metrics_pivot`).
  Reduces redundant DB queries during reruns. Distinct `db_path`
  arguments produce distinct cache entries, preserving test isolation.
- `st.spinner` wrapped around slow `load_*` and matplotlib renders
  across all 7 views.
- Module-level imports of `matplotlib.pyplot` and
  `puma.metrics.fairness.perturbation_disparity` (removed N×inline
  duplications previously needed by the monolithic file).
- Emoji prefixes applied consistently across the 7 view titles
  (matches the tour table).
- `page_icon` changed from `:bar_chart:` to `🐾` for consistency
  with the PUMA logo in the sidebar.
- Friendly expander titles in Overview (`model · YYYY-MM-DD · F1=…`)
  instead of raw 60-char `run_id` strings (still shown as a caption
  inside the expander).
- README.md: branded header with PUMA logo, descriptive blockquote,
  and Related-Resources section linking to puma-vault, INDEX.md, and
  `docs/overview.md`. Sidebar caption expanded to the full PUMA
  acronym.

### Fixed

Sprint 6:
- Dark-mode dataframe text colour: previous CSS rule left text at
  `#1A2E2A` over the `#1A1A2E` dark background, making tables nearly
  unreadable. New rule forces `#E5E7EB` text and `#16213E` cell
  background when dark mode is on.
- Hidden N+1 access in Overview: `load_predictions(DB_PATH)` was
  invoked twice inside a single metric_card call to compute "unique
  instances". Extracted to a single local variable; with the new
  cache decorator this is a no-op on the second call anyway.
- Empty selectbox in Instance Drill-down when filters yielded no
  runs: now shows the unified informative message and returns early.
- `.github/workflows/release.yml` no longer creates duplicate draft
  releases on tag push (E.bis fix; retroactively documented here).

### Highlights

- **Dashboard production-quality.** `app.py` shrank 79 % (803 → 168
  LOC) and gained 10 polish improvements (caching, spinners, CSV
  export, tooltips, friendly titles, empty-state unification, dark-
  mode bug fix). Phase C of the master plan is now fully complete
  — all five Gate-C criteria met.
- **Documentation structured.** `INDEX.md` (project state) and
  `docs/overview.md` (architecture) replace the legacy `index.md`
  with clearer separation of concerns. `README.md` adopts the
  visual identity of the PUMA Research Vault.
- **318 tests passing.** +5 over v2.2.0 covering view module
  integrity, polish helpers, cache decorator presence, and the
  end-to-end AppTest render with the live database.
- **CI hygiene.** GitHub release workflow corrected to prevent
  duplicate drafts on tag push; the v2.3.0 release verifies the fix
  is effective.

## [2.2.0] — 2026-05-13

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
- Dashboard core (Sprint 4, Phase C):
  - `.streamlit/config.toml`: PUMA visual identity (emerald palette
    `#2E7D6A`, sans-serif typography, telemetry disabled).
  - `src/puma/dashboard/data.py`: new `load_predictions_with_gold`
    LEFT-JOINs `predictions ⋈ instances` to expose `gold_label` and
    `input_text` correctly. Fixes a silent bug in two views that read
    `gold_label` from `predictions` (where it does not exist). Also
    new `load_emissions` and `load_sustainability` for the
    quality-vs-cost views.
  - 5 fully functional dashboard views: Overview (cohort cards plus
    per-run expanders, sidebar filters applied), Model Comparison
    (mean±std aggregation over seeds plus run×metric heatmap and
    Wilcoxon artefact rendering), Reliability (real ECE plus
    reliability diagram from logprobs), Sustainability Frontier (F1
    vs CO₂ Pareto consuming the emissions table from Sprint 2 D15),
    Instance Drill-down (gold_label correct via JOIN, top-K logprobs
    rendered, outcome filters).
  - 2 informed placeholders: Fairness and Robustness (made functional
    by Sprint 5).
  - PUMA logo integrated in sidebar (160 px wide).
  - Dark-mode toggle via runtime CSS override.
  - `tests/unit/test_dashboard_smoke.py`: 6 smoke tests (module
    parse, components callable, all 9 loaders exposed, loaders handle
    missing DB, JOIN exposes `gold_label` against an in-memory DB,
    end-to-end render via `streamlit.testing.v1.AppTest`).
- Empirical bias evaluation suite (Sprint 5, Gate D criterion 4):
  - `src/puma/perturbations/gender_swap_prefix.py`: identity prefix
    injection (`John Smith reported: …` vs `Mary Smith reported: …`).
    Deterministic across processes via SHA-256 over `(seed, text)` —
    Python's builtin `hash()` is process-randomised and would have
    silently broken seed-to-seed reproducibility. Methodology per
    Caliskan et al. (2017) and Bolukbasi et al. (2016). 10 TDD tests.
  - `src/puma/perturbations/register_shift.py`: 19-entry
    formal→informal substitution table with a cascade-prevention
    invariant verified by test (no value is also a key). Acts as a
    register-variation proxy for the dialect axis on a monolingual
    technical corpus per Tatman (2017). 7 TDD tests.
  - `src/puma/metrics/fairness.py`: extended with
    `perturbation_disparity` returning `acc_baseline`, `acc_perturbed`,
    `disparity`, `flip_rate`, `flip_to_correct`, `flip_to_incorrect`.
    Preserves the existing `fairness_report` used elsewhere. 8 TDD
    tests.
  - `src/puma/orchestrator/runner.py`: `_build_perturbation_fns`
    mapping extended with three entries; the runner's existing
    `("original", None)`-plus-perturbations loop persists baseline
    and perturbed predictions in one pass.
  - `specs/runs/sweep_bias_perturbations.yaml`: 2 models × (baseline
    + 3 perturbations) × 100 instances = 800 inferences.
  - `scripts/bias_analysis.py`: per-(model, perturbation) disparity
    vs un-perturbed baseline plus paired male-vs-female directional
    comparison; writes `docs/results/bias_evaluation.md`.
  - Dashboard Fairness and Robustness views now functional with real
    perturbed data; fall back to placeholder text when no perturbed
    runs are in the selected cohort.

### Changed

- CHANGELOG.md: `[Unreleased]` section consolidated into `[2.2.0]`.
- README.md and `docs/RELEASES/`: refreshed for v2.2.0 (see commit
  `docs(release): consolidate v2.2.0`).

### Fixed

- Silent JOIN-on-the-wrong-table bug in two dashboard views (Fairness
  and Instance Drill-down read `gold_label` from `predictions`, where
  it did not exist; correct source is `instances`). Fix lives in the
  new `load_predictions_with_gold` data-layer helper.

### Removed

### Methodological findings

- D19 (fairness scaffolding only) is now closed empirically. See
  `docs/known_debt.md` "Resolved technical debt" section.
- D22 (synthetic `triage_jira` dataset persists only `instance_id`
  and `gold_label`; `instances.input_text` is empty) added under Low
  in this release. Affects Dashboard Instance Drill-down render but
  not evaluation metrics. Surfaced during Sprint 4 S4.3.0 when
  JOIN-ing `predictions ⋈ instances` to fix the silent `gold_label`
  bug.

### Highlights

- **Bias evaluation empirically completed.** Adapted methodology to
  technical corpus (signal injection instead of substitution,
  following Caliskan et al. and Bolukbasi et al.). Key empirical
  findings on triage_jira × N=100 per condition: qwen2.5:1.5b shows
  ~25 % prediction flip rate with a gender signal added
  (-11 to -12 pp accuracy, 15 % directional bias male vs female);
  qwen2.5:3b shows the same flip rate but only -3 to -4 pp accuracy
  and 5 % directional bias — the model 3× larger exhibits ~3× less
  directional bias. `register_shift` (formal↔informal) shows ~0 %
  effect: both models robust to register variation but sensitive
  to sociodemographic signal.
- **Multi-seed validation confirms bit-exact reproducibility under
  T=0.0.** Three seeds {42, 123, 456} on the canonical baseline yield
  zero variance, validating the deterministic guarantee documented
  in v2.0.0.
- **ECE pipeline end-to-end.** Baseline qwen2.5:3b shows
  ECE=0.39 — significant miscalibration, expected for out-of-the-box
  LLMs without post-hoc calibration. Now visible in the Dashboard
  Reliability view (real logprobs, no synthetic data).
- **Dashboard with 5 functional views and 2 informed placeholders.**
  Visual identity applied; dark mode functional; emissions data from
  Sprint 2 surfaced in the Sustainability Frontier view. Polish
  (animations, guided tour, refactor to `views/` modules) deferred
  to a future Sprint 6.
- **15 of 23 known debt items now resolved (65 %).** Remaining 8 are
  0 critical, 5 medium, 2 low (1 decided-no-action).
- **Methodological note:** four independent findings (D15, D18, D21,
  D22) share a meta-pattern documented in `docs/known_debt.md`:
  "symptom appears in layer N, root cause in layer M ≠ N". This
  pattern is preserved for academic traceability.

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

[Unreleased]: https://github.com/pumacp/puma/compare/v2.6.0...HEAD
[2.6.0]: https://github.com/pumacp/puma/releases/tag/v2.6.0
[2.5.0]: https://github.com/pumacp/puma/releases/tag/v2.5.0
[2.4.0]: https://github.com/pumacp/puma/releases/tag/v2.4.0
[2.3.0]: https://github.com/pumacp/puma/releases/tag/v2.3.0
[2.2.0]: https://github.com/pumacp/puma/releases/tag/v2.2.0
[2.1.0]: https://github.com/pumacp/puma/releases/tag/v2.1.0
[2.0.0]: https://github.com/pumacp/puma/releases/tag/v2.0.0
