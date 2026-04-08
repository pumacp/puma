# Arquitectura PUMA (Agentic)

## Visión General
PUMA (Puma Unified Model Assessment) es un framework de evaluación de LLMs para tareas de ingeniería de software.

## Componentes Principales

### Agentes (LangGraph + Ollama)
- **Orchestrator**: Coordina flujo de trabajo entre agentes
- **Triage Agent**: Clasifica issues en prioridades (Critical, Major, Minor, Trivial)
- **Estimation Agent**: Estima story points usando serie Fibonacci
- **Code Generator Agent**: Genera código desde especificaciones .spec.md
- **Tester Agent**: Genera y ejecuta tests automáticamente
- **Reviewer Agent**: Valida código generado contra specs

## Flujo de Trabajo (Agentic Workflow)
```
Spec (SDD) → Architect → Coder → Tester → Reviewer → Deploy
     ↑                                                         
     └────────────── Feedback Loop ←─────────────────────────┘
```

## RAG + Context Engineering
- ChromaDB indexa /data/ y /specs/
- Retrieval de los 5 documentos más relevantes
- Summary de 200 tokens antes de prompts largos
- Limpieza de contexto entre experimentos

## Infraestructura
- **Docker**: Contenedores para Ollama y evaluator
- **Ollama**: LLM local (qwen2.5:3b, mistral:7b, etc.)
- **CodeCarbon**: Medición de CO₂ en cada ejecución

## Reproducibilidad
- Temperatura = 0.0 en todos los agentes
- Seed = 42 en todas las ejecuciones
- docker-compose down && up debe dar resultados idénticos