# PUMA sustainability tracking

PUMA records the energy use and estimated carbon emissions of every benchmark
run. This document explains why, how the measurement works, what the numbers
mean, and — just as important — what they do **not** mean.

## Why measure carbon

Running language models, even small local ones, consumes energy, and energy has
a carbon cost that varies by hardware and electrical grid. A benchmark that
reports only task accuracy hides half the trade-off: a model that is marginally
more accurate but several times more energy-hungry is not obviously the better
choice for a project-management office deciding what to deploy. Reporting energy
and carbon alongside F1 and MAE lets that trade-off be made explicitly. The case
for treating compute cost as a first-class metric in NLP evaluation was made by
Strubell et al. (2019); PUMA applies that principle at inference time for
PMO-oriented tasks.

## How PUMA measures

**Tracker.** PUMA uses [CodeCarbon](https://mlco2.github.io/codecarbon/) to
measure energy and estimate CO₂. The tracker version is captured per run
(`codecarbon_version`, e.g. `3.2.7` in the reference configuration). The
integration lives in `src/puma/orchestrator/runner.py` and
`src/puma/sustainability/codecarbon_wrapper.py`; the per-run figures are
persisted in the `emissions` table (`src/puma/storage/models.py`, the `Emission`
model) and surfaced in a submission's `sustainability` block
(`src/puma/community/schema.py`).

**Tracking mode.** The tracker runs in `tracking_mode = "machine"`. In PUMA's
split-container architecture the model runs in a separate Ollama container, so
whole-machine accounting attributes the GPU/CPU/RAM energy of the inference host
correctly; a process-scoped mode would miss the GPU work entirely (this was the
substance of the earlier GPU-attribution fix, D15).

**Coverage.** Since Sprint 12 (debt item D25), the canonical baseline specs ship
with `sustainability.codecarbon: true`, so **every** canonical run produces an
emissions record by default. Attribution is per-run, not per-instance: one
emissions row summarises the whole run.

**Country accounting.** `country_iso` defaults to `ESP` (Spain) for
reproducibility of the reference figures. It selects the grid carbon-intensity
factor CodeCarbon applies to convert energy into CO₂. Users running PUMA
elsewhere should override it to match their own grid; the energy figure
(`energy_kwh_total`) is grid-independent, only the CO₂ conversion changes.

**Hardware coverage.** PUMA defines five baseline hardware profiles in
`config/profiles.yaml`: `cpu-lite`, `cpu-standard`, `gpu-entry`, `gpu-mid`, and
`gpu-high` (plus Apple-Silicon variants, not covered here). All five were
verified **structurally** in Sprint 12 — each loads, declares no per-profile
codecarbon override (the settings are global, so measurement is identical across
profiles), and is accepted by the runner when requested via a spec. **Empirical**
measurement was performed on the host's auto-detected profile, `gpu-entry`;
live measurement on the other profiles awaits access to that hardware.

## What the numbers mean

A PUMA emissions record contains, in plain language:

- `energy_kwh_total` — total electrical energy the inference host drew during the
  run, in kilowatt-hours (sum of CPU, GPU, and RAM energy).
- `co2_grams_total` — that energy converted to grams of CO₂-equivalent using the
  configured country's grid intensity.
- `duration_s` — wall-clock seconds the tracker was active.
- `cpu_energy` / `gpu_energy` / `ram_energy` — the per-component breakdown; for
  GPU-bound runs `gpu_energy` dominates.

**Order of magnitude.** On the reference `gpu-entry` host, a 200-instance
canonical run observed:

| Run | `energy_kwh_total` | `co2_grams_total` | `duration_s` |
|-----|--------------------|-------------------|--------------|
| `baseline_triage` (qwen2.5:3b) | ~0.00065 kWh | ~0.11 g | ~43 s |
| `baseline_estimation_canonical` (qwen2.5:3b) | ~0.0012 kWh | ~0.21 g | ~54 s |

These are the values *in this configuration*; a different model, host, run
size, or country will produce different numbers. The useful takeaway is the
scale: a canonical PUMA baseline on a small local model costs a fraction of a
gram of CO₂ and well under a hundredth of a kWh — roughly the order of leaving a
laptop charger drawing for a minute. As a coarse sanity reference, a single kWh
on a typical European grid corresponds to a few hundred grams of CO₂-eq; our
observed ratio (sub-gram CO₂ for sub-milli-kWh energy) sits comfortably in that
range, which is one way to tell the tracker is producing sane output rather than
a stub.

## Limitations

PUMA measures a slice of the footprint, not the whole world. Specifically:

- **Single-machine scope.** The figures cover the inference host only. They
  exclude data-center overhead (PUE), networking, and the amortised cost of
  training the model — all of which can dwarf inference for a widely deployed
  model.
- **Country code is an approximation.** `country_iso` selects an average grid
  factor, not a real-time, location-specific marginal intensity.
- **Cache and warm-up effects.** The first run after a cold start has different
  energy and latency than later runs. PUMA's KV-cache-hygiene protocol (restart
  Ollama before each canonical baseline) exists to make runs *comparable across
  specs*, not to minimise energy; reported energy is therefore representative of
  a freshly-restarted server, not a steady-state one.
- **Estimation method.** CodeCarbon reads CPU energy via RAPL on supported Linux
  and falls back to a model-based estimate elsewhere; on hosts where RAPL is
  restricted or absent the CPU term may be under-attributed.
- **Self-attestation.** Emissions values in a published submission are reported
  by the runner that produced them. The community Verifier checks the integrity
  *hash* of the predictions, not the *accuracy* of the declared emissions — there
  is no independent re-measurement of energy.

## How to reproduce

The canonical specs that produce the reference figures are
`specs/runs/baseline_triage.yaml` and
`specs/runs/baseline_estimation_canonical.yaml`; both enable codecarbon by
default since Sprint 12. Re-run and validate them with:

```bash
puma validate-baseline --spec specs/runs/baseline_triage.yaml --expected-f1 0.5867
puma validate-baseline --spec specs/runs/baseline_estimation_canonical.yaml --expected-mae 5.7150
```

Each run writes an emissions row to the `emissions` table; `puma share-results
--dry-run` surfaces it in the submission's `sustainability` block.

## See also

- The `sustainability` block of the submission schema
  (`src/puma/community/schema_data/submission.v1.json`) and the `Sustainability`
  model in `src/puma/community/schema.py`.
- The `Emission` model docstring in `src/puma/storage/models.py`.
- `docs/sprints/Sprint-12-Closure.md` (when published) for the Sprint 12
  verification record.

---

*Reference note: this document cites Strubell et al. (2019) for the motivation
to treat inference compute as a reported metric. Broader carbon-accounting
references are informational here and are deferred to the final memoria
write-up, where they will be bibliographically anchored.*
