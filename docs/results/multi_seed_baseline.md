# Multi-seed Baseline Validation (Sprint 3)

## Configuration

- Model: `qwen2.5:3b`
- Scenario: `triage_jira`
- Adaptation: `contextual-anchoring` (no perturbations)
- N instances: 200 (canonical balanced split)
- Temperature: 0.0 (greedy decoding)
- Seeds tested: {42, 123, 456}
- Hardware: see [`docs/HARDWARE.md`](../HARDWARE.md) (RTX 2060 Mobile,
  AC power, idle host)

## Results

| Seed | F1-macro | Accuracy | Parse failure rate | Duration (s) | Energy (Wh) | CO₂ (g) | ECE (15 bins) |
|-----:|---------:|---------:|-------------------:|-------------:|------------:|--------:|--------------:|
|   42 |   0.5831 |   0.5800 |              0.000 |        ~50.0 |       ~0.80 |  ~0.140 | 0.3895 |
|  123 |   0.5831 |   0.5800 |              0.000 |         50.2 |      0.8053 |  0.1402 | n/a    |
|  456 |   0.5831 |   0.5800 |              0.000 |         50.9 |      0.8385 |  0.1459 | n/a    |

> ECE was captured only on the seed=42 run (the
> `baseline_triage_with_logprobs_v1` spec, executed with
> `inference.logprobs=true`). Seeds 123 and 456 used the canonical
> `baseline_triage.yaml` spec which keeps `logprobs=false` to preserve
> bit-exact comparability with v2.0.0's reference. Replicating ECE
> across seeds would require enabling logprobs in those specs, which
> is left for future work; under temperature=0.0 the predicted
> classes are identical across seeds, so the ECE would only vary if
> the *underlying* logprob distribution itself were seed-dependent
> — it is not, on Ollama 0.21.0 + greedy decoding.

## Statistics

Under temperature=0.0 + `seed=42|123|456` the three runs produce
**identical** classification metrics (zero standard deviation across
seeds):

- Mean F1: **0.5831**
- Standard deviation: **0.0000**
- Coefficient of variation (F1): **0.00 %**
- Δ vs canonical v2.0.0 reference (F1=0.5867): **−0.0036** (within
  the ±0.01 tolerance recorded in
  `specs/runs/baseline_triage.yaml`)

Per-bin variability (where it exists) is concentrated in **runtime
metrics**:

- Duration (s): 50.2 vs 50.9 → ≤2 % run-to-run jitter, attributable to
  CPU/scheduler/disk noise on the host
- Energy (Wh): 0.8053 vs 0.8385 → ~4 % spread, consistent with the
  thermal observations from Phase B (see `docs/HARDWARE.md`,
  "sustained-load thermal behaviour")
- CO₂ (g): 0.1402 vs 0.1459 → tracks energy proportionally as
  expected on a fixed grid intensity

## Discussion

### Zero seed-induced variance under T=0.0 is the expected result

PUMA's canonical baseline uses `temperature=0.0` (greedy decoding).
Under greedy decoding the next-token argmax is deterministic given
the same prompt and the same model weights, regardless of the seed
value: the random number generator is never consulted in the
sampling step. This explains the bit-exact F1=0.5831 across three
distinct seed values.

This is a **methodologically important point** that the project's
documentation now makes explicit:

- The `±0.01` tolerance reported alongside the canonical baseline
  (F1=0.5867 ± 0.01) does **not** absorb seed variance (which is
  zero) — it absorbs *non-seed* sources of drift: warm-vs-cold cache,
  Ollama version updates, library minor-version drift, host thermal
  state. See `CHANGELOG.md` ([2.0.0] Empirically Characterized
  Reference Baseline) for the original cold-vs-warm characterisation.
- Multi-seed validation in PUMA is only informative when temperature
  is strictly greater than zero. The roadmap entry "Multi-seed
  validation with confidence intervals" (README.md, post-v2.1.0)
  therefore implicitly requires a temperature schedule (e.g. T=0.7
  with seeds {42, 123, 456, 789, 1024} for variance estimation
  on sampling-based strategies like `self-consistency`).

### What this exercise *does* close

This validation closes the limitation documented in
[`docs/results/phase_b_analysis.md`](phase_b_analysis.md) — *"Single
sweep iteration; multiple seeds for variance estimation pending"* — by
demonstrating, under the project's documented baseline configuration:

1. **Seed-variance is zero by construction** at T=0.0 (greedy
   decoding does not consume the RNG).
2. **Run-to-run jitter** is concentrated in **runtime** (≤4 %
   duration/energy spread), not in **task metrics** (0 % spread in
   F1, accuracy, parse failure rate).
3. The canonical baseline reference value remains within the
   declared ±0.01 tolerance band across the runs executed during
   Sprint 3 (current warm-state value: 0.5831; canonical reference:
   0.5867; Δ = −0.0036 < 0.01).

### What is left for future work

Multi-seed validation under temperature > 0 (sampling-based
strategies such as `self-consistency`) is a natural next step, and
the infrastructure here is reusable: copy the canonical spec, set
`temperature=0.7`, vary seed, repeat. ECE would also become
seed-sensitive in that regime because the logprob distribution feeds
into multinomial sampling.

## Reproducibility

```bash
# Seed-42 (canonical):
puma run specs/runs/baseline_triage.yaml

# Seed-42 with logprobs (captures ECE):
puma run specs/runs/baseline_triage_with_logprobs.yaml

# Seeds 123 and 456:
sed 's/seed: 42/seed: 123/' specs/runs/baseline_triage.yaml \
  > /tmp/baseline_seed_123.yaml
sed 's/seed: 42/seed: 456/' specs/runs/baseline_triage.yaml \
  > /tmp/baseline_seed_456.yaml
puma run /tmp/baseline_seed_123.yaml
puma run /tmp/baseline_seed_456.yaml
```

## References

- v2.0.0 CHANGELOG section "Empirically Characterized Reference
  Baseline" — cold-vs-warm drift characterisation, source of the
  ±0.01 tolerance band
- `docs/HARDWARE.md` — reference machine and reproducibility scope
- `docs/results/phase_b_analysis.md` — single-iteration sweep that
  this validation extends
