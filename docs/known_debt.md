# Known Debt and Methodological Findings

This document tracks two distinct categories of items detected during
PUMA development:

1. **Methodological findings**: observations made during validation
   that have been resolved (either by fix, characterization, or
   documented decision-no-action). These are kept here as a record
   of project rigor.
2. **Open technical debt**: items not yet resolved, classified by
   severity, with recommended phase for resolution.

## Methodological findings during validation (closed)

These are observations detected during the cleanup and validation
phase of v2.0.0 and either resolved in-place or accepted as documented
decisions.

| ID | Finding | Detected | Status | Resolution |
|----|---------|----------|--------|------------|
| F1 | Reference baseline F1=0.5867 corresponds to `contextual-anchoring` strategy, not pure zero-shot (which yields F1=0.3898 on the same configuration) | Phase A.0 | DOCUMENTED | Canonical spec is `specs/runs/baseline_triage.yaml`; configuration acknowledged in CHANGELOG |
| F2 | Cold-vs-warm reproducibility characterization: bit-exact in warm state, drift ≤0.006 cold-vs-warm | Phase A.0 | CHARACTERIZED | Within stated tolerance ±0.01; documented in CHANGELOG and v2.0.0 release notes |
| F3 | Tooling-CI version drift (pre-commit pinned `ruff v0.4.4` while CI installed latest; PT023 and SIM300 default behavior changed between versions) | Post-A.6 push exposed CI failure | FIXED | Exact pin `ruff==0.15.12` in `.pre-commit-config.yaml`, `requirements-dev.txt`, and `pyproject.toml` |
| F4 | Dataset regeneration scope mismatch: `scripts/download_datasets.py` processes a local TAWOS SQL dump rather than fetching from a remote source. The "regenerable in CI" assumption was only true for Jira | Post-A.6 push exposed missing CSVs | MITIGATED | Re-tracked the processed CSVs (~12 MB total) in repo; documented true regeneration path in `data/README.md` |
| F5 | Release workflow `GITHUB_TOKEN` lacked `contents: write` permission (HTTP 403 when calling `softprops/action-gh-release@v2`). Pre-existing bug since `v0.10.0-rc.1` (May 2026) | Phase A.7 first attempt | FIXED | Added `permissions: contents: write` at workflow level in `.github/workflows/release.yml` |
| F6 | CodeCarbon declared as first-class sustainability metric in v2.0.0 but the orchestrator never invoked the `EmissionsTracker`. The `puma.sustainability` module, `Emission` ORM, and `emissions` table were complete; only the runner-level wiring was missing | Phase A.0 (detected) → Phase B.1.4 (fixed) | FIXED | Wired `EmissionsTracker.start()/.stop()` in `src/puma/orchestrator/runner.py`; row persisted to `emissions` table in same session as `Metric` |
| F7 | Catalog/profiles drift: 17 (profile, model_tag) pairs declared compatible in `models_catalog.yaml.profiles_compatible[]` were missing from `profiles.yaml.{profile}.models[]`. Two manually-maintained sources tend to diverge | Phase B.1.2 | FIXED | Refactor to single source of truth: removed `models[]` field from `profiles.yaml`; added `models_for_profile(profile_name)` helper in `src/puma/preflight/catalog.py` that derives the list dynamically from the catalog |
| F8 | `gemma4:e2b` had `gguf_size_gb: 2.0` in catalog versus 7.16 GB actual on disk (3.6× error). Root cause: catalog field copied "effective parameters" value (2B) instead of measuring the actual GGUF (which contains all MoE experts, including inactive ones) | Phase B.1.5 | FIXED | Corrected to 7.2 GB; explanatory notes added to `gemma4:e2b`, `gemma4:e4b`, `gemma4:26b-a4b`; `check_provisioning` disk calculation now accurate for this model |

## Open technical debt

Items not yet resolved, classified by severity. Each item includes
recommended phase for resolution.

### Critical (block sweep interpretation if not addressed)

