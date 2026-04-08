# Specification: Estimation Agent (Etapa 1 MVP)

## Información General
- **Nombre**: Estimation Agent
- **Versión**: 1.0.0
- **Tipo**: Estimador de Esfuerzo
- **Fecha**: 2026-03-26
- **Metodología**: SDD + Agentic Coding

## Requisitos Funcionales

### Input
- **Fuente de datos**: `data/tawos_clean.csv`
- **Estructura CSV**: `project, title, description, story_points`
- **Proyectos disponibles**: MESOS, APSTUD, XD
- **Total de items**: ~31,000

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

### Estrategias Soportadas
1. **Zero-shot**: Sin ejemplos previos
2. **Few-shot**: Con ejemplos de proyectos similares
3. **CoT (Chain of Thought)**: Reasoning sobre complejidad

### Parámetros de LLM
- Temperatura: 0.0
- Seed: 42
- max_tokens: 10 (solo números Fibonacci)

## Criterios de Aceptación

### Métricas
- **MAE** ≤ 3.0 (Mean Absolute Error)
- **MdAE** ≤ 2.0 (Median Absolute Error)
- **Latencia** < 120s por batch de 100 (CPU)

### Validaciones
- Tests en `tests/test_estimation.py` pasan al 100%
- Resultados en `results/estimation_metrics.json`
- Reporte CO₂ generado en `results/emissions.csv`

### Reproducibilidad
- Mismo seed debe producir identical MAE
- docker-compose down && up debe dar mismo resultado

## JSON Schema de Salida

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

## Serie Fibonacci
Story points válidos: 1, 2, 3, 5, 8, 13, 21

## Integración con Sistema
- Agente Orchestrator llama a Estimation Agent
- RAG retrieval desde `/specs/` y `/data/`
- CodeCarbon mide CO₂ en cada ejecución
- Soporte para múltiples proyectos (MESOS, APSTUD, XD)