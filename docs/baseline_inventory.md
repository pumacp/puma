---
title: Baseline Inventory
description: Snapshot of repository state before Phase 0 restructuring
created: 2026-04-18
---

# Baseline Inventory

Snapshot of repository state before Phase 0 restructuring. Produced by executing Step 1 of CLAUDE_CODE_INSTRUCTIONS.md.

---

## 1. Repository Overview

- **Branch:** main
- **Commits:** 1 (`af00114 PUMA`)
- **Python runtime declared:** 3.11 (Dockerfile)
- **Package layout:** flat — no `src/puma/` package yet; code lives in `src/` (scripts) and `agents/` (agent stubs)
- **No `pyproject.toml`** — dependencies managed via `requirements.txt` only

---

## 2. Directory Structure

```
puma/
├── agents/                  # Agent stubs (LangGraph-style, not functional)
│   ├── __init__.py
│   ├── code_generator_agent.py
│   ├── estimation_agent.py
│   ├── orchestrator.py
│   ├── reviewer_agent.py
│   ├── tester_agent.py
│   └── triage_agent.py
├── assets/                  # Static assets
├── data/                    # Runtime datasets (gitignored partially)
│   ├── jira_balanced_200.csv   — 200 balanced Jira issues (4 classes × 50)
│   ├── tawos_clean.csv          — TAWOS cleaned (story points, project col)
│   └── tawos_raw.csv            — TAWOS raw
├── db/                      # TAWOS SQL dump
│   └── TAWOS.sql
├── reports/                 # Benchmark reports (figures deleted)
│   └── summary_report.json
├── results/                 # Evaluation outputs
│   ├── benchmark_history.csv
│   ├── estimation_cache.json
│   ├── evaluation_log.txt
│   ├── triage_cache.json
│   ├── triage_metrics.json          — F1-macro=0.5087 (mistral:7b)
│   └── triage_metrics_mistral_7b.json
├── scripts/
│   ├── create_jira_data.py   — Jira dataset builder (external URLs broken)
│   ├── download_datasets.py  — Dataset downloader
│   └── run_all_models.sh     — Multi-model benchmark runner
├── specs/                   # Existing specs (minimal)
│   ├── architecture.md
│   ├── constitution.md
│   ├── estimation-agent.spec.md
│   ├── triage-agent.spec.md
│   └── prompts/
├── src/                     # Core evaluation scripts (flat, not a package)
│   ├── cleanup.py
│   ├── data_prep.py
│   ├── evaluate_estimation.py
│   ├── evaluate_triage.py
│   ├── history.py
│   ├── rag_index.py
│   └── statistical_analysis.py
├── tests/
│   ├── __init__.py
│   └── test_core.py          — 14 tests (integration + unit)
├── CLAUDE_CODE_INSTRUCTIONS.md
├── Dockerfile                — python:3.11-slim, no GPU support
├── docker-compose.yml        — services: ollama + evaluator
├── emissions.csv             — CodeCarbon output
├── index.md                  — Architecture/scope document
├── pytest.ini
├── README.md
├── requirements.txt
└── start_puma.sh             — Entry point (basic, no preflight/profile logic)
```

---

## 3. Existing Modules

### `src/evaluate_triage.py`
- **Function:** Zero-shot triage classification via Ollama HTTP API (requests-based)
- **Model:** `qwen2.5:3b` (env `LLM_MODEL`)
- **Classes:** `TriageEvaluator` with `evaluate_issue()` and `evaluate_batch()`
- **Parser:** `parse_prediction()` — regex match on `Critical|Major|Minor|Trivial`
- **Metrics:** F1-macro, confusion matrix via scikit-learn
- **Cache:** JSON flat-file (`results/triage_cache.json`)
- **CodeCarbon:** `@track_emissions` decorator
- **Config:** all via env vars (`TRIAGE_TEMPERATURE`, `TRIAGE_SEED`, etc.)

### `src/evaluate_estimation.py`
- **Function:** Few-shot story-point estimation via Ollama
- **Model:** `qwen2.5:3b` (env `LLM_MODEL`)
- **Classes:** `EstimationEvaluator` with `evaluate_item()` and `evaluate_batch()`
- **Parser:** `parse_story_points()` — float extraction with regex
- **Metrics:** MAE via scikit-learn
- **Cache:** JSON flat-file (`results/estimation_cache.json`)
- **Fibonacci series:** `[1, 2, 3, 5, 8, 13, 21]`
- **Few-shot:** 3 hardcoded examples
- **Config:** all via env vars

### `src/history.py`
- **Function:** Persists benchmark runs to `results/benchmark_history.csv`
- **Functions:** `save_to_history()`, `get_ollama_model_info()`, `get_system_info()`
- **HW detection:** `platform`, `psutil` (CPU, RAM); no GPU detection

### `src/data_prep.py`
- **Function:** Balances Jira dataset, cleans TAWOS, produces `data/*.csv`
- **Key functions:** `load_and_balance_jira()`, `load_and_clean_tawos()`

### `src/statistical_analysis.py`
- **Function:** Wilcoxon tests, effect sizes, confidence intervals on benchmark results
- **Dependencies:** `scipy.stats`, `sklearn.metrics`

### `src/cleanup.py`
- **Function:** Removes stale caches and temp files

### `src/rag_index.py`
- **Function:** Stub/placeholder for RAG indexing (not functional)

### `agents/orchestrator.py`
- **Function:** Thin orchestrator stub — delegates to `src/evaluate_*.py`
- **Pattern:** Class `Orchestrator` with `run_workflow()`, no real LangGraph usage

