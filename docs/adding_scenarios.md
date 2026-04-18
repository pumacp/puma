# Adding a New Scenario

## 1. Define the scenario class

Create `src/puma/scenarios/<name>.py` inheriting from `puma.scenarios.base.Scenario`:

```python
from puma.scenarios.base import Scenario

class MyScenario(Scenario):
    name = "my_scenario"
    task_type = "classification"   # or "regression"

    def sample(self, n: int, seed: int = 42) -> "pd.DataFrame":
        """Return a DataFrame of n instances."""
        ...

    def gold_label(self, instance: dict) -> str:
        """Extract the ground-truth label from a row."""
        return str(instance["label_col"])

    def parse_response(self, response: str) -> str | None:
        """Parse the LLM output into a label; return None on failure."""
        import re
        m = re.search(r"\b(ClassA|ClassB)\b", response, re.IGNORECASE)
        return m.group(1).capitalize() if m else None

    def valid_labels(self) -> list[str]:
        return ["ClassA", "ClassB"]
```

## 2. Register in the Runner

Open `src/puma/orchestrator/runner.py` and add to `scenario_map`:

```python
from puma.scenarios.my_scenario import MyScenario

scenario_map = {
    "triage_jira": TriageJiraScenario,
    "estimation_tawos": EstimationTawosScenario,
    "prioritization_jira": PrioritizationJiraScenario,
    "my_scenario": MyScenario,          # ← add this
}
```

## 3. Register in RunSpec

Open `src/puma/orchestrator/runspec.py` and add to `VALID_SCENARIOS`:

```python
VALID_SCENARIOS = {"triage_jira", "estimation_tawos", "prioritization_jira", "my_scenario"}
```

## 4. Create prompt templates

For each strategy you want to support, add a Jinja2 template:

```
specs/prompts/my_scenario/zero_shot.jinja
specs/prompts/my_scenario/few_shot.jinja
...
```

Available template variables: `{{ title }}`, `{{ description }}`, `{{ examples }}`, `{{ gold_label }}`.

## 5. Write tests

Add unit tests in `tests/unit/test_scenarios.py`:

```python
def test_my_scenario_parse():
    s = MyScenario()
    assert s.parse_response("The answer is ClassA.") == "ClassA"
    assert s.parse_response("I don't know") is None
```

## 6. Add a smoke run-spec

```yaml
id: smoke_my_scenario
scenario: my_scenario
sample_size: 5
models: [qwen2.5:3b]
adaptation:
  strategy: [zero-shot]
inference:
  temperature: 0.0
  seed: 42
metrics: [accuracy]
```

Run `puma run specs/runs/smoke_my_scenario.yaml --dry-run` to verify end-to-end.
