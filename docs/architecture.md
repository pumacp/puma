# PUMA Architecture

## Data Flow

```
RunSpec (YAML)
    │
    ▼
Runner._execute_inferences()
    ├── Scenario.sample(n, seed)        ← puma.scenarios.*
    ├── Strategy.build_prompt()         ← puma.adaptation.strategies
    ├── OllamaClient.generate_sync()    ← puma.runtime.client  [skipped in dry-run]
    └── Scenario.parse_response()
         │
         ▼
    list[Prediction dict]
         │
    ┌────┴─────────────┐
    │                  │
    ▼                  ▼
Runner._compute_metrics()    Runner._persist_predictions()
    │                                 │
    ▼                                 ▼
metrics.json                    SQLite (puma.db)
results/<run_id>/               ├── runs
                                ├── instances
                                ├── predictions
                                ├── metrics
                                ├── emissions
                                └── profile_snapshots
```

## Package Map

| Package | Responsibility |
|---------|---------------|
| `puma.preflight` | Hardware detection, profile selection, provisioning checks |
| `puma.runtime` | OllamaClient, InferenceCache (SQLite-backed) |
| `puma.datasets` | Dataset loaders, integrity verification |
| `puma.scenarios` | Task definitions: triage_jira, estimation_tawos, prioritization_jira |
| `puma.adaptation` | Prompting strategies (zero-shot … EGI), example selection |
| `puma.perturbations` | Text perturbations: typos, case_change, truncate, tech_noise |
| `puma.metrics` | accuracy, calibration, robustness, fairness, efficiency, stability |
| `puma.sustainability` | CodeCarbon wrapper, emissions helpers |
| `puma.orchestrator` | RunSpec (Pydantic), Runner, compare_runs |
| `puma.storage` | SQLAlchemy 2.0 ORM: 6 tables, `init_db`, `session_scope` |
| `puma.dashboard` | Streamlit app: 7 views, reusable components, read-only DB access |
| `puma.reporting` | Markdown + optional PDF report generation |

## Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| `puma_ollama` | 11434 | Local LLM inference via Ollama |
| `puma_runner` | — | Benchmarking runner (all CLI commands) |
| `puma_dashboard` | 8501 | Streamlit dashboard |

All services share the `puma_network` bridge. Data is persisted in the `puma_data` named volume mounted at `/app/data`.

## Key Design Decisions

- **Spec-driven**: every run is fully described by a `RunSpec` YAML; results are reproducible given the same spec + seed.
- **Dry-run mode**: `Runner(spec, dry_run=True)` exercises the full pipeline (prompts, DB, artifacts) without calling Ollama — used in unit tests.
- **PYTHONPATH=/app/src**: no editable install required; works identically in Docker and locally.
- **Read-only dashboard**: the Streamlit app never writes to the database, preserving result integrity.
