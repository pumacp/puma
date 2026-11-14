# H1 — Inferential test for issue triage (Wilcoxon signed-rank)

> **Decision: REJECT H0_1** (Wilcoxon signed-rank, two-sided, α = 0.05).
> qwen2.5:3b + contextual-anchoring, F1-macro = **0.5894** (reference 0.5867) vs a
> no-information majority-class baseline (acc **0.25**, F1-macro **0.10**):
> Wilcoxon **p = 6.9 × 10⁻¹³**, r = **−0.51** (large), N = **200**.

This document records the inferential test for hypothesis **H1** on the
`triage_jira` scenario, computed on preserved per-instance predictions and
persisted so the test is independently recomputable. It contains a **deliberate
baseline substitution** (see Limitations / D45) made because the pre-registered
keyword-heuristic baseline is irrecoverable.

## Pre-registered hypothesis (spirit preserved)

- **H0_1:** no model/strategy config achieves correctness above the reference
  baseline on the Jira SR triage set (all differences = random variation;
  Wilcoxon two-sided, α = 0.05).
- **H1:** at least one config achieves statistically higher per-instance
  correctness than the baseline (p < 0.05), effect size r ≥ 0.1.

## Baseline definition (and the substitution)

The pre-registered baseline was a **keyword-rule heuristic**, which requires the
ticket text. The preserved `instances` rows have **empty `input_text` in 200/200
triage rows** (known debt **D22**), so that heuristic is **irrecoverable** and its
F1 cannot be recomputed.

Substituted baseline: the **no-information majority-class floor** — a constant
predictor computable from the preserved gold labels alone. The triage set is
**perfectly balanced** (Critical / Major / Minor / Trivial = 50 / 50 / 50 / 50),
so there is no true majority; any single constant class yields the same floor:

| Baseline | Accuracy | F1-macro |
|---|--:|--:|
| constant-class (`Critical`, deterministic tiebreak) | **0.2500** (= 1/k) | **0.1000** |

The baseline accuracy/F1 are invariant to which class is chosen; the choice only
fixes *which* 50 instances the baseline scores correct (used in the paired test).
The decision is robust to the tiebreak.

## Protocol

| Parameter | Value |
|---|---|
| Scenario / Model / Strategy | `triage_jira` / `qwen2.5:3b` / `contextual-anchoring` |
| Seed / Temperature | 42 / 0.0 |
| N | 200 (canonical preserved set) |
| Source run | `baseline_triage_v1__1a2adeb0e829e30b__20260510T154911` (spec_hash `1a2adeb0e829e30b`) — one of 5 byte-identical N=200 runs (F1 = 0.5894); one earlier run F1 = 0.5831; reference 0.5867 ± 0.01 |
| Test | Wilcoxon signed-rank, two-sided, α = 0.05, on paired per-instance **correctness** (1 = exact-class match, 0 otherwise), `zero_method="wilcox"`, normal approx + continuity correction |
| Effect size | r = Z / √N |
| Interval | 95 % percentile bootstrap CI (n = 1000, seed = 42) for the accuracy and F1-macro deltas |
| Hardware | `gpu-entry`: NVIDIA GeForce RTX 2060, x86_64 Linux, 31.16 GB RAM |

## Results

| Metric | Model (qwen2.5:3b + CA) | Baseline (constant-class) | Δ (model − base) |
|---|--:|--:|--:|
| Accuracy | 0.5850 | 0.2500 | **+0.3350** |
| F1-macro | 0.5894 | 0.1000 | **+0.4894** |

| Wilcoxon (paired correctness) | n_pairs | ties | W | Z | p (two-sided) | r |
|---|--:|--:|--:|--:|--:|--:|
| model vs constant-class | 87 | 113 | 440.0 | −7.1807 | **6.9 × 10⁻¹³** | −0.5078 |

Paired-disagreement composition: model-only-correct = 77, baseline-only-correct =
10, both-correct = 40, both-wrong = 73 (113 ties = both-correct + both-wrong).

95 % bootstrap CI (n = 1000, seed = 42): accuracy delta **[+0.2550, +0.4151]**;
F1-macro delta **[+0.4135, +0.5595]** — both exclude 0.

## H1 decision (falsifiable form)

**REJECT H0_1.** qwen2.5:3b + contextual-anchoring achieves statistically higher
per-instance correctness than the no-information baseline: p = 6.9 × 10⁻¹³ ≪ 0.05,
effect size |r| = 0.51 (large), and both bootstrap CIs exclude zero.

## Honest caveat on the bar

On a perfectly balanced 4-class set the majority-class floor is the **weakest
possible** comparator (25 % accuracy). Beating it is a low bar; the large effect
here is unambiguous but says only that the model is far above chance — **not** that
it beats a competitive heuristic. The pre-registered keyword heuristic (a stronger,
more meaningful comparator) remains irrecoverable until `input_text` is re-ingested
(D22 → D45).

## Strategy contrast (descriptive, not inferential)

| Strategy | F1-macro | Source |
|---|--:|---|
| contextual-anchoring (N=200) | 0.5867 ref / 0.5894 observed | preserved run / `specs/runs/baseline_triage.yaml` |
| zero-shot (N=200) | 0.3898 | tracked `data/puma.db` (v4.0.0 inaugural submission) |

## Limitations (deviations from pre-registration) — tracked as D45

1. **Baseline substitution** — keyword heuristic → no-information majority-class
   floor, because `input_text` is empty (**D22**).
2. **Preserved May-10 data, not a fresh live run** — Ollama/Docker unavailable here.
3. **No run-twice re-check** — requires live inference (underlying run seed=42/T=0.0;
   the 5 stable runs are byte-identical; this computation is deterministic).
4. **Model digest not recorded** (`ollama_version` null); pinned by model tag +
   `spec_hash` + `run_id`.

## Reproduction

`data/puma_h1_triage.db` is self-contained (200 paired rows + `h1_results` +
`meta`); the test recomputes from the db alone:

```bash
python -m venv /tmp/venv && /tmp/venv/bin/pip install numpy scipy
/tmp/venv/bin/python - <<'PY'
import sqlite3, numpy as np
from scipy import stats
c = sqlite3.connect("file:data/puma_h1_triage.db?mode=ro", uri=True)
rows = c.execute("SELECT model_correct, baseline_correct FROM paired_predictions").fetchall()
m = np.array([r[0] for r in rows]); b = np.array([r[1] for r in rows])
res = stats.wilcoxon(m, b, zero_method="wilcox", alternative="two-sided", method="approx", correction=True)
print("acc", m.mean(), "vs", b.mean(), "W", res.statistic, "Z", round(res.zstatistic,4), "p", res.pvalue)
PY
```

## Source

- Per-instance predictions: `data/puma.db.may10-historical-backup` (untracked,
  read-only), run `baseline_triage_v1__1a2adeb0e829e30b__20260510T154911`.
- Reference F1: `specs/runs/baseline_triage.yaml`. Cross-context: `docs/results/phase_b_analysis.md`.
- Companion estimation test: `docs/results/h2_estimation_wilcoxon.md` (D44).
