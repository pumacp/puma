# PUMA — Index

**Platform for Understanding & Management with Agents**
Local, reproducible, multi-dimensional benchmarking of open LLMs on project management tasks.

---

## 1. What is PUMA?

PUMA evaluates open large language models (served locally via [Ollama](https://ollama.ai)) on three PMO tasks: issue triage, story-point estimation, and backlog prioritization. It produces a multi-dimensional performance profile per model covering accuracy, calibration, robustness, fairness, inference efficiency, and carbon footprint — all running 100% locally, GDPR-compliant by design.

### Why PUMA?

Existing LLM benchmarks measure accuracy in cloud environments. PUMA addresses a different question: *which open model should a project management office deploy on-premise, given their hardware, risk tolerance, and sustainability constraints?*

Key differentiators:

| Property | PUMA |
|----------|------|
| Inference | 100% local via Ollama — no external API calls |
| Reproducibility | Spec-driven: every run fully described by a declarative YAML |
| Metrics | Accuracy + calibration + robustness + fairness + efficiency + CO₂ |
| Scenarios | Triage (Jira), Estimation (TAWOS), Prioritization (pairwise) |
| Hardware | Runs on consumer laptops (8 GB RAM) up to GPU workstations |
| Privacy | No data leaves the machine |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Host machine (Docker + docker compose)                  │
│                                                          │
│  ┌──────────────┐   ┌──────────────┐  ┌──────────────┐  │
│  │ puma_runner  │   │ puma_ollama  │  │puma_dashboard│  │
│  │              │──▶│  :11434      │  │   :8501      │  │
│  │  puma CLI    │   │  LLM server  │  │  Streamlit   │  │
│  └──────┬───────┘   └──────────────┘  └──────────────┘  │
│         │                                                 │
│         ▼                                                 │
│  ┌──────────────────────────────┐                        │
│  │  puma_data volume            │                        │
│  │  data/puma.db  (SQLite)      │                        │
│  │  data/cache/inferences.db    │                        │
│  │  results/<run_id>/           │                        │
│  └──────────────────────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

Full data-flow and package map → [docs/architecture.md](docs/architecture.md)

---

## 3. Benchmark Scenarios

### 3.1 Issue Triage (`triage_jira`)

**Task**: Given a Jira issue title and description, assign a priority label.  
**Labels**: `Critical`, `Major`, `Minor`, `Trivial`  
**Dataset**: 200 balanced Jira issues (50 per class)  
**Primary metric**: F1 macro  

### 3.2 Story-Point Estimation (`estimation_tawos`)

**Task**: Given a user story title and description, predict story points.  
**Output**: Fibonacci number from {1, 2, 3, 5, 8, 13, 21, 34, 55, 89}  
**Dataset**: TAWOS — 9 020 agile backlog items  
**Primary metric**: MAE  

### 3.3 Backlog Prioritization (`prioritization_jira`)

**Task**: Given two Jira issues A and B, decide which has higher priority.  
**Output**: `A` or `B`  
**Dataset**: Pairwise samples from Jira SR dataset  
**Primary metric**: Accuracy  

Full scenario specs → [docs/scenarios_reference.md](docs/scenarios_reference.md)

---

## 4. Prompting Strategies

PUMA implements nine prompting strategies covering the major paradigms in the literature:

| Strategy | ID | Description |
|----------|----|-------------|
| Zero-shot | `zero-shot` | Direct instruction, no examples |
| Zero-shot CoT | `zero-shot-cot` | Add "think step by step" |
| One-shot | `one-shot` | Single in-context example |
| Few-shot k=3 | `few-shot-3` | Three stratified examples |
| Few-shot k=5 | `few-shot-5` | Five stratified examples |
| Few-shot k=8 | `few-shot-8` | Eight stratified examples |
| CoT few-shot | `cot-few-shot` | Few-shot with CoT rationales |
| RCOIF | `rcoif` | Role + Context + Output + Instruction + Format |
| Contextual Anchoring | `contextual-anchoring` | Grounds prediction in project context |
| Self-Consistency | `self-consistency` | Majority vote over n samples (requires temperature > 0) |
| EGI | `egi` | Example-Guided Inference |

Templates live in `specs/prompts/<scenario>/<strategy>.jinja`.

---

## 5. Metrics

### 5.1 Accuracy
- **F1 macro / weighted** — classification tasks
- **Accuracy** — overall correct fraction
- **MAE / MDAE / RMSE** — regression tasks (story points)
- **MAE by SP bin** — 1–3 / 5–8 / 13–21 / 34+

### 5.2 Calibration
- **ECE** (Expected Calibration Error) — equal-width bins
- **MCE** (Maximum Calibration Error)
- **Brier Score**
- **Reliability diagrams** (PNG export)

### 5.3 Robustness
- **Robustness score** — `max(0, 1 − |metric_orig − metric_perturbed|)`
- **Consistency rate** — fraction of predictions unchanged under perturbation

Text perturbations: `typos_5pct`, `case_upper`, `case_lower`, `truncate_50pct`, `tech_noise`

### 5.4 Fairness
- **Per-group accuracy** — broken down by any categorical attribute
- **Fairness gap** — max − min accuracy across groups

### 5.5 Efficiency
- **Latency percentiles** — p50, p95, p99, mean (ms)
- **Throughput** — instances per minute
- **Parse failure rate** — fraction of responses that could not be parsed

### 5.6 Sustainability
- **CO₂ equivalent (g / kg)** via CodeCarbon (offline, process-level)
- **Energy consumed (kWh)**
- **gCO₂ per F1 point** — quality-adjusted cost

Full formulas → [docs/metrics_reference.md](docs/metrics_reference.md)

---

## 6. Model Catalog

Models are registered in `config/models_catalog.yaml`. Current catalog:

| Model | Params | Size | CPU-lite | CPU-standard | GPU-entry |
|-------|--------|------|----------|--------------|-----------|
| qwen2.5:0.5b | 0.5B | ~0.4 GB | ✓ | ✓ | ✓ |
| qwen2.5:1.5b | 1.5B | ~1.0 GB | ✓ | ✓ | ✓ |
| qwen2.5:3b | 3B | ~2.0 GB | — | ✓ | ✓ |
| qwen2.5:7b | 7B | ~4.7 GB | — | ✓ | ✓ |
| llama3.2:3b | 3B | ~2.0 GB | — | ✓ | ✓ |
| mistral:7b | 7B | ~4.1 GB | — | ✓ | ✓ |
| deepseek-r1:7b | 7B | ~4.7 GB | — | — | ✓ |

Add a new model → [docs/adding_models.md](docs/adding_models.md)

---

## 7. Hardware Profiles

| Profile | RAM | VRAM | Recommended models |
|---------|-----|------|--------------------|
| `cpu-lite` | 8 GB | — | qwen2.5:0.5b, qwen2.5:1.5b |
| `cpu-standard` | 16 GB | — | qwen2.5:3b, qwen2.5:7b, llama3.2:3b |
| `gpu-entry` | 16 GB | 4 GB | qwen2.5:7b, mistral:7b |
| `gpu-mid` | 32 GB | 8 GB | qwen2.5:14b |
| `gpu-high` | 64 GB | 16 GB+ | qwen2.5:32b, deepseek-r1:14b |

Auto-detected by `puma preflight`. Override with `--profile <name>`.

---

## 8. Storage Schema

All results are persisted to `data/puma.db` (SQLite, read by dashboard and report generator):

| Table | Contents |
|-------|---------|
| `runs` | Run ID, spec hash, profile, status, timestamps |
| `instances` | Canonical dataset items (instance_id, gold label, input text) |
| `predictions` | Per-prediction rows: model, strategy, raw response, parsed label, latency, tokens |
| `metrics` | Flat metric name → value per run (for pivot and comparison) |
| `emissions` | CodeCarbon output: kWh, CO₂ kg, duration |
| `profile_snapshots` | Hardware snapshot at run time: CPU, RAM, GPU, Ollama version |

---

## 9. Project Structure

```
puma/
├── src/puma/               # Main package (PYTHONPATH=/app/src)
│   ├── preflight/          # Hardware detection and profile selection
│   ├── runtime/            # OllamaClient, InferenceCache
│   ├── datasets/           # Dataset loaders and verification
│   ├── scenarios/          # Benchmark task definitions
│   ├── adaptation/         # Prompting strategies and example selection
│   ├── perturbations/      # Text perturbation functions
│   ├── metrics/            # All metric computations
│   ├── sustainability/     # CodeCarbon wrapper
│   ├── orchestrator/       # RunSpec, Runner, compare_runs
│   ├── storage/            # SQLAlchemy ORM (6 tables)
│   ├── dashboard/          # Streamlit app (7 views)
│   ├── reporting/          # Markdown + PDF report generation
│   └── cli.py              # Unified CLI entrypoint
├── tests/
│   ├── unit/               # 206 fast tests, no external deps
│   ├── integration/        # Require data files
│   └── smoke/              # AppTest + end-to-end dry-run
├── specs/
│   ├── prompts/            # Jinja2 templates per scenario × strategy
│   ├── runs/               # Example and gate run-specs
│   └── scenarios/          # Scenario YAML specs
├── docs/                   # Extended documentation
├── config/                 # models_catalog.yaml, runtime_profile.yaml
├── data/                   # Datasets and SQLite DB (gitignored)
├── results/                # Run artifacts: runspec.yaml, metrics.json, report.md
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── start_puma.sh
└── pyproject.toml
```

---

## 10. Success Criteria

A user cloning the repo on a machine with 16 GB RAM and Docker can:

1. Run `./start_puma.sh` with no additional configuration.
2. Wait less than 20 minutes for provisioning (model download + dataset verification).
3. Run `puma run specs/runs/smoke_triage.yaml` and see progress in real time.
4. Open `http://localhost:8501` and explore results in the dashboard.
5. Generate a report with `puma report <run_id>`.
6. Compare models with `puma compare <run_id_1> <run_id_2>`.

All of the above: 100% local, fully traceable, with carbon emissions recorded.

---

## 11. Links

| Resource | Path |
|----------|------|
| User guide | [docs/user_guide.md](docs/user_guide.md) |
| Architecture | [docs/architecture.md](docs/architecture.md) |
| Metrics reference | [docs/metrics_reference.md](docs/metrics_reference.md) |
| Scenarios reference | [docs/scenarios_reference.md](docs/scenarios_reference.md) |
| Adding models | [docs/adding_models.md](docs/adding_models.md) |
| Adding scenarios | [docs/adding_scenarios.md](docs/adding_scenarios.md) |
| Troubleshooting | [docs/troubleshooting.md](docs/troubleshooting.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
