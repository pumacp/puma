# Scenarios Reference

This document describes the three benchmark scenarios implemented in PUMA.

---

## triage_jira

**Class**: `puma.scenarios.triage_jira.TriageJiraScenario`  
**Task type**: Multi-class classification  
**Scenario ID**: `triage_jira`

### Task definition

Given a Jira issue with a title and description, assign one of four priority labels:

| Label | Meaning |
|-------|---------|
| `Critical` | Blocks work; requires immediate attention |
| `Major` | Significant impact; should be resolved soon |
| `Minor` | Low impact; addressed in normal flow |
| `Trivial` | Cosmetic or negligible; lowest priority |

### Dataset

| Property | Value |
|----------|-------|
| File | `data/jira_balanced_200.csv` |
| Rows | 200 (50 per class, balanced) |
| Columns used | `issue_key`, `title`, `description`, `priority` |
| Gold column | `priority` |

### Parse logic

```python
_ANSWER_RE = re.compile(
    r"\b(Critical|Major|Minor|Trivial)\b", re.IGNORECASE
)
# First match in the response is used; case-normalised to title case.
# Returns None if no match found.
```

### Metrics

| Metric | Notes |
|--------|-------|
| `f1_macro` | Primary metric; equal weight per class |
| `f1_weighted` | Weighted by class support |
| `accuracy` | Overall correct fraction |
| `per_class.<label>.precision` | Per-label |
| `per_class.<label>.recall` | Per-label |
| `per_class.<label>.f1` | Per-label |
| `parse_failure_rate` | Fraction where `parse_response` returned `None` |

### Example run-spec

```yaml
id: triage_zeroshot
scenario: triage_jira
sample_size: 50
models: [qwen2.5:3b]
adaptation:
  strategy: [zero-shot]
inference:
  temperature: 0.0
  seed: 42
metrics: [f1_macro]
```

---

## estimation_tawos

**Class**: `puma.scenarios.estimation_tawos.EstimationTawosScenario`  
**Task type**: Regression (ordinal Fibonacci)  
**Scenario ID**: `estimation_tawos`

### Task definition

Given a user story title and description, predict the story points as a Fibonacci number.

Valid values: **{1, 2, 3, 5, 8, 13, 21, 34, 55, 89}**

### Dataset

| Property | Value |
|----------|-------|
| File | `data/tawos_clean.csv` |
| Rows | 9 020 agile backlog items |
| Source | TAWOS (open-source agile dataset, SOLAR group) |
| Columns used | `item_id`, `title`, `description`, `story_points` |
| Gold column | `story_points` |

### Parse logic

```python
# 1. Strip punctuation from response
# 2. Extract first numeric substring
# 3. If numeric value is in FIBONACCI_SERIES → return it
# 4. If |closest_fibonacci - value| ≤ 1 → snap and return
# 5. Otherwise return raw float value
# 6. Return None if no number found
```

Fibonacci series: `{1, 2, 3, 5, 8, 13, 21, 34, 55, 89}`

### Metrics

| Metric | Notes |
|--------|-------|
| `mae` | Mean Absolute Error — primary metric |
| `mdae` | Median Absolute Error — robust to outliers |
| `rmse` | Root Mean Squared Error |
| `mae_by_bin` | MAE broken down by SP range (1–3, 5–8, 13–21, 34+) |
| `parse_failure_rate` | Fraction where response contained no parseable number |

### Story-point bins

| Bin ID | Range | Interpretation |
|--------|-------|---------------|
| `1-3` | 1 to 3 | Small stories |
| `5-8` | 5 to 8 | Medium stories |
| `13-21` | 13 to 21 | Large stories |
| `34+` | 34 and above | Extra-large / epics |

### Example run-spec

```yaml
id: estimation_zeroshot
scenario: estimation_tawos
sample_size: 50
models: [qwen2.5:3b]
adaptation:
  strategy: [zero-shot, few-shot-3]
inference:
  temperature: 0.0
  seed: 42
metrics: [mae]
```

---

## prioritization_jira

**Class**: `puma.scenarios.prioritization_jira.PrioritizationJiraScenario`  
**Task type**: Binary classification (pairwise ranking)  
**Scenario ID**: `prioritization_jira`

### Task definition

Given two Jira issues **A** and **B**, determine which has higher priority. The model must output `A` or `B`.

### Pair construction

Pairs are sampled from the Jira dataset. The gold label is determined by the priority order:

```
Critical > Major > Minor > Trivial
```

If both issues share the same priority, the pair is skipped to ensure unambiguous gold labels.

### Dataset

| Property | Value |
|----------|-------|
| Base file | `data/jira_balanced_200.csv` |
| Sampling | Random pairs (seed-controlled) |
| Columns used | `issue_key`, `title`, `description`, `priority` |
| Gold column | `higher_priority` (`A` or `B`) |

### Parse logic

```python
_ANSWER_RE = re.compile(r"\b([AB])\b", re.IGNORECASE)
# First match (A or B) in the response is used; uppercased.
# Returns None if no match found.
```

### Metrics

| Metric | Notes |
|--------|-------|
| `accuracy` | Primary metric — fraction of correct A/B predictions |
| `parse_failure_rate` | Fraction where response contained neither `A` nor `B` |

### Example run-spec

```yaml
id: prioritization_zeroshot
scenario: prioritization_jira
sample_size: 40
models: [qwen2.5:3b]
adaptation:
  strategy: [zero-shot]
inference:
  temperature: 0.0
  seed: 42
metrics: [accuracy]
```

---

## Common Scenario Interface

All scenarios implement `puma.scenarios.base.Scenario`:

```python
class Scenario(ABC):
    name: str           # scenario ID used in run-specs
    task_type: str      # "classification" | "regression"

    def sample(self, n: int, seed: int = 42) -> pd.DataFrame:
        """Return n instances from the dataset."""

    def gold_label(self, instance: dict) -> str:
        """Extract the ground-truth label from a row dict."""

    def parse_response(self, response: str) -> str | None:
        """Parse the LLM response into a label. Return None on failure."""

    def valid_labels(self) -> list[str]:
        """List of all valid output labels."""
```
