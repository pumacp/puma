# Context Engineering Rules (RAG)

## Objetivo
Optimizar el contexto para agentes LLM usando recuperación de información relevante (RAG).

## Reglas de Recuperación

### 1. Top-K Documents
- Recuperar siempre los **5 documentos más relevantes**
- Usar similarity score ≥ 0.7 como threshold
- Si no hay documentos suficientes, usar todos los disponibles

### 2. Resúmenes (Summarization)
- Generar resumen de **200 tokens máximo** por documento
- Incluir: título, propósito, estructura de datos
- Priorizar información reciente (modificaciones últimas 24h)

### 3. Evitar Contaminación de Contexto
- **Limpiar contexto entre experimentos**: eliminar historial de conversación previo
- **Separar ejecuciones**: cada benchmark es independiente
- **No mezclar datos de train/test**: mantener separación estricta

### 4. Construcción de Prompt
Orden recomendado:
1. System prompt (reglas globales)
2. Context retrieved (RAG)
3. Few-shot examples (si aplica)
4. User query (input actual)

### 5. Métricas de Contexto
- Track de tokens utilizados por prompt
- Alertar si > 4000 tokens
- Considerar truncation de contexto menos relevante

## Implementación RAG

### Fuentes Indexadas
- `/data/*.csv` - Datasets (jira_balanced_200.csv, tawos_clean.csv)
- `/specs/*.md` - Especificaciones SDD
- `/specs/*.spec.md` - Specs de agentes
- `/specs/prompts/*.md` - Prompts optimizados

### Chunks
- Tamaño: 500 tokens por chunk
- Overlap: 50 tokens entre chunks
- Embedding model: sentence-transformers (local)

## Mejores Prácticas

1. **Cache de embeddings**: No recalcular si no hay cambios en datos
2. **Fallback**: Si RAG falla, usar prompts por defecto
3. **Logging**: Registrar qué documentos fueron retrievalados
4. **A/B Testing**: Comparar rendimiento con/sin RAG

## Integración con Agentes
- Triage Agent: recuperar specs de triage + ejemplos de clasificación
- Estimation Agent: recuperar specs de estimation + ejemplos de proyectos similares
- Code Generator: recuperar specs de功能 a implementar