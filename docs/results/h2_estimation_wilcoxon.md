# H2 — Inferential test for story-point estimation (Wilcoxon signed-rank)

> **Decision: FAIL TO REJECT H0_2** (Wilcoxon signed-rank, two-sided, α = 0.05).
> Best config `qwen2.5:7b` MAE = **1.86 SP** vs historical-mean baseline **2.03 SP**,
> reduction **0.17 SP** (below the 0.5 SP practical-relevance threshold),
> p = **0.104**, r = **−0.16**, N = **100**.

This document records the inferential test for hypothesis **H2** on the
`estimation_tawos` scenario, with per-prediction data preserved so the result is
independently recomputable. It is a **data-availability-limited** analysis; see the
**Limitations** section and debt item **D44** before citing.

## Pre-registered hypothesis (verbatim, not altered)

- **H0_2:** no enriched-instruction config achieves MAE lower than the project's
  historical-mean predictor on TAWOS (all differences = random variation;
  Wilcoxon two-sided, α = 0.05).
- **H1_2:** at least one config achieves statistically lower MAE (p < 0.05), with an
  absolute reduction **≥ 0.5 SP** as the practical-relevance threshold.

## Protocol

| Parameter | Value |
|---|---|
| Scenario | `estimation_tawos` (story-point regression, Fibonacci labels) |
| Strategy | `contextual-anchoring` |
| Seed / Temperature | 42 / 0.0 |
| N (per model) | 100 (disjoint samples; 0 instance overlap) |
| Models | `qwen2.5:7b` (best reproducible config), `qwen2.5:3b` (continuity with the report body) |
| Baseline predictor | **global historical-mean** story-point predictor — a constant = **4.0390 SP** (mean of 9,020 `story_points` in `data/tawos_clean.csv`) |
| Test | Wilcoxon signed-rank, two-sided, α = 0.05, on paired per-instance **absolute errors** `|ŷ − y|` (model vs baseline), `zero_method="wilcox"`, normal approximation with continuity correction |
| Effect size | r = Z / √N |
| Interval | 95 % percentile bootstrap CI of the MAE delta (baseline − model), n = 1000, seed = 42 |
| Multiplicity | Holm–Bonferroni across the 2 contrasts |
| Hardware | `gpu-entry`: NVIDIA GeForce RTX 2060, x86_64 Linux, 31.16 GB RAM |

### Baseline definition

The historical-mean predictor outputs a single constant for every instance: the
mean of all numeric `story_points` in the cleaned TAWOS corpus
(`data/tawos_clean.csv`, n = 9,020) → **4.0390 SP**. Its absolute error on an
instance is `|4.0390 − y_true|`. Because TAWOS story points are long-tailed
(median = 3.0), this trivial predictor is a surprisingly strong MAE baseline.

## Results

| Model | N | MAE model | MAE baseline | Δ MAE (base − model) | n_pairs | ties | W | Z | p (raw) | p (Holm) | r | 95 % boot CI (Δ) | Satisfies H1_2? |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|
| **qwen2.5:7b** | 100 | **1.860** | 2.0255 | **+0.165** | 100 | 0 | 2077.0 | −1.6275 | 0.10364 | 0.10364 | −0.163 | [−0.105, +0.409] | **No** |
| qwen2.5:3b | 100 | 2.910 | 2.0255 | −0.885 | 100 | 0 | 1518.0 | −3.5332 | 0.00041 | 0.00082 | −0.353 | [−1.357, −0.448] | **No** |

## H2 decision (falsifiable form)

**FAIL TO REJECT H0_2.** No enriched-instruction config achieves a statistically
significant **MAE** reduction of ≥ 0.5 SP versus the historical-mean predictor:

- **qwen2.5:7b** reduces MAE by only **0.17 SP** — below the 0.5 SP threshold — and
  the reduction is **not statistically significant** (p = 0.104; the 95 % bootstrap
  CI of the MAE delta, [−0.105, +0.409], spans zero).
- **qwen2.5:3b** has a **higher** MAE than the baseline (−0.885 SP, i.e. worse), so
  it cannot satisfy H1_2 regardless of significance.

## Methodological finding: mean vs. median disagree on the long tail