| ID | Description | Source | Empirical evidence | Action pending | Recommended phase |
|----|-------------|--------|--------------------|----------------|-------------------|
| ~~D17~~ | ~~`deepseek-r1` parse_failure_rate ≈ 0.8 with `triage_jira` scenario.~~ — **CLOSED in Sprint 1**: added `puma.scenarios._reasoning.strip_reasoning` helper that strips `<think>...</think>` blocks (closed, unclosed, stray-tag variants) before extraction, wired into all three scenario parsers; 8 unit tests | Phase B.2.5 smoke | parse_failure 0.8 in 5-instance smoke; excluded from B.3 sweep | Implemented | Sprint 1 |
| ~~D21~~ | ~~Runtime client `timeout_s = 120.0` is hard-coded in `puma.runtime.client` and not consulted from `ModelEntry.timeout_s`.~~ — **CLOSED in Sprint 1 (S1.5.bis)**: added `puma.runtime.client.client_for_model` factory that looks up the catalog entry and threads `timeout_s` into `OllamaClient`; runner builds the client per-model inside the loop; `gemma3:12b` catalog timeout bumped 180→1800s (B.3 evidence: 631s/590s observed); `deepseek-r1:7b` catalog timeout already 300s (no bump needed). 5 TDD tests | Sprint 1 D17 smoke (NEW) | 20-instance deepseek-r1:7b smoke on triage_jira: 3 consecutive `500 \| 2m0s` responses from `/api/generate` over 24 minutes; no predictions persisted | Implemented | Sprint 1 (S1.5.bis) |

### Medium (improve correctness or coverage)

| ID | Description | Source | Action pending | Recommended phase |
|----|-------------|--------|----------------|-------------------|
| D16 | `gemma4:e4b` and `gemma4:26b-a4b` have unverified `gguf_size_gb` values (not cached locally). Same root cause as F8 (MoE effective vs total params) is plausible. **Reinforced by D18 evidence**: even if sizes are correct, gemma4 family appears to have parser incompatibility on `gpu-entry` | Phase B.1.5 | Either pull and verify on hardware where gemma4:e4b can fit (gpu-mid or higher) and verify parser works there; or systematically remove gemma4 family from `gpu-entry` `profiles_compatible[]` | Phase B in upper-tier hardware; or short-term: catalog cleanup |
| D2 | `adaptation.cot` field declared in `runspec.py:25` but inert. CoT behavior is activated only via the separate `zero-shot-cot` strategy, not via the field | Phase A.0 | Decide between (a) wire the field to actually toggle CoT independently, (b) remove the field as misleading, or (c) document as alias of `strategy=zero-shot-cot` | Phase D or E |
| D5 | Cold-vs-warm reproducibility characterization is in CHANGELOG but not in user-facing documentation | Phase A.0 | Add reproducibility section to user-facing `docs/` covering when bit-exact reproducibility holds and how to interpret deviations | Phase E |
| D3 | Investigate Ollama runtime flags and CUDA workspace configuration for stricter determinism | Phase A.0 | Research `OLLAMA_LLM_LIBRARY`, `CUBLAS_WORKSPACE_CONFIG`, `CUDA_LAUNCH_BLOCKING` and document recommended setup for maximum reproducibility | Phase E |
| ~~D6~~ | ~~Timestamp columns in ORM models use Python-side defaults, not database-side `server_default`~~ — **CLOSED in Sprint 1**: Alembic migration `0002_server_default_timestamps` adds `server_default=func.now()` to `runs.started_at`, `metrics.computed_at`, `emissions.recorded_at`; ORM updated; AC-11 test added | Phase A.1 | Implemented | Sprint 1 |
| ~~D1~~ | ~~`--validate-baseline` CLI flag declared in earlier specifications but not implemented~~ — **CLOSED in Sprint 1**: added `puma validate-baseline` subcommand with `--spec`, `--expected-f1`, `--tolerance`, `--db`, `--ollama-host` options; 3 TDD tests with monkeypatched runner | Phase A.0 | Implemented | Sprint 1 |
| D19 | `fairness` metric family is scaffolding only in v2.0.0; the CHANGELOG already discloses this as future work | Phase A.8 | Implement bias-related perturbations (`gender_swap`, `dialect`) and corresponding metrics | Phase D |
| D20 | Laptop thermal characteristics may bias `duration_s` and energy measurements during sustained sweeps. **Empirical evidence from B.3**: `mistral:7b` showed 10–18× duration variance across 3 scenarios on the same hardware (129 s vs 1377 s vs 2299 s) consistent with thermal throttling or memory pressure transients | Hardware audit + B.3 sweep evidence | (a) Document expected behavior in CHANGELOG and `docs/HARDWARE.md`, (b) consider running sweeps in chunks with cooldown intervals, (c) require AC power for sweep runs (not battery) | Future Phase B re-runs; document in B.4 analysis |

