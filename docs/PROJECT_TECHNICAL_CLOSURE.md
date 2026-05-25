# Project technical state — closure at v2.7.0

This document formalises the closure of the PUMA project's planned
technical implementation scope for the project release cycle.

## Releases published (8)

  v2.0.0 — Foundations (Phase A complete)
  v2.1.0 — Multi-model sweep (Phase B complete)
  v2.2.0 — Phase E (workflow consolidation)
  v2.3.0 — Professional dashboard (Phase C complete)
  v2.4.0 — Sprint 7 CLI completeness
  v2.5.0 — Sprint 8 hardening (I5-I10)
  v2.6.0 — Sprint 9 Apple Silicon M3/M4/M5 detection + native mode
  v2.7.0 — Sprint 10 catalog expansion (Qwen3 dense + MoE) +
           Kimi K2.6 formal exclusion

## Quality metrics at closure

  Tests passing                  407 (-m "not ollama") + 7 ollama-marked
  Coverage                       61 % (breakdown in docs/TESTING.md)
  Catalog entries                17 across 5 NVIDIA/CPU + 9 Apple
                                 Silicon profiles
  Reproducibility                Bit-exact dual (F1 triage + MAE
                                 estimation under T=0.0 + seed=42)
  CI                             Green on main and develop
  pre-commit                     10/10 clean across 114 files

## Defensive invariants enforced by tests

  1. test_gemma4_family_excluded_from_gpu_entry
     Source: D18/F8 (Sprint 5 empirical evidence)
     Test added: Sprint 5

  2. test_gemma4_family_not_compatible_with_any_apple_silicon
     Source: P6 generalisation of D18/F8 to Apple Silicon
     Test added: Sprint 9

  3. test_qwen3_entries_excluded_from_gpu_entry
     test_qwen3_entries_excluded_from_all_apple_silicon
     test_qwen3_entries_target_gpu_high_only
     Source: P10/P11 — pending-validation entries cannot be
             marked compatible with profiles where validation
             would be impossible
     Tests added: Sprint 10

## Open hypotheses (formalised)

The following hypotheses are formally documented in
docs/CROSS_ARCH_REPRODUCIBILITY.md and constitute publishable
future empirical work when validation hardware becomes available:

  H0 — F1 (triage_jira) is bit-exact between x86_64 (Linux + NVIDIA)
       and arm64 (macOS native + Metal) under the canonical protocol
       (T=0.0, seed=42, same model digest).

  H1 — MAE (estimation_tawos) is bit-exact between architectures
       under the canonical protocol.

  H2 — Logprobs distributions are equivalent (within statistical
       tolerance) between architectures.

  H3 — ECE values are within ±0.01 between architectures.

The 6-step testing protocol for closing H0-H3 is documented.

## Empirical validation pending (post-release work)

The following infrastructure is shipped in v2.7.0 awaiting hardware
for empirical validation:

  - Apple Silicon (9 profiles): MacBook Pro M4/M5 family
  - Qwen3 dense (qwen3:30b): gpu-high NVIDIA 24+ GB VRAM
  - Qwen3 MoE (qwen3:30b-a3b): gpu-high NVIDIA 24+ GB VRAM

Validation protocols are documented in docs/CROSS_ARCH_REPRODUCIBILITY.md
and docs/CATALOG_HISTORY.md (v2.7.0 section).

## Methodology preserved across the full release sequence

  - Wilcoxon signed-rank (Demšar 2006) for paired comparisons
  - Expected Calibration Error (Guo et al. 2017) with logprobs
  - Fairness evaluation under perturbations (Caliskan et al. 2017,
    Bolukbasi et al. 2016, Tatman 2017)
  - CodeCarbon sustainability tracking with platform-aware
    tracking_mode (Linux machine mode unchanged; macOS process-mode
    fallback when powermetrics lacks sudo)

No methodological assumption was altered across Sprints 6-10.
Reproducibility gates F1=0.5867 and MAE=5.7150 are stable across
4 consecutive releases (v2.4.0, v2.5.0, v2.6.0, v2.7.0).

## Formally excluded from v2.7.0 catalog

  - Kimi K2.6 (Moonshot AI, 2026-04-20, Modified MIT, 1T MoE):
    not distributed via Ollama registry as of v2.7.0 cut. 13 tag
    namings probed via registry.ollama.ai manifest endpoint,
    all returned HTTP 404. Exclusion documented in
    docs/CATALOG_HISTORY.md v2.7.0 section. Reconsideration in a
    future release contingent on upstream distribution.

## Deferred to future Sprints

The following were considered within scope but explicitly deferred:

  - qwen3:32b (dense, 18.8 GB GGUF, exists on Ollama): empirical
    validation deferred to gpu-high hardware availability
  - qwen3:235b-a22b (MoE, 132.4 GB GGUF, exists on Ollama):
    requires multi-GPU rigs >> 80 GB VRAM
  - qwen3-coder:30b / qwen3-coder:480b: specialised coding
    variants, scope discipline
  - Multi-language scenario variants (ES/DE/FR/ZH): 2-3 weeks
    effort, future work paper opportunity
  - REST API (FastAPI): 2 weeks effort, post-release
  - Jira/Linear/GitHub Issues connectors: Tier 3 vision

## Rationale for closure at v2.7.0

The originally-planned multi-Sprint scope (Sprint 8 hardening +
Sprint 9 Apple Silicon + Sprint 10 catalog expansion) is complete.
Every quality gate passes. Every defensive invariant is enforced
by tests. No closed findings have been reopened. The empirical
reproducibility contract (F1 + MAE bit-exact) is stable across
the four most recent releases.

Further technical work would introduce risk of regression on 407
passing tests without empirical contrapartida on the validation
hardware available to the project. The marginal value of further
infrastructure work is now exceeded by the marginal value of documentation
finalization for the project release cycle.

The project is prepared for empirical extension when hardware
becomes available. Future Sprints will close H0-H3 hypotheses and
validate the catalogued models empirically. These constitute
post-release work outside the project scope.