`qwen2.5:3b` produces a **significant** Wilcoxon result (raw p = 0.00041, Holm
p = 0.00082) — but in the **per-instance rank** sense, *and its MAE is worse*.
This is not a contradiction: TAWOS is long-tailed. The model predicts the many
low-SP tickets accurately (small absolute error, so it wins the rank comparison on
most instances), but it makes rare catastrophic misses on high-SP tickets
(e.g. predicting a small Fibonacci value where the gold is 21/34/55), and those
few large errors dominate the **mean** (MAE). The constant-4.0390 predictor never
makes a catastrophic miss, so it wins on the **mean** while losing on the median.

Because **H2 is pre-registered on MAE**, the rank-significant-but-MAE-worse outcome
for `qwen2.5:3b` does **not** satisfy H1_2. The broader lesson — that a trivial
mean predictor is a strong MAE baseline on long-tailed story-point data, and that
aggregate MAE and rank-based significance can disagree — is the substantive
finding here.

## Limitations (deviations from pre-registration)

This analysis is **data-availability-limited**. Four deviations are tracked as debt
item **D44** (closure path), cross-referencing **D22**:

1. **Global-mean, not per-project-mean, baseline.** The pre-registration names the
   *per-project* historical mean. The evaluated `instances` rows persist only a
   hashed id and the gold label — `input_text` and any project identifier are
   **empty** (existing debt **D22**), so instances cannot be mapped back to their
   TAWOS project. Only a **global** mean is computable here.
2. **N = 100, not N = 200.** This is the only `contextual-anchoring` estimation data
   that exists at per-prediction granularity; the N = 200 canonical estimation
   baseline (MAE = 5.7150) was run under `zero-shot`, a different strategy.
3. **Preserved data, not a fresh live run.** The predictions come from the
   May-10 Phase-B sweep (canonical seed = 42, T = 0.0, `contextual-anchoring`),
   read-only, because Ollama/Docker were unavailable in the analysis environment.
4. **No run-twice determinism re-check.** That requires live inference. The
   underlying run used seed = 42 / T = 0.0, and **this computation is fully
   deterministic** (fixed bootstrap seed) and re-runnable from the committed db.

Model digests were **not recorded** in the source run (`ollama_version` is null);
the runs are pinned instead by model tag + `spec_hash` + `run_id` (see the db
`meta` table).

## Reproduction

The committed db `data/puma_h2_estimation.db` is **self-contained** — the 200
paired rows (`paired_predictions`) and the computed `h2_results` are stored, so the
test recomputes from the db alone:

```bash
python -m venv /tmp/venv && /tmp/venv/bin/pip install numpy scipy
/tmp/venv/bin/python - <<'PY'
import sqlite3, numpy as np
from scipy import stats
c = sqlite3.connect("file:data/puma_h2_estimation.db?mode=ro", uri=True)
for (model,) in c.execute("SELECT DISTINCT model FROM paired_predictions"):
    rows = c.execute("SELECT ae_model, ae_baseline FROM paired_predictions WHERE model=?", (model,)).fetchall()
    ae_m = np.array([r[0] for r in rows]); ae_b = np.array([r[1] for r in rows])
    res = stats.wilcoxon(ae_m, ae_b, zero_method="wilcox", alternative="two-sided",
                         method="approx", correction=True)
    print(model, "MAE", round(ae_m.mean(),4), "vs", round(ae_b.mean(),4),
          "W", res.statistic, "Z", round(res.zstatistic,4), "p", round(res.pvalue,5))
PY
```

Stored provenance lives in the db `meta` table (source run ids, spec hashes,
baseline constant, hardware, generated date).

## Source

- Per-prediction source: `data/puma.db.may10-historical-backup` (untracked,
  read-only), runs
  `b3_sweep__qwen2_5_7b__estimation_tawos__ffe1372edf557f2d__20260510T125239` and
  `b3_sweep__qwen2_5_3b__estimation_tawos__7ef0f027d2a71504__20260510T124412`.
- Baseline corpus: `data/tawos_clean.csv` (`story_points`, n = 9,020).
- Aggregate cross-model context: `docs/results/phase_b_analysis.md`.
