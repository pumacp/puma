# PUMA Architecture (Agentic)

## Overview
PUMA (Puma Unified Model Assessment) is an LLM evaluation framework for software engineering tasks.

## Main Components

### Agents (LangGraph + Ollama)
- **Orchestrator**: Coordinates workflow between agents
- **Triage Agent**: Classifies issues into priorities (Critical, Major, Minor, Trivial)
- **Estimation Agent**: Estimates story points using the Fibonacci series
- **Code Generator Agent**: Generates code from .spec.md specifications
- **Tester Agent**: Generates and runs tests automatically
- **Reviewer Agent**: Validates generated code against specs

## Workflow (Agentic Workflow)
```
Spec (SDD) → Architect → Coder → Tester → Reviewer → Deploy
     ↑                                                         
     └────────────── Feedback Loop ←─────────────────────────┘
```

## RAG + Context Engineering
- ChromaDB indexes /data/ and /specs/
- Retrieval of the 5 most relevant documents
- Summary of 200 tokens before long prompts
- Context cleanup between experiments

## Infrastructure
- **Docker**: Containers for Ollama and evaluator
- **Ollama**: Local LLM (qwen2.5:3b, mistral:7b, etc.)
- **CodeCarbon**: CO₂ measurement per execution

## Reproducibility
- Temperature = 0.0 in all agents
- Seed = 42 in all runs
- docker-compose down && up must produce identical results