### Low (cosmetic, process, or non-blocking)

| ID | Description | Source | Action pending | Recommended phase |
|----|-------------|--------|----------------|-------------------|
| D8 | 8 ruff codes suppressed in tests via `[tool.ruff.lint.per-file-ignores]`: `B011`, `PT011`, `RUF012`, `SIM117`, `SIM118`, `PT018`, `UP038`, `RUF002` | Phase A.3 | Refactor tests progressively to comply with each rule, removing suppressions one at a time | Future tech-debt cleanup |
| D9 | `mypy` not yet integrated as pre-commit hook (gradual adoption strategy). Strict mode is preserved in `pyproject.toml` for `puma.metrics`, `puma.runtime`, `puma.preflight` modules | Phase A.3 | Add `mypy` hook conditional on full type coverage of those modules; run manually until ready | Future tech-debt cleanup |
| ~~D10~~ | ~~`pre-commit` not installed as a local git hook (incompatibility with cross-container development workflow)~~ — **CLOSED in Sprint 1**: `docs/CONTRIBUTING.md` documents host-only setup via `pipx` plus the cross-container fallback (manual `pre-commit run --all-files` from host) and CI as safety net | Phase A.3 | Documented | Sprint 1 |
| D11 | Git history prior to commit `1abd831` contains references to internal operational documents (now relocated to `docs/internal/`, gitignored) | Phase A.9 | DECIDED-NO-ACTION. Rewriting history with `git filter-repo` would break clones and any references to specific commits in academic memoria; disproportionate for non-artifact documents | (closed by decision) |
| ~~D13~~ | ~~`scripts/download_datasets.py` is mis-named: it processes a local SQL zip dump, not downloads anything~~ — **CLOSED in Sprint 1**: renamed to `scripts/prepare_datasets.py`; references updated across `src/puma/datasets/tawos.py`, `data/README.md`, `docs/user_guide.md`, `docs/troubleshooting.md` | Phase A.7 | Renamed | Sprint 1 |
| D14 | No automated fetch path for the upstream TAWOS SQL dump | Phase A.7 | Investigate UCL repository API or Zenodo alternative mirror; add fetch step with checksum verification to `scripts/` | Future feature |
| D22 | Synthetic `triage_jira` dataset persists only `instance_id` and `gold_label`; original ticket descriptions (`input_text`) are empty in the `instances` table. Limits instance-level inspectability in dashboard drill-down views but does not affect evaluation metrics. Surfaced during Sprint 4 S4.3.0 when JOIN-eing `predictions ⋈ instances` to fix the silent `gold_label` lookup bug in two views; the JOIN itself works but the joined `input_text` column is empty in 200/200 rows of the active dataset | Sprint 4 S4.3.0 dashboard integration | Modify `scripts/create_jira_data.py` to populate `input_text` with original ticket descriptions; re-ingest dataset; re-run baseline to verify reproducibility holds (F1 should remain 0.5867 ± 0.01 if the prompt template was already using a placeholder for the input) | Future data pipeline enhancement, before next major dataset refresh |
| ~~D18-cleanup~~ | ~~`pyproject.toml` has `version = "2.0.0-dev"` which causes the published wheel to be named `puma-2.0.0.dev0-py3-none-any.whl` instead of `puma-2.0.0-py3-none-any.whl`~~ — **PARTIALLY CLOSED in Sprint 1**: bumped `2.0.0-dev` → `2.1.0-dev` (development now targets next minor). Full versioning policy (bump to clean string before tag, bump to next `-dev` after) deferred to release-process documentation in Phase E | Phase A.7 observation | Bumped | Sprint 1 (partial) |

## Resolved technical debt

Items previously tracked as open technical debt that have been fully
resolved, with the resolution and supporting evidence preserved here
for academic traceability. Sprint 1 closures remain inline in the
"Open technical debt" tables above with strikethrough notation; the
following entries document the more involved resolutions from Sprint 2
onward, where the fix touched multiple files and had measurable
empirical impact.

### D15 — CodeCarbon GPU detection inside container

