---
phase: 3
title: Scenarios, Adaptation Strategies, and Perturbations
status: approved
gate: F3
---

# Phase 3 — Scenarios, Adaptation & Perturbations

## Objective

Any combination scenario × model × strategy × perturbation expressed as YAML executes correctly.

## Checklist

- [ ] F3.1 `puma.scenarios.base.Scenario` abstract base class
- [ ] F3.2 Core scenarios: `TriageJira`, `EstimationTawos`, `PrioritizationJira`
- [ ] F3.3 YAML scenario metadata in `specs/scenarios/*.yaml`
- [ ] F3.4 `puma.adaptation.Strategy` abstract base class
- [ ] F3.5 Nine strategies as subclasses with Jinja templates
- [ ] F3.6 Few-shot example selector (stratified, deterministic)
- [ ] F3.7 Five perturbation functions
- [ ] F3.8 Tests per strategy and perturbation (snapshot + idempotence)

## F3.1 Scenario Base Class

```
src/puma/scenarios/base.py
```

Abstract class `Scenario`:
- `name: str` — unique ID matching scenario YAML filename
- `dataset: str` — "jira_sr" | "tawos"
- `task_type: Literal["classification", "regression", "ranking"]`
- `labels: list[str]` — valid output labels (empty for regression)
- `sample(n, seed) -> DataFrame` — reproducible subset from canonical dataset
- `parse_response(raw: str) -> str | float | None` — extract prediction from raw LLM text
- `gold_label(instance: dict) -> str | float` — ground-truth label from a DataFrame row

## F3.2 Core Scenarios

### TriageJira
- task_type: classification
- labels: ["Critical", "Major", "Minor", "Trivial"]
- gold_label column: "priority"
- parse_response: substring match (case-insensitive), first match wins

### EstimationTawos
- task_type: regression
- labels: [] (Fibonacci: [1,2,3,5,8,13,21])
- gold_label column: "story_points"
- parse_response: regex for first integer/float; snap to nearest Fibonacci

### PrioritizationJira
- task_type: ranking
- labels: ["A", "B"] (which issue is higher priority)
- Builds pairs from Jira SR; gold label = higher-priority issue

## F3.3 Scenario YAML Metadata

Each `specs/scenarios/<id>.yaml` contains:
```yaml
id: triage_jira
description: "Multi-class priority classification on Jira issues"
dataset: jira_sr
task_type: classification
primary_metric: f1_macro
suggested_sample: 500
labels: [Critical, Major, Minor, Trivial]
gold_column: priority
```

## F3.4 Adaptation Strategy Base Class

```
src/puma/adaptation/base.py
```

Abstract `Strategy`:
- `name: str`
- `build_prompt(scenario, instance, examples=None) -> str` — renders Jinja template
- `parse(raw_response: str) -> str | float | None` — delegates to scenario.parse_response

## F3.5 Nine Strategies

| ID | Class | Template |
|----|-------|---------|
| zero-shot | ZeroShot | `<scenario>/zero_shot.jinja` |
| zero-shot-cot | ZeroShotCoT | `<scenario>/zero_shot_cot.jinja` |
| one-shot | OneShot | `<scenario>/few_shot.jinja` (k=1) |
| few-shot-k | FewShotK | `<scenario>/few_shot.jinja` |
| cot-few-shot | CoTFewShot | `<scenario>/cot_few_shot.jinja` |
| rcoif | RCOIF | `<scenario>/rcoif.jinja` |
| contextual-anchoring | ContextualAnchoring | `<scenario>/contextual_anchoring.jinja` |
| self-consistency | SelfConsistency | Wraps ZeroShot, n=5, majority vote |
| egi | EGI | Multi-turn with clarifying questions |

All Jinja templates in `specs/prompts/<scenario>/<strategy>.jinja`.

## F3.6 Example Selector

```
src/puma/adaptation/examples.py
```

`select_examples(df, k, seed, stratify_by=None) -> list[dict]`:
- Stratified by class if `stratify_by` provided
- Deterministic: `random_state=seed`
- Returns list of row dicts (excluding the target instance)

## F3.7 Perturbations

```
src/puma/perturbations/text.py
```

Five functions, all pure (no side effects), all accept `seed: int`:

1. `typos(text, rate=0.05, seed=42) -> str` — visual-homolog character substitution
2. `case_change(text, mode="upper"|"lower"|"random", seed=42) -> str`
3. `truncate(text, keep=0.5, from_="end"|"middle") -> str`
4. `reorder_fields(instance: dict, order: list[str]) -> dict` — reorders text fields
5. `tech_noise(text, terms=["TODO","FIXME","deprecated"], insertions=3, seed=42) -> str`

## F3.8 Tests

- `tests/unit/test_scenarios.py` — parse_response, gold_label, sample determinism
- `tests/unit/test_adaptation.py` — prompt snapshot tests per strategy
- `tests/unit/test_perturbations.py` — idempotence with fixed seed, rate checks
- Gate run-spec: `specs/runs/smoke_triage.yaml` executes 20 instances

## Gate F3

A smoke run-spec `specs/runs/smoke_triage.yaml` combining:
- `triage_jira × qwen2.5:3b × few-shot-3 × typos_5pct`
- 20 instances
- Produces parsed predictions (run against real Ollama or mocked)
