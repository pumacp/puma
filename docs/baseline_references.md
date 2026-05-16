# Canonical baseline references

This document records the **canonical empirical baselines** that
`puma validate-baseline` uses as its reference values. Each entry
fixes a `(scenario, model, strategy, N, seed, T)` configuration to a
single number (`F1-macro` for triage, `MAE` for estimation) measured
on PUMA's validation hardware (RTX 2060 Mobile 6 GB, `gpu-entry`
profile). Subsequent releases must reproduce these values within the
documented tolerance, otherwise `puma validate-baseline` exits
non-zero.

When a reference baseline is established or refreshed, the row in the
table below is updated, the `run_id` is recorded for traceability,
and the release notes for that version document the change explicitly.

## triage_jira

| Field | Value |
|---|---|
| Spec | `specs/runs/baseline_triage.yaml` |
| Scenario | `triage_jira` |
| Model | `qwen2.5:3b` |
| Strategy | `contextual-anchoring` |
| Sample size | 200 |
| Seed | 42 |
| Temperature | 0.0 |
| **Reference F1-macro** | **0.5867** |
| Tolerance | ±0.01 |
| Hardware | `gpu-entry` (RTX 2060 Mobile 6 GB) |
| Established | v2.0.0 |

Invocation:

```bash
puma validate-baseline
# or, equivalently:
puma validate-baseline --expected-f1 0.5867 --tolerance 0.01
```

## estimation_tawos

| Field | Value |
|---|---|
| Spec | `specs/runs/baseline_estimation_canonical.yaml` |
| Scenario | `estimation_tawos` |
| Model | `qwen2.5:3b` |
| Strategy | `zero-shot` |
| Sample size | 200 |
| Seed | 42 |
| Temperature | 0.0 |
| **Reference MAE** | **5.7150** SP |
| Tolerance | ±0.05 SP |
| Hardware | `gpu-entry` (RTX 2060 Mobile 6 GB) |
| Established | v2.5.0 |
| Establishing run | `baseline_estimation_canonical_v1__26d0e07aaa7949ec__20260516T003317` |
| Duration | 55.2 s |
| Parse failure rate | 0.0000 |

Auxiliary metrics from the establishing run: `mdae=4.0000`,
`rmse=8.0078`, `n_samples=200`.

Invocation:

```bash
# Recommended: restart Ollama first to guarantee a fresh model state.
docker compose restart puma_ollama
puma validate-baseline \
  --spec specs/runs/baseline_estimation_canonical.yaml \
  --expected-mae 5.7150 --tolerance 0.05
```

#### Protocol note — fresh Ollama state

Empirically (v2.5.0, four-run verification), MAE = 5.7150 is bit-exact
across cold-start and warm-state runs of the canonical estimation
baseline when the *only* recent activity is `estimation_tawos` itself.
A `triage_jira` run executed *between* an Ollama restart and the
estimation validation perturbs the model's KV-cache state and shifts
MAE to ≈ 6.3150 (delta = +0.6 SP) — a regression well outside the
±0.05 tolerance.

Validation runs should therefore be performed from a fresh Ollama
state. If both triage and estimation baselines need to be validated
in one session, restart `puma_ollama` between them, e.g.:

```bash
docker compose restart puma_ollama
puma validate-baseline  # F1 path, default triage spec
docker compose restart puma_ollama
puma validate-baseline \
  --spec specs/runs/baseline_estimation_canonical.yaml \
  --expected-mae 5.7150 --tolerance 0.05
```

The cross-scenario state contamination is a property of Ollama's
inference engine and is independent of PUMA's code path — see
`docs/known_debt.md` D3 for the broader CUDA non-determinism context.

### Why this differs from Phase B numbers

The Phase B analysis (`docs/results/phase_b_analysis.md`) reports
`qwen2.5:3b | estimation MAE | 2.91` on a smaller sample drawn from
the TAWOS dataset. The v2.5.0 reference (MAE = 5.7150 SP) uses
`N=200` and the canonical seed/temperature/strategy combination
fixed in `baseline_estimation_canonical.yaml`. The two numbers are
*not* directly comparable: TAWOS story-point distributions are
long-tailed, so MAE is sensitive to which specific instances are
sampled.

The v2.5.0 reference is the contract going forward. The Phase B
number remains historically valid as a cross-model comparison
within that sweep but is not used by `puma validate-baseline`.

## Tolerance philosophy

Under `T=0.0` + `seed=42` + a fixed model digest, both F1 and MAE
should be bit-exact reproducible in warm state on the same hardware.
The published tolerances (±0.01 for F1, ±0.05 for MAE) absorb the
known cold-vs-warm drift (≤ 0.006 for F1 per the D3 analysis) plus a
safety margin for floating-point ordering differences across
equivalent NVIDIA hardware (see `docs/HARDWARE.md` gpu-entry
tolerance table).

If `puma validate-baseline` returns FAIL with `delta` outside the
documented tolerance, the cause is typically one of:

1. A model version mismatch (run `ollama show qwen2.5:3b` and
   compare digest).
2. A non-determinism regression in the code path
   (`puma.scenarios`, `puma.metrics`, `puma.runtime`).
3. A hardware tier mismatch (e.g., running on CPU when the
   reference was established on `gpu-entry`).

See `docs/known_debt.md` for the live status of any open
reproducibility-related debt.

## Refreshing a reference

To refresh a reference baseline in a future release:

1. Run the canonical spec on the validation hardware in warm state.
2. Verify `parse_failure_rate = 0` and the run completes without
   errors.
3. Record the new `run_id` and value in this document.
4. Update the relevant default in `src/puma/cli.py` only if the
   change reflects an intentional methodology shift (e.g., changing
   the canonical strategy from zero-shot to contextual-anchoring
   for estimation). Otherwise, leave the CLI default as the
   user-facing reference and document the new value here.
5. Note the refresh in `CHANGELOG.md` and the release notes.
