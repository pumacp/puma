# Cross-architecture reproducibility

## Open question

Are PUMA's task-level metrics (F1-macro, MAE) and per-token logprobs
**bit-exact** between x86_64 Linux (validation environment) and arm64
macOS (Apple Silicon, native mode) under PUMA's canonical configuration
(`T=0.0`, `seed=42`, same Ollama model digest)?

## Current status

**Empirically unverified as of v2.6.0.** The detection and dispatch
infrastructure to enable a future empirical test is in place:

- `puma.preflight.apple_silicon.detect_apple_silicon_profile` maps the
  10 catalogued M-series chip variants to `apple-silicon-*` profile
  identifiers.
- `config/profiles.yaml` declares all 9 apple-silicon-m3/m4/m5
  profiles with `empirical_validation: pending`.
- `start_puma.sh --native` boots a native Ollama (Metal accelerated)
  + Python venv on macOS, enabling Mode B end-to-end.
- `puma validate-baseline --expected-f1` and `--expected-mae` (from
  v2.5.0) can run unchanged on Mode B and produce comparable
  numbers to the Linux reference.

No empirical comparison has been performed — the project's validation
hardware (RTX 2060 Mobile 6 GB, `gpu-entry`) does not extend to Apple
Silicon.

## Theoretical expectations

| Metric | Expected behaviour | Confidence |
|---|---|---|
| `f1_macro` | Bit-exact (±0.000) across architectures | High |
| `mae` | Bit-exact (±0.0001) across architectures | High |
| Per-token logprobs | Differ by FP rounding (~1e-5 to 1e-3) | Medium |
| Per-prediction confidence (derived) | Differ marginally | Medium |
| `latency_p95` | Differ substantially (GPU class) | Certain |
| `co2_kg`, `kwh` | Differ substantially (hardware + tracker) | Certain |

### Why `f1` and `mae` are *expected* bit-exact

Q4_K_M quantisation (Ollama's default) performs inference in
quantised integer arithmetic at the matmul level. The token-id
sequence emitted by greedy decoding (`temperature=0.0`) is therefore
deterministic at the level of token equality, regardless of the
underlying SIMD instruction set (AVX2 on x86_64, NEON on arm64).
Both `f1_macro` and `mae` are computed from the parsed token output,
so they should agree bit-exactly when the same token sequence is
produced.

The triage parser maps the first valid label token to one of 5
classes; the estimation parser maps the first valid integer literal
to a story-point value. Neither parser depends on continuous
floating-point comparisons — only on token equality.

### Why logprobs are *expected* to differ

Logprobs are continuous floating-point values derived from the
softmax of the model's final-layer logits. Softmax includes
exponentiation and normalisation, both of which involve
floating-point arithmetic in `f32` or `f16` (depending on the
quantised path). Differences in instruction-level FP semantics
(AVX2 FMA vs NEON FMA, vendor-specific fast-math flags, kernel
choices in Metal Performance Shaders vs CUDA) can produce
non-identical bit patterns even when the model weights and inputs
are byte-identical.

**Implication**: ECE (Expected Calibration Error) — which is
computed from logprobs — may differ slightly between Linux and
macOS. The magnitude of the difference is the open empirical
question.

## Hypothesis for future empirical work

- **H0**: `f1_macro` and `mae` are bit-exact across architectures
  under `T=0.0` + `seed=42` + same model digest, on the canonical
  baselines.
- **H1**: At least one of `f1_macro` or `mae` differs by more than
  ±0.000 across architectures under the same configuration.

A secondary hypothesis on logprobs:

- **H2**: The mean absolute difference between paired logprobs
  (same instance, same prompt) across architectures is below 1e-3.
- **H3**: ECE differs by less than ±0.01 across architectures on
  the canonical triage baseline.

## Testing protocol when Mac hardware becomes available

1. Acquire / borrow a MacBook with one of the M-series variants
   catalogued in `config/profiles.yaml`. Note the chip brand exactly
   as `sysctl -n machdep.cpu.brand_string` reports it.
2. `brew install ollama` and verify the daemon starts.
3. Pull `qwen2.5:3b` natively (`ollama pull qwen2.5:3b`). Compare
   the digest against the Linux reference (`ollama show qwen2.5:3b`).
   If the digests differ, the comparison is invalidated — Ollama's
   distribution layer may serve different quantisations across
   architectures.
4. Clone PUMA, `./start_puma.sh --native`, and run:
   ```bash
   puma validate-baseline --expected-f1 0.5867 --tolerance 0.01
   puma validate-baseline \
     --spec specs/runs/baseline_estimation_canonical.yaml \
     --expected-mae 5.7150 --tolerance 0.05
   ```
5. Record:
   - `f1_macro` and `mae` (PASS/FAIL with delta).
   - `parse_failure_rate` (should be 0.0; non-zero is a
     parser-level cross-arch issue, not a deterministic-FP issue).
   - `puma list-runs --last-n 1 --json` to capture the exact run_id
     and timestamps.
6. Per-token logprob comparison (advanced):
   - Re-run both baselines with `inference.logprobs: true` in the
     spec.
   - Export `predictions.logprobs_json` from both DBs.
   - Compute mean absolute difference per token across paired
     instances.
   - Compute ECE on both runs and report the delta.

Results from this protocol close H0/H1 and partially close H2/H3.
File an issue or PR documenting the findings; if H0 holds, update
this document's status section to "empirically verified" and add
the Mac hardware row to `docs/HARDWARE.md`'s tolerance table.

## Implication for v2.6.0 users

Users running PUMA in macOS Mode B (native Ollama, Metal
accelerated) should NOT assume their F1/MAE results are directly
comparable to Linux baselines without first running the protocol
above on their specific hardware. The canonical Linux references
remain authoritative:

- triage_jira F1 = 0.5867 (qwen2.5:3b + contextual-anchoring, N=200)
- estimation_tawos MAE = 5.7150 SP (qwen2.5:3b + zero-shot, N=200)

A Mode B user who observes `f1 = 0.5867` is reproducing the result
exactly; a user who observes `f1 = 0.5712` should suspect either a
model-digest mismatch (verify with `ollama show`) or a genuine
cross-arch FP-ordering divergence (H1 holds for their specific
configuration). Either outcome is informative and would benefit the
project — please report it.

## Related documents

- [`MACOS_NOTES.md`](MACOS_NOTES.md) — Mode A vs Mode B operational
  notes.
- [`HARDWARE.md`](HARDWARE.md) — gpu-entry tolerance table; Apple
  Silicon row currently points back to this document.
- [`baseline_references.md`](baseline_references.md) — canonical
  empirical baselines for both scenarios.
- [`CATALOG_HISTORY.md`](CATALOG_HISTORY.md) — `catalog_version`
  2.6.0 entry documenting the apple-silicon-* additions.