### `agents/{triage,estimation,reviewer,tester,code_generator}_agent.py`
- **Function:** Stub agent classes — no real Ollama calls or logic

---

## 4. Dependencies (`requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| pandas | (unpinned) | DataFrames |
| scikit-learn | (unpinned) | Metrics |
| scipy | (unpinned) | Statistical tests |
| ollama | (unpinned) | Ollama Python client |
| codecarbon | (unpinned) | CO₂ tracking |
| matplotlib | (unpinned) | Plots |
| seaborn | (unpinned) | Plots |
| requests | (unpinned) | HTTP calls |
| pytest | (unpinned) | Tests |

**Missing vs. target** (from `CLAUDE_CODE_INSTRUCTIONS.md §F0.2`):  
`typer`, `httpx`, `pydantic`, `pyyaml`, `jinja2`, `numpy`, `sqlalchemy`, `psutil`, `streamlit`, `langdetect`, `pytest-cov`, `ruff`, `mypy`, `structlog`, `rich`, `pre-commit`, `alembic`, `respx`

---

## 5. Tests (`tests/test_core.py`)

14 test cases across 7 classes:

| Class | Count | Type | Status |
|-------|-------|------|--------|
| `TestDataFiles` | 5 | Integration (needs CSV files) | Pass (data present) |
| `TestTriageEvaluator` | 4 | Unit | Pass |
| `TestEstimationEvaluator` | 5 | Unit | Pass |
| `TestStatisticalAnalysis` | 4 | Unit | Pass |
| `TestCodeCarbon` | 1 | Import | Pass |
| `TestOllamaClient` | 1 | Import | Pass |
| `TestEndToEnd` | 2 | E2E (needs Ollama) | Skip without Ollama |

No `tests/unit/`, `tests/integration/`, `tests/smoke/` subdirectories yet.

---

## 6. Docker / Infrastructure

### `docker-compose.yml`
- **Services:** `ollama` (ollama/ollama:latest), `evaluator` (custom Dockerfile)
- **No GPU support** in compose file
- **No dashboard service**, no Grafana service
- **Config via env vars** in compose

### `Dockerfile`
- Base: `python:3.11-slim`
- Installs requirements, copies repo
- No entrypoint (CMD: `tail -f /dev/null`)

### `start_puma.sh`
- Starts Docker Compose
- Pulls Ollama model
- Runs `src/evaluate_triage.py` and `src/evaluate_estimation.py`
- **No HW detection, no profile selection, no preflight**

---

## 7. Known Results (MVP Baseline)

| Task | Model | Metric | Value |
|------|-------|--------|-------|
| Triage | qwen2.5:3b | F1-macro | ~0.5867 (reported) / 0.5087 (mistral:7b in saved JSON) |
| Estimation | qwen2.5:3b | MAE | ~1.89 SP (reported in CLAUDE_CODE_INSTRUCTIONS.md) |

---

## 8. What Is Missing vs. Target Architecture

| Component | Target (INDEX.md) | Current State |
|-----------|-------------------|---------------|
| `src/puma/` package | Full modular package | Does not exist |
| `pyproject.toml` | Required | Does not exist |
| `preflight/` | HW detection + profiles | Not implemented |
| `runtime/` | OllamaClient (httpx, logprobs) | Uses `requests` + `ollama` SDK ad-hoc |
| `datasets/` | Jira SR + TAWOS downloaders | Partial (`scripts/download_datasets.py`) |
| `scenarios/` | Declarative YAML scenarios | Stubs in `specs/` |
| `adaptation/` | 9 prompting strategies | Zero-shot only |
| `perturbations/` | 5 perturbation types | Not implemented |
| `metrics/` | 7 metric families | Only accuracy (F1, MAE) |
| `sustainability/` | CodeCarbon wrapper | Basic `@track_emissions` |
| `storage/` | SQLAlchemy + SQLite | JSON flat-file caches |
| `dashboard/` | Streamlit app | Not implemented |
| `cli.py` | Typer CLI | Not implemented |
| `config/profiles.yaml` | 5 HW profiles | Not implemented |
| `config/models_catalog.yaml` | Full model catalog | Not implemented |
| `specs/runs/` | Declarative run-specs | Not implemented |
| `specs/prompts/` | Jinja prompt templates | Partial (1 file) |
| `tests/unit/` | ≥80% coverage on core modules | Not structured |
| `tests/integration/` | Ollama integration tests | Not structured |
| `tests/smoke/` | E2E smoke tests | Not structured |
| `Makefile` | `make lint/test/smoke` | Not implemented |
| `ruff` / `mypy` | Linting and type checking | Not configured |
| Logging | structlog JSON lines | Basic `logging` module |

---

## 9. Files to Preserve (Conservative Refactor)

The following files contain working logic that must be migrated (not deleted) during Phase 0:

- `src/evaluate_triage.py` → migrate to `src/puma/scenarios/triage_jira.py` + `src/puma/runtime/`
- `src/evaluate_estimation.py` → migrate to `src/puma/scenarios/estimation_tawos.py`
- `src/history.py` → migrate to `src/puma/storage/` + `src/puma/preflight/`
- `src/data_prep.py` → migrate to `src/puma/datasets/`
- `src/statistical_analysis.py` → migrate to `src/puma/metrics/`
- `tests/test_core.py` → split into `tests/unit/` and `tests/integration/`
- `data/jira_balanced_200.csv` → keep in `data/` during transition
- `data/tawos_clean.csv` → keep in `data/` during transition
- `db/TAWOS.sql` → source for `src/puma/datasets/tawos.py`

---

## 10. Open Questions (Phase 0)

See `docs/open_questions.md` for decisions logged during implementation.
