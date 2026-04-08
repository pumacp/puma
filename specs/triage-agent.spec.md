# Specification: Triage Agent (Etapa 1 MVP)

## Información General
- **Nombre**: Triage Agent
- **Versión**: 1.0.0
- **Tipo**: Clasificador de Issues
- **Fecha**: 2026-03-26
- **Metodología**: SDD + Agentic Coding

## Requisitos Funcionales

### Input
- **Fuente de datos**: `data/jira_balanced_200.csv`
- **Estructura CSV**: `issue_key, title, description, priority`
- **Total de issues**: 200 (50 por clase: Critical, Major, Minor, Trivial)

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

### Estrategias Soportadas
1. **Zero-shot**: Sin ejemplos previos
2. **Few-shot**: Con 2-3 ejemplos por clase
3. **CoT (Chain of Thought)**: Reasoning explícito

### Parámetros de LLM
- Temperatura: 0.0
- Seed: 42
- max_tokens: 50

## Criterios de Aceptación

### Métricas
- **F1-Macro** ≥ 0.55
- **Latencia** < 60s por batch de 200 (CPU)
- **Accuracy** por clase balanceado

### Validaciones
- Tests en `tests/test_triage.py` pasan al 100%
- Resultados en `results/triage_metrics.json`
- Reporte CO₂ generado en `results/emissions.csv`

### Reproducibilidad
- Mismo seed debe producir identical F1-score
- docker-compose down && up debe dar mismo resultado

## JSON Schema de Salida

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

## Integración con Sistema
- Agente Orchestrator llama a Triage Agent
- RAG retrieval desde `/specs/` y `/data/`
- CodeCarbon mide CO₂ en cada ejecución