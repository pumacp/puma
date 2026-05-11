# Wilcoxon Signed-Rank Pairwise Model Comparison (Sprint 3)

## Methodology

For each scenario, the top-K performers (by F1-macro for
classification, by MAE for regression) are compared pairwise using
the Wilcoxon signed-rank test (Wilcoxon 1945) on **paired correctness
indicators**: for every instance evaluated by *both* models we encode
each model's prediction as 1 (correct) or 0 (incorrect) and feed the
paired sequence to `scipy.stats.wilcoxon`. Pairs with identical
correctness (both right or both wrong) are ties and are dropped per
the standard "wilcox" zero-handling rule.

The test answers the question *"is the median difference in
correctness rank zero?"* — a non-parametric pairwise comparison that
does not assume a normal sampling distribution for the difference,
making it appropriate for the small sample sizes typical in
PMO-scenario benchmarks (Demšar 2006).

Implementation: `puma.metrics.statistical_tests.wilcoxon_signed_rank_models`
(4 TDD tests in `tests/unit/test_statistical_tests.py`). Driver
script: `scripts/wilcoxon_topmodels.py`.

## Scope note

The original v2.1.0 B.3 sweep (9 models × 3 scenarios × 100 instances)
is *not* preserved at the per-prediction level in the local DB
shipped with v2.1.0 — only aggregate metrics survive in
`docs/results/phase_b_analysis.md`. Sprint 3 therefore demonstrates
the tool against a **fresh mini-comparison** that fits in the
release-validation envelope (two models × 50 triage_jira instances,
~3-5 min wall-clock). Re-running the full B.3 sweep with per-
prediction persistence to enable Wilcoxon at scale is left as future
work; the driver script is already parameterised by `--run-prefix`
and `--top-k` to absorb that cohort without changes.

## Results — triage_jira

Run prefix: `wilcoxon_` (executed 2026-05-10).

| Rank | Model         | F1-macro |
|-----:|---------------|---------:|
|    1 | `qwen2.5:1.5b` |   0.6165 |
|    2 | `gemma3:1b`    |   0.4283 |

Pairwise Wilcoxon (two-sided, α=0.05):

| Pair                          | n_total | n_pairs (non-tied) | mean_diff | p-value | Significant? |
|-------------------------------|--------:|-------------------:|----------:|--------:|:------------:|
| qwen2.5:1.5b vs gemma3:1b     |      50 |                 19 |    +0.140 |  0.1083 |   no (α=0.05) |

## Interpretation

The 0.19-point F1-macro gap between `qwen2.5:1.5b` and `gemma3:1b` —
visible in the aggregate metric — is **not** statistically significant
under the Wilcoxon signed-rank test at α=0.05 with this sample size.

This is the kind of finding the test is designed to surface:

- **31 of 50 instances are tied** (both models correct or both
  incorrect). The test only operates on the 19 instances where the
  two models disagreed. At n=19 the Wilcoxon test has limited power.
- The **mean signed difference is +0.140 in favour of qwen2.5:1.5b**
  (14 pp more correct answers on average per instance), but the
  *distribution* of those differences across the 19 disagreeing
  instances is not extreme enough to reach significance.
- A larger sample (N=200, as in the canonical baseline) would likely
  resolve this either way. The N=50 cohort chosen for Sprint 3 is a
  release-validation envelope, not an academic-scale comparison.

The methodological point this surfaces — that *aggregate F1 gaps and
significance tests can disagree* — is exactly the value of adding a
Wilcoxon-style pairwise test to the PUMA toolkit: it forces the
analyst to distinguish "Model A scored higher on this sample" from
"Model A is statistically distinguishable from Model B on this task."

## Reproducibility

```bash
# Run the two model spec variants (~3-5 min total):
puma run /tmp/wilcoxon_pair_qwen15b.yaml
puma run /tmp/wilcoxon_pair_gemma3_1b.yaml

# Analyse:
docker exec puma_runner python /app/scripts/wilcoxon_topmodels.py \
    --run-prefix "wilcoxon_" --top-k 2 --scenarios triage_jira
```

To target a future B.3-style sweep, pass that sweep's `--run-prefix`
to the same script — no code changes needed.

## References

- Wilcoxon, F. (1945). *Individual comparisons by ranking methods.*
  Biometrics Bulletin 1(6), 80-83.
- Demšar, J. (2006). *Statistical comparisons of classifiers over
  multiple data sets.* JMLR 7, 1-30.
- `tests/unit/test_statistical_tests.py` — 4 TDD tests covering
  identical-model null, clearly-different-model alternative,
  required-fields contract, p_value range.
