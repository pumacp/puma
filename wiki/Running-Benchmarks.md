# Running Benchmarks

This page is the operational reference for the `puma run` command and its
companion subcommands. For the conceptual layering of the system see
[Architecture](Architecture); for the model and dataset catalog see
[Models and Datasets](Models-And-Datasets).

## The `puma run` command

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--scenario` | string (required) | — | Scenario name: `triage_jira`, `effort_tawos`, or `prioritization_jira`. |
| `--model` | string (required) | — | Ollama tag of the model under test (e.g. `qwen2.5:3b`). |
| `--strategy` | string | `zero_shot` | Prompting strategy. See list below. |
| `--instances` | int | 100 | Number of dataset instances to evaluate. |
| `--seed` | int | 42 | Random seed for any sampling step. |
| `--profile` | string | auto | Hardware profile override. Skips `preflight` detection. |
| `--temperature` | float | 0.0 | Sampling temperature for the model. |
| `--output-dir` | path | `data/runs/` | Where to write SQLite + JSON artifacts. |
| `--run-id` | string | auto | Override the auto-generated run identifier. |

## Scenarios available

- **`triage_jira`** — classify each issue into one of four priorities:
  Critical, Major, Minor, Trivial. Metric of interest: F1-macro.
- **`effort_tawos`** — story-point estimation as regression. Metrics of
  interest: MAE, MdAE.
- **`prioritization_jira`** — pairwise prioritization (given two issues,
  which is higher priority?). Metrics of interest: pairwise accuracy and
  ranking-aware MRR.

## Models supported

Run `puma models` to list the current curated catalog with sizes, baseline
F1, and recommended hardware profile. Any Ollama-compatible tag can be passed
to `--model`, but only models in the curated catalog ship with empirical
validation; off-catalog runs are accepted and logged but flagged as
"experimental" in their submission metadata if you publish them.

## Prompting strategies

- **`zero_shot`** — no in-context examples; only the task instructions and
  the input.
- **`few_shot_3`** / **`few_shot_6`** — three or six labelled examples
  selected from a held-out portion of the dataset, balanced across labels.
- **`chain_of_thought`** — appends an explicit "think step by step" cue to
  encourage reasoning before the final answer.
- **`rcoif`** — structured Role / Context / Objective / Instructions / Format
  template. Best for models with strong instruction following.
- **`contextual_anchoring`** — the canonical baseline strategy used in PUMA's
  reference comparisons.

## Multi-model comparison

Once you have two runs, place them side by side or test for statistical
significance:

```bash
docker compose run --rm puma_runner puma compare <run_id_1> <run_id_2>
docker compose run --rm puma_runner puma wilcoxon <run_id_1> <run_id_2>
```

`compare` prints a side-by-side metrics table; `wilcoxon` runs the Wilcoxon
signed-rank test on the paired per-instance metrics and reports the p-value.