**Status:** CLOSED in Sprint 2 (2026-05-10).

**Symptom (pre-fix).** All 27 B.3 sweep emissions rows had
`gpu_energy = 0` despite GPU-bound runs (e.g., `gemma3:12b` engaging
GPU significantly). `kwh` and `co2_kg` figures in the `emissions`
table consequently reflected only CPU+RAM energy.

**Root cause — two coupled issues hiding behind a single symptom.**

1. *Infrastructure.* The `puma_runner` container in
   `docker-compose.yml` did not declare CDI GPU passthrough. Even
   though `puma_ollama` (where inference actually runs) had GPU
   access, the orchestrator container — where `EmissionsTracker`
   was instantiated — did not, so `pynvml` failed to load
   `libnvidia-ml.so.1` and CodeCarbon enumerated zero GPU devices.

2. *Measurement method.* `EmissionsTracker` was instantiated with
   `tracking_mode="process"` in both
   `src/puma/orchestrator/runner.py` and
   `src/puma/sustainability/codecarbon_wrapper.py`. In PUMA's
   multi-container architecture the runner process is an HTTP
   client to `puma_ollama`; it does not drive the GPU directly.
   `tracking_mode="process"` therefore measures only the
   orchestrator's own (CPU-only) energy and would have continued to
   report `gpu_energy = 0` even after the passthrough fix.

Resolving either issue in isolation would have left
`gpu_energy = 0` in the emissions rows. This is a textbook case of
*apparently-correct infrastructure + apparently-correct measurement
= incorrect result if the two are not aligned*.

**Resolution.**

- `docker-compose.yml`: added the same CDI passthrough block to
  `puma_runner` that `puma_ollama` already declared
  (`driver: cdi`, `capabilities: [gpu]`,
  `device_ids: [nvidia.com/gpu=all]`).
- `src/puma/orchestrator/runner.py` and
  `src/puma/sustainability/codecarbon_wrapper.py`: changed
  `tracking_mode="process"` → `tracking_mode="machine"`. Under the
  documented sweep convention (AC power + idle host + no other GPU
  consumers) whole-machine consumption attributes correctly to
  PUMA.

**Tests.** New file
`tests/integration/test_codecarbon_gpu_detection.py` with 3 tests
gated on the `requires_gpu` marker (skip automatically when no
NVIDIA GPU is visible, e.g., on CI runners): pynvml init,
`EmissionsTracker._total_gpu_energy > 0` after `stop()`, and a real
Runner `dry_run=True` end-to-end persisting an emissions row with
`gpu_energy > 0`. The `requires_gpu` marker is registered in
`pytest.ini`.

**Empirical evidence post-fix.** Smoke
`d15_smoke` (qwen2.5:3b × 10 instances on triage_jira, codecarbon
enabled), 2026-05-10:

| column | value |
|--------|------:|
| `gpu_energy` | 3.85e-05 kWh |
| `cpu_energy` | 8.42e-06 kWh |
| `ram_energy` | 3.71e-05 kWh |
| `kwh` (total) | 8.40e-05 kWh |
| `co2_kg` | 1.46e-05 kg |
| `duration_s` | 7.17 s |

This is the first emissions row in the project's history with
non-zero `gpu_energy`.

**Comparability impact.** Post-D15 emissions rows are **not directly
comparable** to pre-D15 rows on the `gpu_energy` column (and
therefore on the `kwh` / `co2_kg` totals for GPU-bound runs). The 27
B.3 sweep rows underreport total CO₂. This is documented in
`CHANGELOG.md`, `docs/HARDWARE.md`, and `docs/results/phase_b_analysis.md`.

**References.** PR `feature/sprint-2-critical-debt`, Sprint 2 task
S2.1.

### D18 — gemma4 family parser incompatibility on gpu-entry

**Status:** CLOSED in Sprint 2 (2026-05-10) via documented exclusion.

**Symptom (pre-fix).** B.3 sweep (9 models × 3 scenarios × 100
instances on `gpu-entry`) recorded `parse_failure_rate` 0.98–1.00 for
`gemma4:e2b` across all 3 scenarios (triage_jira, estimation_tawos,
prioritization_jira) despite per-run wall times of 4–82 minutes. The
runs accounted for **60.5 % of total sweep CO₂** while producing zero
usable predictions.

