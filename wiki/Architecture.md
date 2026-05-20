# Architecture

PUMA is built as a six-layer modular system designed for reproducibility,
swappability between models and strategies, and clear separation of concerns
between the inference path, the metrics path, and the storage path.

## The six layers

1. **Preflight** — hardware capability detection (CPU cores, RAM, GPU make and
   VRAM), automatic selection of one of five hardware profiles (`cpu-lite`
   through `gpu-pro`), and pre-flight validation that the chosen model fits
   the chosen profile.
2. **Runtime** — the Ollama HTTP client with retry, timeout, and structured
   logging; a response cache keyed on (model, prompt, options) so repeated
   evaluations of the same instance never touch the GPU twice.
3. **Datasets** — readers for the Jira Social Repository balanced 200-issue
   triage set, the TAWOS multi-project story-point estimation set, and the
   prioritization pairwise dataset. Each reader is deterministic and seeded.
4. **Scenarios** — the abstract `Scenario` class plus three concrete
   implementations: `TriageJiraScenario`, `EstimationTawosScenario`, and
   `PrioritizationJiraScenario`. A scenario owns its dataset, parser, and
   ground-truth label.
5. **Adaptation** — the prompting strategies: `zero_shot`, `few_shot_3`,
   `few_shot_6`, `chain_of_thought`, `rcoif` (Role/Context/Objective/
   Instructions/Format), and `contextual_anchoring`. New strategies plug in
   via a registry.
6. **Metrics + Sustainability** — seven metric families (Accuracy, Calibration,
   Efficiency, Stability, Robustness, Fairness, Sustainability) computed from
   the predictions table, plus a CodeCarbon emissions wrapper that records
   energy and CO₂ for every run.

## Reproducibility guarantees

- Default `--seed 42` and `--temperature 0`. The same `puma run` invocation
  twice on the same hardware produces byte-identical predictions.
- Deterministic Ollama invocations (`options.seed`, `options.temperature` set
  at every request).
- Bi-temporal SQLite storage: every row records both the wall-clock time and
  the logical run version, so historical comparisons stay consistent even when
  the dataset is updated.
- The full run specification (scenario, model, strategy, instances, seed,
  hardware profile, PUMA version) is stored alongside the metrics so any
  result can be regenerated bit-for-bit.

## The data flow

```
  Preflight  ─►  Runtime  ─►  Scenario  ─►  Adaptation  ─►  Metrics
  (profile)     (Ollama)     (dataset +    (prompt        (7 families
                              parser)       template)      + CodeCarbon)
                                                                 │
                                                                 ▼
                                                              Storage
                                                              (SQLite)
                                                                 │
                                                                 ▼
                                                              Dashboard
                                                              (Streamlit)
```

Each layer is exercised end to end by the integration test suite, and each
boundary is documented with explicit data contracts in the source.
