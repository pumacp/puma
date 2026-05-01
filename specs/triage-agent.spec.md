# Specification: Triage Agent (Phase 1 MVP)

## General Information
- **Name**: Triage Agent
- **Version**: 1.0.0
- **Type**: Issue Classifier
- **Date**: 2026-03-26
- **Methodology**: SDD + Agentic Coding

## Functional Requirements

### Input
- **Data source**: `data/jira_balanced_200.csv`
- **CSV structure**: `issue_key, title, description, priority`
- **Total issues**: 200 (50 per class: Critical, Major, Minor, Trivial)

### Output
```json
{
  "issue_id": "string",
  "predicted_priority": "Critical|Major|Minor|Trivial",
  "confidence": "float (0.0-1.0)",
  "reasoning": "string",
  "co2_grams": "float"
}
```

### Supported Strategies
1. **Zero-shot**: No prior examples
2. **Few-shot**: With 2-3 examples per class
3. **CoT (Chain of Thought)**: Explicit reasoning

### LLM Parameters
- Temperature: 0.0
- Seed: 42
- max_tokens: 50

## Acceptance Criteria

### Metrics
- **F1-Macro** ≥ 0.55
- **Latency** < 60s per batch of 200 (CPU)
- **Accuracy** balanced per class

### Validations
- Tests in `tests/test_triage.py` pass at 100%
- Results in `results/triage_metrics.json`
- CO₂ report generated in `results/emissions.csv`

### Reproducibility
- Same seed must produce identical F1-score
- docker-compose down && up must give the same result

## Output JSON Schema

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "issue_id": {"type": "string"},
      "predicted_priority": {"type": "string", "enum": ["Critical", "Major", "Minor", "Trivial"]},
      "confidence": {"type": "number", "minimum": 0, "maximum": 1},
      "reasoning": {"type": "string"},
      "co2_grams": {"type": "number"}
    },
    "required": ["issue_id", "predicted_priority"]
  }
}
```

## System Integration
- Orchestrator Agent calls Triage Agent
- RAG retrieval from `/specs/` and `/data/`
- CodeCarbon measures CO₂ per execution