**Originally hypothesised cause.** A MoE-specific token format or
CPU-offload artifacts producing outputs that the PUMA scenario
parsers could not interpret. The action pending originally proposed
"implement a gemma4-aware parser or document gemma4 family as
systematically incompatible with `gpu-entry`".

**Actual root cause (confirmed by S2.2 diagnostic).** The issue lies
one layer below the PUMA parser, at Ollama's detokenizer:

| evidence | observation |
|----------|-------------|
| 5-instance `gemma4:e2b` triage run, `raw_response` in DB | All 5 rows: empty string, `len = 0`, `parsed_label = None` |
| `tokens_out` in same rows | All 5 rows: 256 (saturated the `num_predict` cap) |
| Direct `POST /api/generate` with simple prompt `"Reply with just the word: hello"` | `response='hello'`, `eval_count=2`, `done_reason='stop'` ✓ |
| Direct `POST /api/generate` with real PUMA contextual-anchoring prompt (743 chars, 160 prompt tokens) | `response=''`, `eval_count=32` (hit cap), `done_reason='length'` ✗ |
| Same call with `think=True` / `think=False` | No `thinking` field returned; behaviour unchanged |

On gpu-entry (RTX 2060 6 GB VRAM) the 7.2 GB `gemma4:e2b` GGUF
forces partial CPU offload. Under that condition the model emits
tokens that the Ollama server's detokenizer cannot decode into a
valid string — `eval_count` advances but `response` is empty. The
PUMA parser receives `''` and cannot recover anything because there
is no content to parse. An MoE-aware parser would not help: the
fault is in the inference path, not the post-processing.

**Resolution.** Documented exclusion of the gemma4 family from the
`gpu-entry` profile:

- `config/models_catalog.yaml`: `gpu-entry` removed from
  `profiles_compatible` for `gemma4:e2b` and `gemma4:e4b`.
  `gemma4:26b-a4b` already did not list it (16 GB GGUF). Each
  entry's `notes` field now explains the D18 exclusion with a
  pointer to the empirical evidence.
- `tests/unit/test_catalog_metadata.py`: added
  `test_gemma4_family_excluded_from_gpu_entry`, which asserts
  `gpu-entry not in profiles_compatible` for all three gemma4 tags.
- The gemma4 family **remains available** for `gpu-mid` and
  `gpu-high` profiles, where the model fits in VRAM and CPU offload
  is not triggered. Re-evaluation on that hardware is left as future
  work.

**Scope note (followups identified during S2.2, deferred).**
`gemma4:e2b` retains `cpu-standard` in `profiles_compatible`. By the
same root-cause logic, that configuration is also expected to
exhibit the detokenizer issue (no VRAM at all → full CPU offload).
That has not been empirically tested in this project. Tracked as a
future low-priority follow-up rather than expanded here, to keep
this resolution scoped to the original D18 finding on `gpu-entry`.

**References.** PR `feature/sprint-2-critical-debt`, Sprint 2 task
S2.2. B.3 sweep evidence in `docs/results/phase_b_analysis.md`
("60 % wasted compute" finding).

## Summary

- Closed methodological findings: **8**
- Closed in Sprint 1: **7** (D1, D6, D10, D13, D17, D18-cleanup, D21)
  - D21 was detected mid-sprint during D17 smoke verification and folded
    into Sprint 1 as task S1.5.bis; see CHANGELOG for the full sequence.
- Closed in Sprint 2: **2** (D15 measurement-and-infrastructure fix;
  D18 documented exclusion based on detokenizer diagnostic).
- Open technical debt items: **7** (Critical: 0; Medium: 5; Low: 2; one of those marked `DECIDED-NO-ACTION`)
- Total items tracked across project lifecycle: **24**

No critical debt remains after Sprint 2. The repository is in
release-quality state pending the medium / low backlog (catalog
verification on upper-tier hardware, dashboard polish, reproducibility
documentation, etc.).

## Updating this document

When new debt is identified during a phase, add the entry under the
appropriate severity section with the format used by existing entries:
ID (next available number), description, source (phase or sub-task
where detected), empirical evidence (if any), action pending, and
recommended phase for resolution.

When debt is resolved, move it from "Open technical debt" to a new
top-level section "Resolved technical debt" (parallel to "Methodological
findings during validation") with the resolution noted.
