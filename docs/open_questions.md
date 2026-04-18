# Open Questions

Design decisions taken during implementation that were not explicitly specified, documented here for review.

---

## Resolved

### Q1 — Response parsing fallback policy

**Question**: When a model does not follow the output format, should the prediction be (a) excluded (`None`), (b) assigned an "unknown" class, or (c) retried?

**Decision**: Return `None` and exclude from metric computation. The `parse_failure_rate` metric tracks this separately.

**Rationale**: Assigning "unknown" would pollute F1 and accuracy with a synthetic class. Retries were not implemented to keep inference time predictable. The `parse_failure_rate` metric makes parse failures visible without distorting task metrics.

---

### Q2 — pytest.ini vs pyproject.toml

**Question**: Both `pytest.ini` and `[tool.pytest.ini_options]` in `pyproject.toml` exist. Which takes precedence?

**Decision**: `pytest.ini` is kept as the canonical config because the Docker Python 3.11 environment resolves it preferentially over `pyproject.toml`.

**Resolution**: Both files are kept in sync manually. `pytest.ini` is the authoritative source.

---

### Q3 — Prompt language

**Question**: Should prompts be in English or Spanish?

**Decision**: All prompts are in English. The Jinja2 templates in `specs/prompts/` use English. Legacy `src/evaluate_*.py` files (pre-v2) used Spanish prompts but are excluded from the active pipeline.

---

### Q4 — TAWOS SQL parsing

**Question**: The `db/TAWOS.sql` file is 4.3 GB with 1 004 INSERT batches. Runtime parsing is impractical.

**Decision**: Use `data/tawos_clean.csv` (9 020 rows, pre-processed) as the canonical runtime artifact. The SQL file is kept as a source-of-truth reference. A one-time conversion script can regenerate the CSV.

---

### Q5 — OllamaClient sync vs async

**Question**: The `Runner` orchestration loop uses `generate_sync()`. Should it use `async generate()`?

**Decision**: Sync is used to avoid event-loop complexity in the sequential orchestration loop. The async variant is implemented and available for future parallel batch execution.

---

### Q6 — Inference cache invalidation

**Question**: When a model is updated (new weights pulled for the same tag), cached responses may be stale.

**Decision**: Cache keys include `(model_tag, prompt_hash, temperature, seed)` but not a model version hash (Ollama does not expose one in the API). Users must run `puma cache clear` after pulling a model update.

**Status**: Acceptable for v2.0.0. A future improvement would query the model digest from `ollama show <model>` and include it in the cache key.

---

## Open (unresolved)

### Q7 — Optimal sample size per scenario on `cpu-standard`

**Question**: What sample size gives statistically reliable F1 estimates within the 30-minute gate time on `cpu-standard`?

**Observation**: With `qwen2.5:3b` and `zero-shot`, 50 instances takes ~8–12 minutes on cpu-standard. A 200-instance run would take ~30–45 minutes — above the gate limit for two models.

**Proposed answer**: 50 instances per model per strategy for the gate run; 200 instances for publication-quality results.

**Status**: Needs empirical validation on a cpu-standard machine.

---

### Q8 — Model warm-up

**Question**: Should the first inference call be discarded (warm-up round)?

**Observation**: The first call to a freshly loaded model includes the model load time (`load_duration_ns` in the Ollama response). Subsequent calls are faster.

**Current behaviour**: All calls are included in latency metrics. The `parse_ollama_timings()` function exposes `load_ms` separately so downstream analysis can distinguish cold vs warm calls.

**Proposed answer**: Expose `is_warm` flag in the prediction row and compute separate latency distributions. Not yet implemented.

---

### Q9 — Logprob support detection in preflight

**Question**: Ollama ≥ 0.12.11 is required for logprob extraction. Should `puma preflight` block runs with `logprobs: true` on older versions?

**Current behaviour**: If logprobs are requested but not supported, Ollama returns an empty logprobs field. The calibration metrics are then skipped (no data).

**Proposed improvement**: Add a preflight check that compares `ollama_version` against `0.12.11` and emits an `ERROR` severity issue when `logprobs: true` is requested on an incompatible version.

**Status**: Not yet implemented in `puma.preflight.provisioning`.
