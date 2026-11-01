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

### D23 — Verifier Space algorithmic mismatch with the client (since v3.0.0)

**Status:** open. Scheduled for resolution: v4.x with a schema decision.
**Severity:** low — affects only `puma community verify-hash --remote`; local
verification is unaffected and remains canonical.

**Description.** The client (`src/puma/community/integrity.py`,
`compute_predictions_hash`) computes `predictions_summary_hash` over a 4-field
CSV `(instance_id, predicted_label, predicted_value, prompt_hash)` read from the
PUMA database, joined by LF, then SHA-256 (plain 64-hex, no prefix). The Verifier
Space `pumaproject/puma-verifier` (`app.py`) computes its hash over a 2-field
JSONL `(instance_id, prediction)` fetched from `raw_predictions_url`, then SHA-256
prefixed with `sha256:`. The two operate on different inputs and different
formats, so they never agree by construction.

**Schema note (correction to an earlier Sprint 11' assumption).**
`raw_predictions_url` IS an optional field in schema v1.0.0
(`submission.v1.json`, absent from `required`), so `--remote` is reachable
whenever a submission sets that field — contrary to the initial premise that the
field was absent. The limitation is purely algorithmic, not a missing field.

**Impact.**
- `puma community verify-hash --remote` returns a systematic `mismatch` for
  genuine submissions that set `raw_predictions_url`. The command detects the
  local-verified + remote-mismatch case, warns, and treats it as
  `verified-local-only (D23 warned)` (exit 0).
- Submissions without `raw_predictions_url` (the common case, since the field is
  optional) give `--remote` no URL to fetch; the command prints an informational
  note and falls back to the canonical local result.
- Local verification (`verify-hash` without `--remote`) is canonical and fully
  functional.

**Path to resolution (deferred to a future Sprint with explicit schema scope).**
(a) Converge the Verifier onto the canonical 4-field CSV algorithm — requires the
    client to publish that CSV alongside the submission (e.g. to the HF dataset).
(b) Strip the `sha256:` prefix on the Verifier side (the S11'.5 minimal repair)
    and redefine the Verifier's input to match the client — still needs a way to
    recover the 4 canonical columns from a public artifact.
Both directions require a decision on which canonical artifact the Verifier
consumes; neither is attempted in Sprint 11'.

**Deferral rationale (S12.2 empirical confirmation, 2026-05-25).** A controlled
discovery session in Sprint 12 S12.2 attempted the client-side alignment and
HALTED before any edit, confirming D23 is schema-decision work, not a
mechanical fix. Four blockers were identified empirically:
1. The Sprint 12 plan assumed a `src/puma/community/hashing.py` with a
   `_compute_summary_hash` function; neither exists. The real producer is
   `integrity.compute_predictions_hash`, a 4-field CSV hash. The plan was
   working from a stale model of the code.
2. **Schema vs Verifier prefix contradiction.** The schema mandates
   `predictions_summary_hash` match `^[a-f0-9]{64}$` (plain 64-hex, no prefix,
   `schema_data/submission.v1.json:78-81`) and is immutable (P3). The Verifier
   emits `sha256:<hex>`. Cross-service string equality cannot be reached by
   editing only the client hash; it needs a Verifier-side prefix strip
   (FORBIDDEN + the Space is not git-accessible) or a `verify_cli` `--remote`
   comparison change (separate scope).
3. **"prediction" is semantically undefined for PUMA.** The 4-field canonical
   deliberately carries both `predicted_label` (triage_jira / prioritization_jira)
   and `predicted_value` (estimation_tawos). A single 2-field
   `(instance_id, prediction)` requires ratifying what "prediction" maps to per
   scenario.
4. **Unverifiable in isolation.** The Verifier Space source is not on GitHub
   (`pumacp/puma-verifier` and `pumaproject/puma-verifier` both 404) and
   `HF_TOKEN` was unavailable, so no 2-field implementation could be confirmed
   byte-for-byte against the live Space. A wrong guess would pass local
   `verify-hash` (client agrees with itself) while breaking production silently.

**Three open decisions D23 closure requires.** (a) Which side adapts — client
to Verifier, Verifier to client, or a third shared canonical. (b) How to
reconcile the `sha256:` prefix with the immutable schema (`verify_cli --remote`
comparison logic vs Verifier-side strip). (c) What "prediction" maps to per
scenario if the chosen canonical is 2-field. **Target: a schema-decision Sprint
after v4.0.0.** Cross-references: S12.2 HALT report; D27 (the exporter, RESOLVED
in S12.2, which productizes the *existing* 4-field canonical and is decoupled
from this decision); `schema_data/submission.v1.json:78-81` (the immutable
constraint).

**Decision (2026-10-31).** Option (a) approved by the maintainer: the Verifier
adopts the client's 4-field canonical form (`instance_id`, `predicted_label`,
`predicted_value`, `prompt_hash`; LF-joined CSV; SHA-256 as plain 64-hex). No
schema change; existing submissions are untouched; implementation pending.

### D24 — Canonical baseline specs missing `profile_required` (since v1.0.0)

**Status:** RESOLVED in v4.0.0 (Sprint 12 S12.1). Discovered: 2026-05-25
(Sprint 11' E2E demo attempt, S11'.10.a).
**Severity:** medium — blocks the publication pipeline on canonical runs out
of the box.

**Description.** The shipped specs under `specs/runs/baseline_*.yaml` do not
declare the `profile_required` field. The runner
(`src/puma/orchestrator/runner.py:68`) populates `Run.profile` only from
`spec.profile_required`. The publication pipeline builder
(`src/puma/community/builder.py:320-321`) requires `Run.profile` to be
non-NULL. Therefore, no run produced by a canonical spec can be turned into a
shareable submission.

**Impact.** All canonical runs in the Sprint 11' DB at v3.1.0 release time
have `Run.profile = NULL` and cannot feed `share-results`.

**Detection.** S11'.10.a attempted to produce a real demo submission and was
blocked at the builder precondition. A one-off untracked demo spec
(`specs/runs/demo_triage_s11p.yaml`) was used to bridge the gap locally
(adding `profile_required: gpu-entry`); the run's F1 stayed 0.5831 bit-exact,
confirming the field is metadata, not an inference parameter. The broader fix
is to add `profile_required` as a declared field in canonical specs.

**Path to resolution.** Two viable approaches:
(a) Add `profile_required` to each canonical baseline spec with a sensible
    default (e.g. `auto-detect` resolved at run time).
(b) Make `runner.py:68` fall back to the auto-detected profile when the spec
    does not declare `profile_required`.
Either approach is a small code or spec change in a future Sprint.

**Resolution (Sprint 12 S12.1).** Implemented approach (b): `runner.py` now
resolves `Run.profile` via `_resolve_run_profile`, which returns
`spec.profile_required` when declared and otherwise falls back to the existing
`select_profile(detect_capabilities())` auto-detection, logging an INFO line
(`run.profile_autodetected`). Commit `54fd53e`. Empirically bit-exact (F1
triage 0.5831) and covered by `tests/unit/test_runner_profile_fallback.py`.

### D25 — Canonical baseline specs disable codecarbon (since v1.0.0)

**Status:** RESOLVED in v4.0.0 (Sprint 12 S12.1). Discovered: 2026-05-25
(Sprint 11' E2E demo attempt, S11'.10.a).
**Severity:** medium — blocks the publication pipeline on canonical runs (same
flow as D24).

**Description.** The canonical baseline specs ship with
`sustainability.codecarbon: false`. As a result, no emissions record is created
in the DB. The publication pipeline builder
(`src/puma/community/builder.py:330`) requires an emissions record to exist.
Therefore, even with D24 bridged (`Run.profile` set), the absence of an
emissions record blocks `share-results` on canonical runs — empirically the
second precondition hit during S11'.10.a, after D24 was bridged.

**Impact.** Same scope as D24: canonical runs are not publishable directly.

**Path to resolution.** Default `sustainability.codecarbon` to `true` in
canonical specs (cheap to enable; minor overhead). Alternative: relax the
builder requirement to allow runs without emissions records, with a clear
warning.

**Resolution (Sprint 12 S12.1).** Flipped `sustainability.codecarbon` from
`false` to `true` in `specs/runs/baseline_triage.yaml` and
`specs/runs/baseline_estimation_canonical.yaml`, so canonical runs now produce
the emissions record `builder.py:330` requires. Commit `6a2c812`. Empirically
verified the flip does not affect inference: F1 triage stays 0.5831 (within
±0.01) and MAE estimation stays 5.7150 bit-exact.

### D26 — `runner.py` never populates `ProfileSnapshot.extra` (since v1.0.0)

**Status:** RESOLVED in v4.0.0 (Sprint 12 S12.1). Discovered: 2026-05-25
(Sprint 11' E2E demo attempt, S11'.10.a).
**Severity:** medium-high — the hard blocker preventing any canonical run from
feeding `share-results`. Unlike D24 and D25, this is **not** spec-fixable; it
requires a code change.

**Description.** `src/puma/orchestrator/runner.py:526`
(`_add_profile_snapshot`) constructs a `ProfileSnapshot` without ever setting
the `extra` field, so `extra` is empty for every run. The publication pipeline
builder (`src/puma/community/builder.py:365`) requires
`ProfileSnapshot.extra['cpu_cores']` to be present. Therefore, even with
D24 + D25 bridged via spec, the runner output still fails the builder's snapshot
completeness check. (The same function also hardcodes a stale
`puma_version="2.0.0-dev"`.)

**Why this gap remained latent until S11'.10.a.** The `share-results` and
`puma community *` subcommand test fixtures (e.g.
`tests/community/conftest.py:218`) hand-craft full `ProfileSnapshot` records
including `extra['cpu_cores']`. Because no test exercised the runner → builder
integration end-to-end, the gap between what the runner produces and what the
builder requires remained invisible. Unit tests at 80-89% coverage on the
community CLI did not catch it.

**Impact.** Combined with D24 + D25, no canonical run can be turned into a
publishable submission. The community CLI subcommands implemented in
Sprint 11'.2 (`validate`, `verify-hash`, `browse`, `pull`) are architecturally
complete and unit-tested, but the upstream pipeline that feeds them with real
artifacts cannot operate on canonical inputs.

**Path to resolution.** Populate `ProfileSnapshot.extra` in
`_add_profile_snapshot` with at minimum `cpu_cores` (via `os.cpu_count()` or
`psutil`), plus a `puma_version` derived dynamically from the package version
(instead of the hardcoded `"2.0.0-dev"`). Estimated effort: < 1 day including
a small integration test that exercises the full pipeline from `puma run`
through to a validated submission.

**Methodological note.** This gap is a textbook case where component-level unit
testing (which passes at high coverage) does NOT substitute for end-to-end
integration testing with real artifacts. Future Sprints should add a single
end-to-end integration test that runs the full pipeline on a fresh, real
submission to catch this class of regression.

**Resolution (Sprint 12 S12.1).** `_add_profile_snapshot` now populates
`ProfileSnapshot.extra` via `_collect_profile_extra` (`cpu_cores`,
`cpu_physical_cores`, `memory_total_gb`, `platform`, `python_version`,
`has_cuda`, `cuda_device_name`) and derives `puma_version` dynamically via
`importlib.metadata.version("puma")` (`_resolve_runner_puma_version`),
replacing the hardcoded `"2.0.0-dev"`. Commit `a76bec9`. Covered by
`tests/unit/test_profile_snapshot.py`. The methodological note's recommendation
was acted on: `tests/integration/test_e2e_publication.py` (US-12.5) now
exercises the full runner → share-results → community CLI pipeline end-to-end,
the regression test that would have caught D24/D25/D26 immediately.

### D29 — Estimation predictions-hash run-to-run nondeterminism (since v3.0.0)

**Status:** TRACKED — defer to post-v4.0.0 schema-decision sprint (alongside D23).
**Discovered:** Sprint 12 / S12.7b determinism oracle check (2026-05-26).

**Finding.** Three independent runs of the canonical estimation baseline on
byte-identical code produce three different `predictions_summary_hash` values
(e.g. `89f0e30…` / `7a89130…` / `604d324…`). The reported metric MAE is
bit-exact `5.7150` across all runs. Triage hashes are bit-identical across runs.

**Root cause.** `src/puma/community/integrity.compute_predictions_hash` hashes
`parsed_label` as a raw string. The estimation LLM (`qwen2.5:3b` at
`temperature=0.0`, `seed=42`) emits the same numeric value in occasionally
different string forms (`"5"` vs `"5.0"` vs `"5.00"`). String form differs →
hash differs; numeric value identical → metric identical. Triage labels are
categorical (no string-form variation) → triage hashes are stable.

**Impact.**
- The reproducibility claim "`predictions_summary_hash` bit-equal across runs"
  is FALSE for estimation; any documentation asserting hash-level reproducibility
  for estimation submissions must be qualified to metric-level only until D29 is
  resolved.
- Verifier roundtrip validation of estimation submissions is affected: a
  legitimate re-run of the same code produces a different submission hash, which
  the Verifier may flag as mismatch despite identical metrics. (Within a single
  run, the exported JSONL still matches that run's declared hash, so local
  `verify-hash` is unaffected.)

**Resolution path.** Normalize `parsed_label` to a canonical numeric form (e.g.
a float formatted with fixed precision such as `"%.6f"`) before hashing in
`compute_predictions_hash`. This makes the hash invariant to
string-representation noise while preserving metric bit-exactness. Coordinate
with D23 (Verifier hash 2-field alignment + `sha256:` prefix) in the
schema-decision sprint, since both changes touch integrity hashing.

**P1 capture (P1-S12.7b-COORD-01).** Coordinator-level prompt drift: the S12.7b
prompt asserted hash-level determinism as a mandatory gate, but the actual P2
invariants are metric-level. The gate was over-strict; the metric invariants
(F1 = 0.5831 ±0.01, MAE = 5.7150 bit-exact) are upheld in this phase.

### D30 — Docs sync for the new `models` subcommand structure (since v4.0.0)

**Status:** RESOLVED (2026-05-31, S12.17) — stale `puma models pull` /
`puma list-ollama-models` references rewritten across `README.md`,
`docs/user_guide.md`, `docs/troubleshooting.md`, `docs/adding_models.md`;
held-out docs repaired and re-entered the mkdocs nav (six groups, 26
public pages); `docs/cli_reference.md` already current for the v4.0.0
sub-group surface. `mkdocs build --strict` exits 0 with zero warnings.
**Discovered:** Sprint 12 / S12.9 discovery pass (2026-05-26).

**Finding.** S12.9 replaced the legacy `puma models` (catalog-print + `ollama
pull` via subprocess) and `puma list-ollama-models` (docker-exec subprocess
wrapper) with a read-only `puma models` Typer sub-group (`list` / `show` /
`recommended`). Several docs still reference the removed command forms.

**Affected docs.**
- `docs/user_guide.md` — `puma models list`, `puma models pull qwen2.5:3b`
- `docs/troubleshooting.md` — `puma models pull qwen2.5:3b`, `puma models list`
- `docs/adding_models.md` — `puma models pull`, `puma models list`
- `README.md` — the `puma models` one-line description
- `docs/cli_reference.md` — locked this phase (S12.9 FORBIDDEN); regeneration
  needs its lock lifted in the docs-sync phase.

**What changed.**
- `puma models list` (catalog YAML print) → `puma models recommended` (themed
  table with local availability)
- `puma models pull <tag>` → `ollama pull <tag>` (use the Ollama CLI directly;
  `puma doctor` already hints `ollama pull <name>` for missing models, so the
  guidance stays consistent)
- `puma list-ollama-models` → `puma models list` (httpx `/api/tags`, themed)

**Field-gap note (curated catalog).** `config/models_catalog.yaml` does not
encode `validated_for` / `status` / `rationale`; `puma models recommended`
derives them with conservative defaults (`validated_for={triage, estimation}`,
`status=experimental`, `rationale` from the catalog `notes`). The YAML is NOT
modified this phase. Adding these fields to the catalog schema is the natural
complement to this docs-sync work.

**Resolution path.** In the next docs-focused phase (or S12.17), update each
affected doc to reference the new commands and regenerate
`docs/cli_reference.md` (its lock lifted there).

**Update (S12.11, 2026-05-26).** mkdocs scaffolding is in place (Material theme,
`mkdocs build --strict` green). The published site is intentionally MINIMAL —
nav surfaces only `index`, `cli_reference`, `sustainability`, `known_debt`, and
`RELEASES/v3.1.0`; every other doc is held out of the build via `exclude_docs`
(kept on disk, not deleted). The stale user-facing docs (`user_guide`,
`troubleshooting`, `adding_models`), the remaining reference docs, the older
release notes, and `RELEASES/v3.0.0.md` (its `../../CHANGELOG.md` link aborts
strict and the file is locked) are all queued for the S12.17 content sync, which
will fix their links/content and add them to the nav. `overview.md` also has
broken `../CONTRIBUTING.md` / `../CHANGELOG.md` links to repair in S12.17.

**P1 capture (P1-S12.9-COORD-01).** Coordinator-level prompt drift: the S12.9
prompt assumed `puma models` was greenfield, but a legacy
`@app.command(name="models")` plus a separate `puma list-ollama-models`
already existed, and `config/models_catalog.yaml` already contained the
17-entry curated registry the prompt was about to hardcode in Python. Detected
by the executor's discovery pass before branching (audit-before-write).
Resolution: re-scoped to REPLACE legacy with the new sub-group, reuse the
existing YAML catalog, and drop `pull` (read-only phase per S12.9 FORBIDDEN);
docs-sync tracked here as D30. Third coordinator-level prompt drift of Sprint 12
(after P1-S12.2-COORD-01 and P1-S12.7b-COORD-01).

### D31 — Estimation MAE baseline drift in the current Ollama runtime (since v4.0.0)

**Status:** TRACKED — environment/reproducibility finding; investigate under D3
(Ollama/CUDA determinism) and F2 (cold-vs-warm drift).
**Discovered:** Sprint 12 / S12.9 baseline re-validation (2026-05-26).

**Finding.** The canonical estimation baseline
(`specs/runs/baseline_estimation_canonical.yaml`, `qwen2.5:3b`,
`temperature=0.0`, `seed=42`) now produces `mae=6.3150`, a +0.6000 shift from
the P2 reference `5.7150` (outside the ±0.01 gate). The triage baseline F1 in
the same session is `0.5891` (+0.0060, within ±0.01).

**Isolation (not caused by S12.9).**
- Reproduces identically (`6.3150`) on pristine `origin/develop` @ `6f09b2d`
  with no S12.9 code present; the estimation code path is byte-identical there.
  S12.9 adds only read-only discovery commands and removes two legacy CLI
  commands — it touches no inference/estimation code.
- Stable across three runs (two warm, back-to-back) — a deterministic shift,
  not sampling noise.
- Model unchanged: `qwen2.5:3b` digest `357c53fb659c`, modified 6 days prior,
  quant `Q4_K_M`; Ollama `0.21.0`. The model was not re-pulled.
- The Ollama container had been restarted ~20 min before the session, so the
  warm runtime state differs from when `5.7150` was last captured (S12.8).

**Likely cause.** Ollama runtime nondeterminism across container/runtime
restarts (GPU kernel scheduling / batching) — the same class as F2 (cold-vs-warm
drift ≤0.006 on F1) and D3 (untuned CUDA determinism flags). Estimation MAE is
numerically more sensitive than categorical triage F1, so the same runtime
perturbation moves MAE well beyond the ±0.01 window while F1 stays within it.

**Resolution path.** (1) Characterize the drift across N warm runs to establish
the current-environment MAE distribution; (2) apply and document the D3
determinism configuration (`CUBLAS_WORKSPACE_CONFIG`, `OLLAMA_*` flags) and
re-measure; (3) if the shift persists as a stable environment property, re-pin
the canonical estimation MAE reference (with its supporting run set) and update
the reproducibility docs (D5). Until then, the estimation MAE gate must be
interpreted against the current runtime, not the historical `5.7150`.

**Scope note.** Does not block S12.9 (read-only discovery, no inference path);
recorded here so the failing MAE gate during S12.9 re-validation is traceable
and not mistaken for an S12.9 regression.

### D32 — License compatibility automation (since S12-N2)

**Status:** OPEN — deferred from S12-N2 MVP scope.
**Discovered:** Sprint 12 / S12-N2 security audit MVP (2026-05-31).

**Finding.** The S12-N2 MVP wires `pip-audit` (CVE scanning), `bandit`
(Python SAST), `gitleaks` (secret scanning), and `Trivy` (container CVE
scanning) into CI, but does not automate license compatibility. A
non-permissive license (GPL, AGPL, custom restrictive terms) entering
the production dependency tree via a transitive update would not be
caught until manual review at release time.

**Resolution path.** Add `pip-licenses` (or equivalent) as a CI step
that emits a license inventory and fails the build on any non-MIT /
non-BSD / non-Apache-2.0 / non-PSF-License license in the production
dependency closure. Allowlist explicit exceptions with a documented
rationale.

**Rationale for deferral.** Right-sized out of S12-N2 MVP scope to keep
the security audit deliverable focused on vulnerability scanning;
license-compatibility automation is a candidate for the post-Sprint-12
backlog or the next security audit cycle.

### D33 — SBOM CycloneDX generation (since S12-N2)

**Status:** OPEN — deferred from S12-N2 MVP scope.
**Discovered:** Sprint 12 / S12-N2 security audit MVP (2026-05-31).

**Finding.** Published artifacts (the `puma-cp` PyPI wheel and the
`ghcr.io/pumacp/puma:vX.Y.Z` container image) ship without a Software
Bill of Materials. Downstream consumers cannot programmatically
verify the dependency closure or correlate published-artifact contents
with upstream advisories at install time.

**Resolution path.** Add a CI step that runs `cyclonedx-py` (Python
deps) and `syft` or `Trivy` SBOM mode (image layers) and attaches the
CycloneDX SBOM as an asset to every published release; reference it
from `SECURITY.md` and `docs/security.md`.

**Rationale for deferral.** Right-sized out of S12-N2 MVP scope to keep
the security audit deliverable focused on detection (vulnerability
scanning); the SBOM is a provenance artifact that is most useful once
v4.0.0 actually ships and downstream consumption begins. Candidate
for the next security audit cycle.

### D34 — Mutation testing on `src/puma/community/integrity.py` (since S12-N2)

**Status:** OPEN — deferred from S12-N2 MVP scope.
**Discovered:** Sprint 12 / S12-N2 security audit MVP (2026-05-31).

**Finding.** `src/puma/community/integrity.py` is the canonical
implementation of the `SHA-256` over the canonical predictions tuple
that backstops every PUMA Community submission. The file is locked
(schema-bearing) and has unit + integration test coverage, but no
mutation-testing pass has verified that the tests would actually
catch subtle mutations of the canonical hash procedure (e.g. a
swapped sort order, a tuple ordering change, an off-by-one when
canonicalizing).

**Resolution path.** Run `mutmut` (or equivalent) on
`src/puma/community/integrity.py` with the existing test suite as the
oracle; document the mutation-survival rate; tighten tests where
needed; record the achieved score in `docs/security.md` §5.

**Rationale for deferral.** Mutation testing is non-trivial to set up
and tune (run-time, killable-but-not-killed analysis, allowlist for
equivalent mutants); right-sized out of S12-N2 MVP scope. Candidate
for the post-Sprint-12 backlog.

### D35 — Cross-platform install test (since S12-N2)

**Status:** OPEN — deferred from S12-N2 MVP scope.
**Discovered:** Sprint 12 / S12-N2 security audit MVP (2026-05-31).

**Finding.** CI runs on `ubuntu-latest` only; the published wheel and
the published image are exercised on a single platform. A regression
that breaks the install on macOS (x86_64 or arm64) or Windows would
not surface until a contributor reports it.

**Resolution path.** Add a matrix job to a CI workflow (likely a new
`install-smoke.yml`) that installs `puma-cp` from the built wheel on
`ubuntu-latest`, `macos-13`, `macos-14` (arm64), and
`windows-latest`, and verifies `puma --help` exits 0.

**Rationale for deferral.** Right-sized out of S12-N2 MVP scope —
S12-N2 focuses on vulnerability detection, not platform-coverage
expansion. Candidate for the post-Sprint-12 backlog, ideally before
v4.0.0 ships so the published wheel is verified on the documented
target platforms.

### D38 — validate-submission workflow uses a non-existent action version (since S12-N1)

**Status:** RESOLVED (`pumacp/puma-community` PR #12, merged to `main` 2026-10-31).
**Discovered:** Sprint 12 / S12-N1 inaugural submission (2026-05-31).

**File.** `.github/workflows/validate-submission.yml` in `pumacp/puma-community`.

**Finding.** The workflow references
`actions-ecosystem/action-add-labels@v1.4.0`, a version that was never
published. On the inaugural submission (PR #8, 2026-05-31) the workflow failed
at the "Prepare all required actions" step, before any validation logic ran.

**Resolution path.** Pin the action to `@v1.3.0` (latest stable) or to a
current commit SHA.

**Resolution (`pumacp/puma-community` PR #12).** Commit `fba79b9`: both
labelling steps pin `actions-ecosystem/action-add-labels` to commit
`18f1af5e3544586314bbe15c0273249c770b2daf`, the `v1.1.3` release (see D52).
A new step fails the check when a PR modifies, deletes or renames any existing
file under `submissions/`, so only added files pass; the trigger now covers
every path under `submissions/` so such changes reach that guard. On a
`synchronize` event the `valid` label is removed before the new head is
validated, so a label earned by an earlier commit does not carry over.

### D39 — Verify submission integrity workflow broken by gradio_client API drift (since S12-N1)

**Status:** RESOLVED (`pumacp/puma-community` PRs #10, #11 and #13, merged to
`main` 2026-10-31); the labelling of PRs from forks remains a limitation (see
below).
**Discovered:** Sprint 12 / S12-N1 inaugural submission (2026-05-31).

**File.** `scripts/verify_submissions.py` in `pumacp/puma-community`, line 54.

**Finding.** The script calls `Client(VERIFIER_SPACE, hf_token=token)`; the
current `gradio_client` API expects `token=token` (without the `hf_` prefix).
The inaugural submission triggered the verify workflow, which failed with
`TypeError: Client.__init__() got an unexpected keyword argument 'hf_token'`.

**Consequence.** The inaugural submission carries
`integrity.verification_status="self-attested"` instead of `"verified"`. The
PUMA Leaderboard Space appears to filter for verified submissions, so the
inaugural row is not yet visible despite being correctly archived in the
submissions dataset.

**Resolution path.** Rename the `hf_token` kwarg to `token` in
`scripts/verify_submissions.py`; re-run verification on the inaugural
submission to upgrade its `verification_status`.

**Resolution (`pumacp/puma-community` PRs #11, #10 and #13).** Commit
`e9dc524` (PR #11): `scripts/verify_submissions.py` passes `token=` to
`gradio_client.Client`, reads the declared hash from
`integrity.predictions_summary_hash` (schema v1.0.0 has no top-level
`predictions_summary_hash`), and verifies only submission files newly added in
`HEAD~1..HEAD`; the fallback that globbed every file in `submissions/` is
removed, so existing submissions are never re-verified. A
`<id>.verified.json` sidecar is written only when the Verifier returns
`verified`; every other status is logged without writing a file. The inaugural
submission is not re-run (D53). Commit `a0da178` (PR #10):
`scripts/generate_badges.py` skips `*.verified.json` sidecars, so they are not
counted as submissions. Commit `653a9b3` (PR #13): `auto-merge-valid.yml` reads
each file's status from the pull-request files API and refuses auto-merge
unless every changed file is added.

**Remaining limitation.** `validate-submission.yml` runs on `pull_request` and
labels with `GITHUB_TOKEN`. On a PR opened from a fork that token is read-only,
so the `valid` / `invalid` labels cannot be applied and `auto-merge-valid.yml`,
which triggers on the `valid` label, does not run. A maintainer has to label
fork submissions by hand.

### D40 — `puma share-results` CLI hangs after the Review panel (since S12-N1)

**Status:** RESOLVED in v4.0.1 (PR #64, merged to `develop` 2026-10-31).
**Discovered:** Sprint 12 / S12-N1 inaugural submission (2026-05-31).

**File.** `src/puma/community/share_results.py` (likely) in `pumacp/puma`.

**Finding.** After printing the Review submission panel with "Action: will open
a PR against pumacp/puma-community", the CLI process either hangs indefinitely
or completes silently without opening the PR; the `--yes` flag does not bypass
whatever is blocking. Three attempts during the inaugural submission (S12-N1)
all stopped at the same point; no PR was opened by the CLI. A manual
`fork + push + gh pr create` was used as the workaround.

**Investigation needed.** Instrument the post-review-panel code path with debug
logging; verify the fork + push + PR-creation pipeline; check whether `--yes`
is honored by all confirmation prompts in the chain.

**Root cause (PR #64 investigation).** Two defects in
`src/puma/community/github_client.py` (`ensure_fork`), reproduced against an
in-process fake GitHub API; `--yes` was honoured, every prompt sits before the
Review panel.
1. `ensure_fork` assumed every authenticated user has, or can create, a fork
   named `puma-community` under their own account. For the upstream owner,
   `user.get_repo("puma-community")` returns the upstream itself
   (`fork == False`), so the client requested a fork of its own repository and
   polled 20 s for one that can never appear before failing. The inaugural
   submitter was the owner, which is why `pumacp/puma-community#8` carries a
   branch on the upstream rather than on a fork.
2. `Github(auth=...)` kept PyGithub's default `GithubRetry(total=10)`, which
   sleeps silently on 403 rate-limit answers (until the limit resets, up to an
   hour) and on 5xx, re-sending the fork request each time, and finally raises
   a `requests` `RetryError` that is not a `GithubException`, so it escaped both
   the client and the `except GitHubError` chain in `share_cli.py`.

**Resolution (PR #64).** Commit `88d843a`: the upstream owner publishes straight
to `pumacp/puma-community` (PR head `pumacp:submission/<id>`, the shape of
PR #8); a same-named repository that is not a fork of the upstream counts as
"no fork"; the client is built with `GithubRetry(total=2)` for transient 5xx
and an explicit 30 s timeout, calls `check_rate_limit()` before the first
write so an exhausted limit raises `APIRateLimitError`, and maps `requests`
transport errors to `GitHubError` so they reach the themed CLI handler; the
CLI prints one progress line before contacting GitHub. The submission payload
(schema v1.0.0), `submissions/<id>.json` path, `submission/<id>` branch name,
commit message and PR title/body are unchanged and asserted by tests. Covered
by `tests/community/test_github_client.py`,
`tests/community/test_share_cli.py` and
`tests/integration/test_share_results_fake_github.py` (owner, ordinary user,
exhausted rate limit, secondary-limit and 5xx fork failures; no network).

### D41 — Container image v4.0.0 blocked by Trivy on 3 HIGH base-image CVEs (since S12.18)

**Status:** RESOLVED in v4.0.1 (PR #67, merged to `develop` 2026-10-31); the
GHCR image remains unpublished until the next release tag runs
`publish-docker.yml`.
**Discovered:** Sprint 12 / S12.18 release ceremony (2026-05-31).

**File.** `Dockerfile.publish` (base image) in `pumacp/puma`.

**Finding.** During the v4.0.0 release ceremony the `publish-docker.yml` run
(26795071210) built the image successfully, but the Trivy scan reported 3 HIGH,
3 MEDIUM, and 1 LOW finding (0 CRITICAL) in the base image. The configured
`severity: CRITICAL,HIGH` / `exit-code: 1` gate failed the step, so the GHCR
push never ran; `ghcr.io/pumacp/puma:4.0.0` was not published. The SARIF was
uploaded to the GitHub Security tab under ref `refs/tags/v4.0.0`. This is the
security gate working as designed, not a code defect.

**Resolution path.** Update the base image in `Dockerfile.publish` to a
Trivy-clean patched tag (e.g. the most recent `python:3.11-slim` /
`python:3.12-slim` patch), rebuild, and re-run `publish-docker.yml`; ship as a
v4.0.1 patch release.

**Resolution (PR #67).** Commit `7d9496c`: both stages of `Dockerfile.publish`
pull `python:3.11-slim` by digest (the multi-arch index
`sha256:673719e0…` for 3.11.18-slim-trixie as of 2026-10-31). A rebuild
showed the pin alone does not clear the gate: the base ships setuptools
79.0.1, whose vendored wheel 0.45.1 (CVE-2026-24049) and jaraco.context
5.3.0 (CVE-2026-23949) are HIGH with fixes available, so `ignore-unfixed`
keeps them. The final stage therefore upgrades setuptools to 84.2.1 (vendors
wheel 0.46.3, no jaraco.context, no `pkg_resources`; no runtime dependency
imports `pkg_resources`). Local Trivy 0.76.1 with the workflow flags
(`CRITICAL,HIGH`, `ignore-unfixed`, `exit-code 1`): 2 HIGH before, 0 after;
`puma --version`, `puma --help` and the banner path run from the image.
Python 3.11.18, application packages, entrypoint, user and workdir are
unchanged. Nothing was pushed to GHCR; the image publishes on the next `v*`
tag.

### D42 — PyPI wheel does not bundle config/profiles.yaml and other data files (since S12.18)

**Status:** OPEN — owner: maintainer. Target: post-Sprint-12 (v4.0.1 / patch sprint).
**Discovered:** Post-S12.18 verification (`pip install puma-cp==4.0.0` in a clean venv).

**File.** `pyproject.toml` — missing `include-package-data = true` or a
`[tool.setuptools.package-data]` entry for non-Python data files.

**Finding.** A clean-venv install of `puma-cp==4.0.0` (at `/tmp/verify-v400`)
emits the runtime warning "Profile catalog not found at
`<venv>/lib/python3.12/config/profiles.yaml` — profile_id validation will
reject all values". The wheel bundles no `config/*.yaml` or JSON schema data.

**Consequence.** End users who install from PyPI cannot run benchmarks; hardware
profile validation rejects all values. Source-clone installs
(`pip install -e .[dev]`) are unaffected because `config/` is present in the
working tree.

**Resolution path.** Add `include-package-data = true` to the
`[tool.setuptools]` section, or enumerate package data via
`[tool.setuptools.package-data]` (`puma = ["config/*.yaml", "schema_data/*.json"]`).
Verify by rebuilding the wheel and inspecting it:
`python -m zipfile -l dist/puma_cp-*.whl | grep -E "(config|schema)"`. Ship in
v4.0.1.

### D43 — CLI does not expose a top-level `--version` flag (since S12.18)

**Status:** RESOLVED in v4.0.1 (PR #63, merged to `develop` 2026-10-31).
**Discovered:** Post-S12.18 verification.

**File.** `src/puma/cli.py` — the root Typer/Click command group.

**Finding.** `puma --version` returns "No such option '--version'. Did you mean
'--verbose'?". The CLI does not implement the standard `--version` convention.

**Consequence.** Cosmetic. Users expect `--version`; the current workaround is
`pip show puma-cp`.

**Resolution path.** Add `@click.version_option(package_name="puma-cp")` to the
root group (or the Typer equivalent). Ship in v4.0.1.

**Resolution (PR #63).** The root Typer callback in `src/puma/cli.py` now takes
an eager `--version` option that prints `puma-cp <version>` from
`importlib.metadata.version("puma-cp")` and exits 0, falling back to
`0.0.0-unknown` when no distribution is installed (plain source-tree runs).
Commits `5fdf755` (flag, unit tests, CLI reference row) and `8bd598d`
(colour-independent help assertion for CI) on `develop`. Verified on a wheel
built from the branch and installed in a fresh venv: `puma --version` →
`puma-cp 4.0.0`, exit 0, also when the flag precedes a subcommand. Covered by
`tests/unit/test_cli_flags.py::TestVersionFlag`.

### D44 — H2 estimation inferential test computed on preserved N=100 data with a global-mean baseline (since post-Sprint-12)

**Status:** OPEN — owner: maintainer. Target: when Ollama hardware is available and
instance-level project persistence (D22) is fixed.
**Discovered:** Post-Sprint-12 H2 reproducibility task (2026-06-04).
**Related:** **D22** (root cause for the baseline deviation), `D26`/RT3 (version sentinel).

**Files.** `docs/results/h2_estimation_wilcoxon.md`, `data/puma_h2_estimation.db`.

**Finding.** The pre-registered hypothesis H2 requires a Wilcoxon signed-rank test
of enriched-instruction configs against the project's **per-project** historical-mean
predictor on `estimation_tawos`. A real, independently-recomputable test was produced
(decision: **fail to reject H0_2**; best config `qwen2.5:7b` MAE = 1.86 vs global-mean
baseline 2.03, reduction 0.17 SP, p = 0.104, r = −0.16, N = 100), but under four
deviations from the pre-registration:

1. **Global-mean baseline instead of per-project mean** — the evaluated `instances`
   rows persist only a hashed id + gold label; `input_text`/project are empty
   (**D22**), so instances cannot be mapped to their TAWOS project.
2. **N = 100** — the only `contextual-anchoring` estimation data preserved at
   per-prediction granularity; the N = 200 canonical baseline was `zero-shot`.
3. **Preserved May-10 Phase-B predictions, not a fresh live run** — Ollama/Docker
   were unavailable in the environment.
4. **No run-twice determinism re-check** — requires live inference (the underlying
   run used seed = 42 / T = 0.0; the test computation itself is deterministic).

**Consequence.** The committed H2 result is valid for what it measures (global-mean
baseline, N = 100) but is not the full pre-registered test. It is labelled
data-availability-limited in the results doc.

**Resolution path (closure).** On hardware with Ollama: (a) fix **D22** so
`instances` persist project id + `input_text`; (b) re-run `estimation_tawos`
`contextual-anchoring` at N = 200 (seed = 42, T = 0.0) with per-prediction logging;
(c) compute the Wilcoxon test against the **per-project** historical-mean baseline;
(d) run the best config twice to confirm bit-exact MAE. Supersede
`h2_estimation_wilcoxon.md` with the fresh result.

### D45 — H1 triage inferential test uses a no-information majority-class baseline, not the pre-registered keyword heuristic (since post-Sprint-12)

**Status:** OPEN — owner: maintainer. Target: when `input_text` is re-ingested
(D22 fix) and Ollama hardware is available.
**Discovered:** Post-Sprint-12 H1 reproducibility task (2026-06-04).
**Related:** **D22** (root cause — empty `input_text`), **D44** (parallel H2 case).

**Files.** `docs/results/h1_triage_wilcoxon.md`, `data/puma_h1_triage.db`.

**Finding.** The pre-registered H1 test compares the triage model against a
**keyword-rule heuristic** baseline. That heuristic needs the ticket text, but the
preserved `instances` rows have empty `input_text` in 200/200 triage rows (**D22**),
so the heuristic is irrecoverable. A real, independently-recomputable test was
produced (decision: **REJECT H0_1**; qwen2.5:3b + contextual-anchoring F1-macro
0.5894 vs a no-information majority-class floor acc 0.25 / F1 0.10; Wilcoxon
p = 6.9e-13, r = -0.51, N = 200) under a **baseline substitution**: the keyword
heuristic was replaced by a constant-class floor computable from gold labels alone.

**Consequence.** H0_1 is rejected, but only against the weakest possible (chance-level)
baseline on a perfectly balanced 4-class set — a low bar. The result does not
establish superiority over a competitive heuristic. Other deviations: preserved
May-10 data (not a fresh live run); no run-twice re-check (the 5 stable N=200 runs
are byte-identical; the computation is deterministic); model digest not recorded.

**Resolution path (closure).** On hardware with Ollama: (a) fix **D22** so triage
`instances` persist `input_text`; (b) implement/run the keyword-rule heuristic
per-instance on the same N=200 set; (c) recompute the Wilcoxon test of model vs
keyword heuristic; (d) re-run the model config twice to confirm bit-exact F1.
Supersede `h1_triage_wilcoxon.md` with the fresh result.

### D46 — Leaderboard reads `verification.status` instead of `integrity.verification_status` (since post-Sprint-12)

**Status:** RESOLVED (`pumaproject/puma-leaderboard` Space commit `7de208b`,
2026-10-31).
**Discovered:** Sprint 12 community diagnostic.

**File.** `app.py` in `pumaproject/puma-leaderboard` (HF Space).

**Finding.** The leaderboard reads `record["verification"]["status"]`, but the
v1.0.0 submission schema exposes the status at
`record["integrity"]["verification_status"]`. The key path never matches, so the
"verified" column renders "—" for every submission regardless of its real status.

**Consequence.** Display-only; no effect on data or metrics. With a single
self-attested submission the visible effect is nil today.

**Resolution path.** Read the correct key and map
`self-attested` / `verified` / `mismatch`. Ship in v4.0.1.

**Resolution (Space commit `7de208b`).** `app.py` loads only the UUID-named
submission records (`submissions/????????-????-????-????-????????????.json`),
so `*.predictions.jsonl` and other sidecar files next to them are no longer
read, and the "verified" column reads `integrity.verification_status`. On the
running Space (2026-11-01) the leaderboard lists the inaugural submission
(`1d88e49b-5b49-46b9-a8a6-df7bdd5bf80b`, qwen2.5:3b / triage_jira /
zero_shot) with "verified" shown as `self-attested`.

### D47 — D39's description of leaderboard filtering is inaccurate (since post-Sprint-12)

**Status:** OPEN (documentation) — owner: maintainer. Target: v4.0.1 / patch sprint.
**Discovered:** Sprint 12 community diagnostic.

**File.** This file — the **D39** entry.

**Finding.** D39 states the leaderboard "appears to filter for verified
submissions, so the inaugural row is not yet visible". Inspection of `app.py`
(`get_leaderboard`) shows it filters only by scenario / model / profile; there is
no verification-status filter, so the row is shown with "—", not hidden.

**Consequence.** Documentation only — D39's stated consequence overstates the
effect. The deployed Space was not verified from the academic environment; the
local source is authoritative.

**Resolution path.** Correct the wording of the **D39** entry. Ship in v4.0.1.

### D48 — `pyproject.toml` dependencies omit runtime imports; `puma dashboard` fails from a pip install (since S12.15)

**Status:** RESOLVED in v4.0.1 (PR #71, merged to `develop` 2026-11-01).
**Discovered:** Post-v4.0.0 maintenance review (2026-10-31).

**Files.** `pyproject.toml` (`[project].dependencies`), `requirements.txt`,
`tests/unit/test_requirements_consistency.py`.

**Finding.** `requirements.txt:25-26` list `matplotlib>=3.8` and
`seaborn>=0.13`, but `[project].dependencies` declares neither, and the
published 4.0.0 wheel's `Requires-Dist` confirms they are absent. A reverse
check of every third-party import under `src/puma/` against the declared
dependencies finds one real gap: `matplotlib`, imported at module level by
`src/puma/dashboard/views/{model_comparison,reliability,robustness,sustainability}.py`
and lazily by `metrics/calibration.py` and `dashboard/components.py`. In a
clean `pip install puma-cp==4.0.0` venv, `import puma.dashboard.app` fails
with `ModuleNotFoundError: No module named 'matplotlib'`, so `puma dashboard`
cannot start; the CLI, runner and metrics still import because their uses are
lazy. `seaborn` is imported nowhere in the package (only
`scripts/generate_phase_b_plots.py`). The remaining undeclared imports are
intentional and guarded: `ollama` (lazy, inside the live evaluators),
`pyarrow` (explicit ImportError message for parquet output), `torch` (CUDA
probe in a try block) and `click` (a dependency of typer).
`test_requirements_consistency.py` checks only that pyproject names appear in
the requirements files, so this direction is unguarded.

**Consequence.** Users of the PyPI wheel and of the published container image
(built from the same wheel) cannot open the dashboard. Clone, Compose and CI
installs are unaffected because they install `requirements.txt`. Together
with **D42** (data files) this is the second wheel-completeness gap: D42 is
about files the package needs, D48 about dependency metadata.

**Resolution path.** Add `matplotlib>=3.8` to `[project].dependencies`
(`pyproject.toml` is not locked; the existing consistency test stays green
because `requirements.txt` already lists it); extend
`test_requirements_consistency.py` with the reverse direction (every
module-level third-party import under `src/puma/` resolves to a declared
dependency); decide whether `seaborn` stays in `requirements.txt` as a
scripts-only tool or is declared. Ship in v4.0.1.

**Resolution (PR #71).** Commit `4335e61`: `matplotlib>=3.8` is declared in
`[project].dependencies` with the same lower bound as `requirements.txt`;
`seaborn` is not declared. `test_requirements_consistency.py` gains
`test_module_level_imports_are_declared_in_pyproject`, which parses the top
level of every module under `src/puma/`, maps each third-party import to its
distribution through `importlib.metadata.packages_distributions()` and fails
if that distribution is not declared in the dependencies or an extra; imports
inside functions are out of scope because they are lazy. Before the fix, a
`pip install -e .` of `develop` and a `pip install puma-cp` (4.0.0) both lacked
matplotlib and the dashboard app raised `No module named 'matplotlib'`; a
wheel built from the branch carries `Requires-Dist: matplotlib>=3.8` and
`import puma.dashboard.app` works from a wheel-only venv. A module-level
`import ollama` added to a scratch copy makes the new test fail.

**Correction (2026-11-01).** Two statements above are inaccurate and are left
as written. `seaborn` is not used by `scripts/generate_phase_b_plots.py`:
nothing in the repository imports it, and the only dependency file that lists
it is `requirements.txt`. Clone installs are affected too: the README "Manual
install", `docs/development-workflow.md` §6 and `start_puma.sh` install from
pyproject (`pip install -e .` or `pip install -e ".[dev]"`), not from
`requirements.txt`; the Compose image (`Dockerfile`) and the `lint-and-test`
and `smoke` CI workflows install the requirements files.

### D49 — CI never runs `tests/community/` or `tests/cli/`, skips the mkdocs test and only installs pinned requirements (since S12-N2)

**Status:** OPEN — owner: maintainer. Target: v4.0.1 / patch sprint (own `ci/` PR).
**Discovered:** Post-v4.0.0 maintenance review (2026-10-31).

**Files.** `.github/workflows/lint-and-test.yml`, `.github/workflows/smoke.yml`,
`requirements-dev.txt`, `tests/integration/test_mkdocs_build.py`.

**Finding.** `lint-and-test.yml` runs `pytest tests/unit/` and
`pytest tests/integration/ -m "not ollama"`; `smoke.yml` runs `tests/smoke/`.
No workflow runs `tests/community/` (208 tests) or `tests/cli/` (23 tests);
both pass locally today. `tests/integration/test_mkdocs_build.py` calls
`pytest.importorskip("mkdocs")`, and `mkdocs` lives only in the `[docs]`
extra while the job installs the requirements files, so the test is skipped on
every CI run. Every job installs the pinned `requirements.txt`, so the
`PyGithub>=2.4,<3` range declared in `pyproject.toml` is never exercised; the
`get_rate_limit().core` regression fixed in PR #66 (PyGithub >= 2.7 returns a
`RateLimitOverview`) therefore passed CI and was found only by a local
`pip install -e ".[dev]"`.

**Consequence.** The community CLI, which produces the artefacts
`pumacp/puma-community` consumes, has no CI coverage; pip users resolve newer
dependency versions than CI ever tests.

**Resolution path.** One `ci/` PR (workflow changes are their own atomic PR per
the development workflow §3): add `pytest tests/community/ tests/cli/` to
`lint-and-test`; add a job that installs with `pip install -e ".[dev,docs]"`
(no pins) and runs `tests/community/`,
`tests/integration/test_share_results_fake_github.py` and
`tests/integration/test_mkdocs_build.py`, which also un-skips the mkdocs test.
Report the resolved PyGithub version in the job log.

### D50 — Version lookups query distribution `puma` instead of `puma-cp`; `0.0.0-unknown` everywhere (since S12.15)

**Status:** OPEN — owner: maintainer. Target: v4.0.1 / patch sprint (needs the
`runner.py` lock lifted).
**Discovered:** Post-v4.0.0 maintenance review (2026-10-31).

**Files.** `src/puma/ui/banner.py:28`, `src/puma/diagnostics/env.py:27`,
`src/puma/orchestrator/runner.py:718` (**locked** path),
`src/puma/__init__.py:7`.

**Finding.** All three sites call `importlib.metadata.version("puma")`. The
distribution has been named `puma-cp` since the S12.15 PyPI hardening, so the
lookup raises `PackageNotFoundError` and the fallback `0.0.0-unknown` is
returned in every install mode: editable clone, wheel and container image. It
surfaces in the banner, in `puma env` ("PUMA version 0.0.0-unknown") and in
`ProfileSnapshot.puma_version` of every run recorded since the rename. The
D26 resolution text describes this lookup as the dynamic version source.
`src/puma/__init__.py` still carries `__version__ = "2.0.0-dev"`, the stale
sentinel noted under RT3. The inaugural submission is **not** affected: the
builder resolves `puma_version` from `git describe --tags --abbrev=0` first,
which gave `3.1.0`, the latest tag on 2026-05-31 (`v4.0.0` was tagged on
2026-06-02); that published value is correct for its time and must not be
changed. The exposure is prospective: a pip user without a git checkout falls
through to the snapshot value `0.0.0-unknown`, which matches the schema's
semver pattern and would be published.

**Resolution path.** Query `version("puma-cp")` in the three sites (the
`runner.py` change needs the §3 lock-lift discussion; it does not touch
metrics), refresh or remove the `__init__.__version__` sentinel, and add a
unit test asserting the queried distribution name and the resolved value on an
installed wheel. Ship in v4.0.1.

### D51 — Minor hygiene findings: test artefacts in the checkout, deprecated license table, mypy on Python 3.12 (since v4.0.0)

**Status:** Items 1 and 3 RESOLVED in v4.0.1 (PR #70 and PR #69, merged to
`develop` 2026-10-31). Item 2 OPEN (low) — owner: maintainer. Target: next
maintenance pass, before 2027-02-18.
**Discovered:** Post-v4.0.0 maintenance review (2026-10-31).

**Finding and triage.**
1. *Tests write into the checkout (low).* `tests/unit/test_runner.py`,
   `tests/unit/test_runspec.py`, `tests/unit/test_profile_codecarbon_config.py`,
   `tests/integration/test_run_summary.py`,
   `tests/integration/test_runner_codecarbon.py`,
   `tests/integration/test_runner_retry_determinism.py` and
   `tests/integration/test_codecarbon_gpu_detection.py` leave run directories
   under `results/` and `data/cache/inferences.db` because
   `orchestrator/runner.py:29` (`RESULTS_ROOT = Path("results")`) and
   `runtime/cache.py:16` are cwd-relative. Gitignored, so `git status` stays
   clean, but every local run accumulates artefacts. Fix: an autouse fixture
   redirecting `RESULTS_ROOT` and the cache path to `tmp_path` for those
   modules.
2. *Deprecated license metadata (low now, build-breaking later).*
   `pyproject.toml:11` uses `license = { text = "MIT" }` plus the
   `License :: OSI Approved :: MIT License` classifier; setuptools warns on
   every build and announces removal of support on 2027-02-18. Fix:
   `license = "MIT"`, `license-files = ["LICENSE"]`, drop the classifier and
   require `setuptools>=77` in `[build-system]`;
   `tests/integration/test_publishing_workflows.py` only asserts the field is
   present.
3. *mypy error on Python 3.12 only (low).* `mypy src/puma/` passes on 3.11
   (CI) but on 3.12 reports `src/puma/metrics/calibration.py:36: Incompatible
   types in assignment (expression has type "complex128", variable has type
   "float")`, from the numpy stubs' typing of `mask.sum() / n`. The project
   declares `requires-python >= 3.11`. Fix: `float(mask.sum()) / n` (the module
   is under strict mypy but not a locked path).

**Resolution path.** Three small independent PRs (`test/`, `build/`, `fix/`),
none touching locked paths. Ship when convenient; item 2 before 2027-02.

**Resolution of item 1 (PR #70).** Commit `e98db3a`: an autouse fixture in
`tests/conftest.py` points `runner.RESULTS_ROOT` at `tmp_path` and redirects
relative `InferenceCache` paths there; absolute paths, as used by the cache
unit tests, are untouched. No `src/` change. After a full unit, community,
integration (`-m "not ollama"`) and smoke run, `git status --short --ignored`
shows no new entry under `results/` or `data/cache/`, and the test counts are
those of `develop` before the change.

**Resolution of item 3 (PR #69).** Commit `d24aeaa`:
`src/puma/metrics/calibration.py` computes `float(mask.sum()) / n`, so
`mypy src/puma/` passes on Python 3.11 and 3.12. The ECE value is unchanged
(bit-identical on 5000 random inputs).

Item 2 (license metadata) remains open.

### D52 — Erratum to D38: the proposed action tag `v1.3.0` does not exist (documentation)

**Status:** OPEN (documentation) — owner: maintainer. Target: v4.0.1 / patch sprint.
**Discovered:** Post-v4.0.0 maintenance review (2026-10-31).

**File.** This file — the **D38** entry (resolution path), left unchanged.

**Finding.** D38 proposes pinning `actions-ecosystem/action-add-labels` to
`@v1.3.0` "(latest stable)". No such tag exists; the latest release is
`v1.1.3` at commit `18f1af5e3544586314bbe15c0273249c770b2daf`.

**Resolution path.** Pin the action in `pumacp/puma-community`
`.github/workflows/validate-submission.yml` to that commit SHA (or `v1.1.3`).

### D53 — Erratum to D39: the instruction to re-run verification on the inaugural submission is withdrawn (documentation)

**Status:** OPEN (documentation) — owner: maintainer. Target: v4.0.1 / patch sprint.
**Discovered:** Post-v4.0.0 maintenance review (2026-10-31).

**File.** This file — the **D39** entry (resolution path), left unchanged.

**Finding.** D39 asks to re-run verification on the inaugural submission
"to upgrade its `verification_status`". That step is withdrawn: rewriting a
merged, mirrored submission conflicts with the historical integrity of the
corpus, and `"verified"` is not a value schema v1.0.0 defines for
`integrity.verification_status`. The `hf_token=` → `token=` repair of
`scripts/verify_submissions.py` stands; it applies to future submissions only.

**Resolution path.** Record only; no change to the inaugural submission.

### D54 — Erratum to D47: the leaderboard shows no rows because of a dataset load failure, not filtering (documentation)

**Status:** OPEN (documentation) — owner: maintainer. Target: v4.0.1 / patch sprint.
**Discovered:** Post-v4.0.0 maintenance review (2026-10-31).

**File.** This file — the **D47** entry, left unchanged.

**Finding.** D47 corrects D39 by stating the row "is shown with '—', not
hidden". That is also inaccurate: the deployed leaderboard Space shows no rows
at all because loading the submissions dataset fails, so neither filtering
(D39) nor the verification column (D46/D47) explains the empty table.

**Resolution path.** Fix the dataset load in the leaderboard Space
(`pumaproject/puma-leaderboard`), then re-check D46 and D47 against the live
page.

### D55 — Errata to `docs/first-submission.md` (documentation; original text unchanged)

**Status:** OPEN (documentation) — owner: maintainer. Target: v4.0.1 / patch sprint.
**Discovered:** Post-v4.0.0 maintenance review (2026-10-31).

**File.** `docs/first-submission.md`, delivered with v4.0.0 and left unchanged.

**Finding.** Four statements no longer hold:
- lines 68-69: the new row did not become visible on the leaderboard Space
  (see D54);
- lines 103-104: the proposed pin `@v1.3.0` does not exist (see D52);
- lines 108-109: `"verified"` is not a value schema v1.0.0 defines for
  `integrity.verification_status` (see D53);
- line 110: the `notify-discord` webhook secret existed; the workflow failed
  because the post itself failed, not for a missing secret.

**Resolution path.** Apply the four corrections in a docs PR that edits only
that page, citing this entry.

### D56 — Erratum to D23: the Verifier no longer emits the `sha256:` prefix (documentation)

**Status:** OPEN (documentation) — owner: maintainer. Target: v4.0.1 / patch sprint.
**Discovered:** Post-v4.0.0 maintenance review (2026-10-31).

**File.** This file — the **D23** entry (description, blocker 2 and open
decision (b)), left unchanged apart from the appended Decision paragraph.

**Finding.** D23 still describes the Verifier Space as emitting
`sha256:<hex>`. The prefix was removed in the Verifier at commit `d8a4ffd`
(as the v3.1.0 release notes record), so blocker 2 and open decision (b) of
D23 are moot; the remaining difference is the 2-field versus 4-field input,
settled by the Decision paragraph above.

**Resolution path.** Record only; D23 closes with the pending implementation.

### D57 — Erratum to `pumacp/puma-community` docs: automatic merging is described but does not happen (documentation)

**Status:** OPEN (documentation) — owner: maintainer. Target: v4.0.1 / patch sprint.
**Discovered:** Post-v4.0.0 maintenance review (2026-10-31).

**Files.** In `pumacp/puma-community`: `docs/maintainer-guide.md:78-84`,
`wiki/Validation-Process.md:38`, `wiki/FAQ.md:18-20`.

**Finding.** The three passages state that `auto-merge-valid.yml` merges a
submission PR automatically once it is labelled `valid`. In practice no
submission has been merged that way: the inaugural submission (PR #8) was
merged by hand with an admin bypass, as `docs/first-submission.md` records,
and the validation workflow that applies the label fails before labelling
(D38).

**Resolution path.** Correct the three passages in `pumacp/puma-community`
once D38 is fixed and the label-to-merge path has been exercised on a real
submission; until then describe the maintainer-driven merge as the current
path.

**Update (2026-11-01).** Two related `pumacp/puma-community` PRs are merged:
PR #3 (`1ee1376`) grants `wiki-sync.yml` `contents: write` so the wiki push
can succeed, and PR #14 (`224c4a8`) points the Hugging Face dataset references
in `README.md`, `docs/mirrors-setup.md` and three `wiki/` pages at
`pumaproject/puma-community-submissions`. The published wiki pages change
only when the maintainer dispatches `wiki-sync`. The three passages named
above are unchanged.

### P1 captures (Sprint 12)

Coordinator-level prompt-drift captures. Earlier captures are embedded in the
debt entry they relate to (P1-S12.7b-COORD-01 in D29; P1-S12.9-COORD-01 in
D30); later captures are collected here.

#### P1-S12.9-COORD-02 — Coordinator prompt over-strict MAE gate

Scope: the S12.9 prompt (and all prior phase prompts) specified "MAE = 5.7150
bit-exact" as a P2 invariant. The actual property that holds is "MAE = 5.7150
bit-exact WITHIN a warm Ollama session"; across container restarts, MAE can
drift > bit-exact tolerance without any code regression, as demonstrated by
D31's pristine-develop reproduction (three identical 6.3150 runs).

Detected by: executor's baseline re-validation with rigorous isolation in S12.9
(run #3 on pristine develop @ 6f09b2d reproduced 6.3150).

Resolution: from S12.10 onward, phase prompts specify the MAE gate as
"5.7150 ± 1.0" rather than "bit-exact 5.7150". Bit-exactness is reserved for
within-session re-validation only. F1 ± 0.01 unchanged.

Pattern: fourth coordinator-level prompt drift of Sprint 12 (P1-S12.2-COORD-01
nonexistent module, P1-S12.7b-COORD-01 hash-level gate, P1-S12.9-COORD-01
greenfield assumption, P1-S12.9-COORD-02 bit-exact assumption). All four share
the same upstream root cause: coordinator prompts over-asserting determinism in
an LLM-local stochastic system.

#### P1-S12.12-COORD-01 — Coordinator prompt assumed wrong CLI surface for share-results / verify-hash

Scope: the S12.12 prompt scripted `puma share-results --output-dir … --spec …`
and `puma verify-hash <file>` as if they were top-level subcommands with those
flag names. The actual CLI surface is:

- `puma share-results --dry-run --run-id <id> --yes` (output dir via env `PUMA_DRY_RUN_DIR`)
- `puma community verify-hash <submission> --predictions <jsonl>`
- run_id parsed from `puma run` stdout line: `Run complete: <run_id>`

Plus: no small demo spec existed in `specs/runs/`, so
`specs/runs/demo_publication.yaml` had to be created in-phase (the single
justified `specs/runs/` exception per the S12.12 prompt).

Detected by: executor's discovery pass (read `share_cli.py` + `verify_cli.py`
before scripting the demo).

Resolution: prompt-time assumptions corrected in-place via the executor's
discovery → adapt loop; demo script and tests use the real surface. Future
Sprint 12 prompts that wire existing CLI commands must REQUIRE a discovery step
before scripting flags (already the pattern; reinforce in the next phases).

Pattern: fifth coordinator-level prompt drift of Sprint 12 (P1-S12.2-COORD-01
nonexistent module, P1-S12.7b-COORD-01 hash-level gate, P1-S12.9-COORD-01
greenfield assumption, P1-S12.9-COORD-02 bit-exact MAE assumption,
P1-S12.12-COORD-01 CLI surface assumption). Root cause across all five:
coordinator (chat-side) prompts under-grounded in current repo state; mitigated
each time by the executor's audit-before-write discipline.

#### P1-S12.13-COORD-01 — Coordinator prompt assumed wrong auth surface

Scope: the S12.13 prompt asked for a `puma auth whoami` username read and an
`authenticated_as: str | None` field populated with the local GitHub username.
The actual auth surface is `puma auth login/status/logout` with token-only
storage at `~/.config/puma/credentials.toml`; there is no `whoami` and no
locally-cached username (resolving the username would require api.github.com,
which is forbidden this phase).

Detected by: executor's discovery pass on src/puma/community/_community_app.py
and the auth module before scripting status.

Resolution: implemented `authenticated = local-credential-presence-check` (no
HTTP), `authenticated_as = None` always (with a doc note explaining why). The
status renderer shows "✓ authenticated" without a username — accurate to what
the local state can determine without network.

Pattern: sixth coordinator-level prompt drift of Sprint 12 (P1-S12.2-COORD-01,
P1-S12.7b-COORD-01, P1-S12.9-COORD-01, P1-S12.9-COORD-02, P1-S12.12-COORD-01,
P1-S12.13-COORD-01). All six share the same upstream root cause: coordinator
(chat-side) prompts under-grounded in current repo surface state; mitigated each
time by the executor's audit-before-write discipline.

## Resolved technical debt

Items previously tracked as open technical debt that have been fully
resolved, with the resolution and supporting evidence preserved here
for academic traceability. Sprint 1 closures remain inline in the
"Open technical debt" tables above with strikethrough notation; the
following entries document the more involved resolutions from Sprint 2
onward, where the fix touched multiple files and had measurable
empirical impact.

### D27 — Predictions JSONL exporter missing in `share-results` (since v3.0.0)

**Status:** RESOLVED in v4.0.0 (Sprint 12 S12.2).
**Discovered:** Sprint 12 S12.1 (2026-05-25), while implementing the E2E
publication test — `share-results --dry-run` emitted only the submission JSON,
so the `<id>.predictions.jsonl` that `puma community verify-hash` and
`validate --strict` consume had no producer. The S12.1 E2E test worked around
this by exporting the JSONL directly from the database via `integrity._COLUMNS`.

**Resolution.** Commit `7a753b9` — `integrity.export_predictions_jsonl` writes
the predictions JSONL using the existing 4-field canonical column list
(`integrity._COLUMNS`: `instance_id`, `predicted_label`, `predicted_value`,
`prompt_hash`), and `share-results --dry-run` now emits
`<submission_id>.predictions.jsonl` next to `<submission_id>.json`. Because
`verify_cli.hash_predictions_jsonl` is byte-identical to
`compute_predictions_hash` for that 4-field format, the on-disk JSONL hashes to
the value the submission declares — verified by the smoke check
(`verify-hash` → `verified`), by `tests/unit/test_predictions_exporter.py`
(the byte-equality contract test), and by the refactored E2E test (`0617a16`),
which now consumes the real artifact instead of the DB stand-in.

**Scope note.** This is a productizing step with no change to the hash
semantics, the schema, or the Verifier. It is deliberately decoupled from D23
(Verifier 2-field alignment): the 4-field format is the existing canonical that
both `compute_predictions_hash` and `hash_predictions_jsonl` already share. If
D23's eventual schema decision selects a different canonical format, the
exporter updates atomically with that change. The live-publish path
(`raw_predictions_url` upload) is not wired here; it belongs to the live
publication demo (S12.12) alongside the D23 resolution.

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
