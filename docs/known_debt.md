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
| D18 | `gemma4` family produces outputs incompatible with current scenario parsers. The MoE-specific token format and CPU-offload artifacts on VRAM-constrained hardware combine to produce unparseable responses | Phase B.3 sweep (NEW) | gemma4:e2b on gpu-entry yielded parse_failure_rate 0.98–1.00 across all 3 scenarios; runs took 4–82 minutes despite producing no usable predictions | Either implement a gemma4-aware parser or document gemma4 family as systematically incompatible with `gpu-entry` profile (recommend skip in catalog `profiles_compatible[]`) | Before any future sweep includes gemma4 |
| D15 | CodeCarbon GPU detection inside container reports `gpu_energy = 0` because the RTX 2060 is not visible to the codecarbon process from within `puma_runner` | Phase B.1.4 | All 27 B.3 sweep emissions rows have `gpu_energy_kwh = 0` despite GPU-bound runs (e.g., `gemma3:12b` engaging GPU significantly) | Investigate `nvidia-runtime` configuration in `docker-compose.yml`, verify `pynvml` and `nvidia-smi` accessible inside container, possibly use `--privileged` or specific device passthrough | Before any Phase B run that loads >6 GB into VRAM (currently relevant for `gemma3:12b` and any 12B+ models) |
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
| ~~D18-cleanup~~ | ~~`pyproject.toml` has `version = "2.0.0-dev"` which causes the published wheel to be named `puma-2.0.0.dev0-py3-none-any.whl` instead of `puma-2.0.0-py3-none-any.whl`~~ — **PARTIALLY CLOSED in Sprint 1**: bumped `2.0.0-dev` → `2.1.0-dev` (development now targets next minor). Full versioning policy (bump to clean string before tag, bump to next `-dev` after) deferred to release-process documentation in Phase E | Phase A.7 observation | Bumped | Sprint 1 (partial) |

## Summary

- Closed methodological findings: **8**
- Closed in Sprint 1: **7** (D1, D6, D10, D13, D17, D18-cleanup, D21)
  - D21 was detected mid-sprint during D17 smoke verification and folded
    into Sprint 1 as task S1.5.bis; see CHANGELOG for the full sequence.
- Open technical debt items: **8** (Critical: 2 — D15, D18; Medium: 5; Low: 1; one of those marked `DECIDED-NO-ACTION`)
- Total items tracked across project lifecycle: **24**

## Updating this document

When new debt is identified during a phase, add the entry under the
appropriate severity section with the format used by existing entries:
ID (next available number), description, source (phase or sub-task
where detected), empirical evidence (if any), action pending, and
recommended phase for resolution.

When debt is resolved, move it from "Open technical debt" to a new
top-level section "Resolved technical debt" (parallel to "Methodological
findings during validation") with the resolution noted.
