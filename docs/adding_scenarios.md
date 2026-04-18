# Adding a New Scenario

This guide walks through the steps to implement a new benchmark scenario in PUMA.

---

## Overview

A scenario defines:
- **How to load** the dataset
- **What the gold label is** for each instance
- **How to parse** the LLM response into a label
- **Which metrics** apply

Adding a scenario requires changes in five places:

1. Scenario class (`src/puma/scenarios/<name>.py`)
2. Runner scenario map (`src/puma/orchestrator/runner.py`)
3. RunSpec valid scenarios (`src/puma/orchestrator/runspec.py`)
4. Prompt templates (`specs/prompts/<name>/`)
5. Unit tests (`tests/unit/test_scenarios.py`)

---

## Step 1 — Write the scenario class

Create `src/puma/scenarios/my_scenario.py`:

```python
"""My custom PUMA scenario."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from puma.scenarios.base import Scenario


class MyScenario(Scenario):
    name = "my_scenario"
    task_type = "classification"    # or "regression"

    _DATA_PATH = Path("data/my_dataset.csv")
    _ANSWER_RE = re.compile(r"\b(LabelA|LabelB|LabelC)\b", re.IGNORECASE)

    def sample(self, n: int, seed: int = 42) -> pd.DataFrame:
        df = pd.read_csv(self._DATA_PATH)
        return df.sample(n=min(n, len(df)), random_state=seed).reset_index(drop=True)

    def gold_label(self, instance: dict) -> str:
        return str(instance["my_label_column"])

    def parse_response(self, response: str) -> str | None:
        m = self._ANSWER_RE.search(response)
        return m.group(1).capitalize() if m else None

    def valid_labels(self) -> list[str]:
        return ["LabelA", "LabelB", "LabelC"]
```

### Scenario base class contract

All scenarios must implement the `Scenario` ABC:

```python
class Scenario(ABC):
    name: str           # ID used in run-specs
    task_type: str      # "classification" | "regression"

    def sample(self, n: int, seed: int = 42) -> pd.DataFrame: ...
    def gold_label(self, instance: dict) -> str: ...
    def parse_response(self, response: str) -> str | None: ...
    def valid_labels(self) -> list[str]: ...
```

### Parse response guidelines

- Return a canonical label string on success (match your `valid_labels()`)
- Return `None` on failure — the Runner counts these as `parse_failure_rate`
- Use a compiled regex with `re.IGNORECASE` for robustness
- Take the **first** match to be deterministic

### Task type and metrics

| `task_type` | Metrics automatically computed |
|-------------|-------------------------------|
| `"classification"` | F1 macro/weighted, accuracy, confusion matrix, parse_failure_rate |
| `"regression"` | MAE, MDAE, RMSE, MAE by bin, parse_failure_rate |

If your scenario needs different metrics, override the Runner's `_compute_metrics` logic or implement a custom metric function in `puma.metrics.accuracy`.

---

## Step 2 — Register in the Runner

Open `src/puma/orchestrator/runner.py` and add to the `scenario_map`:

```python
from puma.scenarios.my_scenario import MyScenario   # ← add import

scenario_map = {
    "triage_jira":          TriageJiraScenario,
    "estimation_tawos":     EstimationTawosScenario,
    "prioritization_jira":  PrioritizationJiraScenario,
    "my_scenario":          MyScenario,              # ← add entry
}
```

---

## Step 3 — Register in RunSpec

Open `src/puma/orchestrator/runspec.py` and add the new ID to `VALID_SCENARIOS`:

```python
VALID_SCENARIOS = {
    "triage_jira",
    "estimation_tawos",
    "prioritization_jira",
    "my_scenario",         # ← add here
}
```

---

## Step 4 — Create Jinja2 prompt templates

PUMA requires at least a `zero_shot.jinja` template. Create the directory and templates:

```
specs/prompts/my_scenario/
├── zero_shot.jinja
├── zero_shot_cot.jinja
├── few_shot.jinja
├── cot_few_shot.jinja
├── rcoif.jinja
├── contextual_anchoring.jinja
└── egi.jinja
```

**Minimal `zero_shot.jinja` example:**

```jinja
You are an expert evaluator.

Given the following item:
Title: {{ title }}
Description: {{ description }}

Classify it as one of: LabelA, LabelB, LabelC.

Respond with exactly one label and nothing else.
```

**Few-shot `few_shot.jinja` example:**

```jinja
You are an expert evaluator.

Here are some examples:
{% for ex in examples %}
Title: {{ ex.title }}
Description: {{ ex.description }}
Label: {{ ex.gold_label }}

{% endfor %}
Now classify this item:
Title: {{ title }}
Description: {{ description }}

Respond with exactly one label.
```

### Available template variables

| Variable | Type | Description |
|----------|------|-------------|
| `{{ title }}` | str | Instance title field |
| `{{ description }}` | str | Instance description / body field |
| `{{ examples }}` | list[dict] | Few-shot examples (each has all instance fields + `gold_label`) |
| `{{ labels }}` | list[str] | `valid_labels()` output |

---

## Step 5 — Add unit tests

Add tests in `tests/unit/test_scenarios.py`:

```python
@pytest.mark.unit
class TestMyScenario:
    def setup_method(self):
        from puma.scenarios.my_scenario import MyScenario
        self.s = MyScenario()

    def test_parse_valid_label(self):
        assert self.s.parse_response("The answer is LabelA.") == "Labela"

    def test_parse_case_insensitive(self):
        assert self.s.parse_response("labela") == "Labela"

    def test_parse_returns_none_on_failure(self):
        assert self.s.parse_response("I have no idea") is None

    def test_parse_returns_first_match(self):
        assert self.s.parse_response("LabelB or LabelC? I say LabelB.") == "Labelb"

    def test_valid_labels(self):
        assert set(self.s.valid_labels()) == {"LabelA", "LabelB", "LabelC"}
```

Run tests:

```bash
docker compose run --rm --no-deps puma_runner pytest tests/unit/test_scenarios.py -v
```

---

## Step 6 — Create a smoke run-spec

```yaml
id: smoke_my_scenario
description: "Smoke: my_scenario × qwen2.5:3b × zero-shot"
scenario: my_scenario
sample_size: 5
models: [qwen2.5:3b]
adaptation:
  strategy: [zero-shot]
inference:
  temperature: 0.0
  seed: 42
metrics: [f1_macro]
```

Validate the full pipeline:

```bash
puma run specs/runs/smoke_my_scenario.yaml --dry-run
```

---

## Step 7 — Add dataset documentation

Add a section to `docs/scenarios_reference.md` describing:
- Task definition and labels
- Dataset source, file path, and columns
- Parse logic
- Primary metric
- Example run-spec

---

## Checklist

- [ ] `src/puma/scenarios/my_scenario.py` — scenario class
- [ ] `src/puma/orchestrator/runner.py` — entry in `scenario_map`
- [ ] `src/puma/orchestrator/runspec.py` — entry in `VALID_SCENARIOS`
- [ ] `specs/prompts/my_scenario/zero_shot.jinja` — at minimum
- [ ] `tests/unit/test_scenarios.py` — parse tests
- [ ] `specs/runs/smoke_my_scenario.yaml` — smoke run-spec
- [ ] `docs/scenarios_reference.md` — documentation entry
- [ ] `puma run specs/runs/smoke_my_scenario.yaml --dry-run` passes
