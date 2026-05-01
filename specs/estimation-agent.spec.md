# Specification: Estimation Agent (Phase 1 MVP)

## General Information
- **Name**: Estimation Agent
- **Version**: 1.0.0
- **Type**: Effort Estimator
- **Date**: 2026-03-26
- **Methodology**: SDD + Agentic Coding

## Functional Requirements

### Input
- **Data source**: `data/tawos_clean.csv`
- **CSV structure**: `project, title, description, story_points`
- **Available projects**: MESOS, APSTUD, XD
- **Total items**: ~31,000

### Output
```json
{
  "item_id": "string",
  "project": "string",
  "predicted_sp": "int (1,2,3,5,8,13,21)",
  "confidence": "float (0.0-1.0)",
  "reasoning": "string",
  "co2_grams": "float"
}
```

### Supported Strategies
1. **Zero-shot**: No prior examples
2. **Few-shot**: With examples from similar projects
3. **CoT (Chain of Thought)**: Explicit reasoning about complexity

### LLM Parameters
- Temperature: 0.0
- Seed: 42
- max_tokens: 10 (Fibonacci numbers only)

## Acceptance Criteria

### Metrics
- **MAE** ≤ 3.0 (Mean Absolute Error)
- **MdAE** ≤ 2.0 (Median Absolute Error)
- **Latency** < 120s per batch of 100 (CPU)

### Validations
- Tests in `tests/test_estimation.py` pass at 100%
- Results in `results/estimation_metrics.json`
- CO₂ report generated in `results/emissions.csv`

### Reproducibility
- Same seed must produce identical MAE
- docker-compose down && up must give the same result

## Output JSON Schema

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "item_id": {"type": "string"},
      "project": {"type": "string"},
      "predicted_sp": {"type": "integer", "enum": [1, 2, 3, 5, 8, 13, 21]},
      "confidence": {"type": "number", "minimum": 0, "maximum": 1},
      "reasoning": {"type": "string"},
      "co2_grams": {"type": "number"}
    },
    "required": ["item_id", "project", "predicted_sp"]
  }
}
```

## Fibonacci Series
Valid story points: 1, 2, 3, 5, 8, 13, 21

## System Integration
- Orchestrator Agent calls Estimation Agent
- RAG retrieval from `/specs/` and `/data/`
- CodeCarbon measures CO₂ per execution
- Support for multiple projects (MESOS, APSTUD, XD)
