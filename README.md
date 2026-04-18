# PUMA — Local LLM Benchmarking for Project Management

**Platform for Understanding & Management with Agents**

PUMA is an open-source, reproducible benchmarking framework for evaluating open large language models on project management tasks: issue triage, story-point estimation, and backlog prioritization. All inference runs locally via [Ollama](https://ollama.ai) — no external API calls, no data leaves your machine.

![Tests](https://img.shields.io/badge/tests-209%20passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Docker](https://img.shields.io/badge/runs%20on-Docker-2496ED)
![Version](https://img.shields.io/badge/version-v2.0.0-orange)

---

## Requirements

| Requirement | Minimum |
|-------------|---------|
| Docker Engine | 24+ |
| Docker Compose | v2 |
| RAM | 8 GB (16 GB recommended) |
| Disk | 10 GB free (for models + data) |
| GPU | Optional — NVIDIA/AMD/Apple Silicon |

> No Python installation needed on the host. Everything runs inside Docker.

---

## Quickstart

```bash
# Clone and provision (downloads models, datasets, applies DB schema)
git clone <repo-url> && cd puma
./start_puma.sh

# Run a benchmark (dry-run — no Ollama needed)
docker compose run --rm puma_runner puma run specs/runs/smoke_triage.yaml --dry-run

# Run a live benchmark (requires Ollama + model)
docker compose run --rm puma_runner puma run specs/runs/smoke_triage.yaml

# Open the dashboard
open http://localhost:8501
```

---

## CLI Reference

All commands run inside the `puma_runner` container:

```bash
docker compose run --rm puma_runner puma <command>
```

Or use the shorthand after `./start_puma.sh`:

```bash
alias puma='docker compose run --rm puma_runner puma'
```

### `puma preflight`

Detect hardware, select an execution profile, and check provisioning readiness.

```bash
puma preflight
puma preflight --profile cpu-standard     # override auto-detection
puma preflight --no-write-config          # skip writing config/runtime_profile.yaml
```

Profiles: `cpu-lite`, `cpu-standard`, `gpu-entry`, `gpu-mid`, `gpu-high`, `auto`.

---

### `puma models`

List or pull models from the catalog.

```bash
puma models list                   # show all catalog models with size and compatible profiles
puma models pull qwen2.5:3b        # pull a specific model via Ollama
```

---

### `puma datasets`

Verify dataset integrity and show statistics.

```bash
puma datasets verify               # check checksums and row counts for all datasets
```

---

### `puma run`

Execute a benchmark defined by a run-spec YAML.

```bash
puma run specs/runs/smoke_triage.yaml
puma run specs/runs/smoke_triage.yaml --dry-run          # skip Ollama, test pipeline
puma run specs/runs/smoke_triage.yaml --ollama-host http://puma_ollama:11434
puma run specs/runs/smoke_triage.yaml --db data/puma.db
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | false | Build prompts and persist results without calling Ollama |
| `--ollama-host` | `http://localhost:11434` | Ollama API base URL (env: `OLLAMA_HOST`) |
| `--db` | `data/puma.db` | SQLite database path |

---

### `puma compare`

Compare metrics across two or more runs.

```bash
puma compare run_id_1 run_id_2
puma compare run_id_1 run_id_2 --output comparison.json
puma compare run_id_1 run_id_2 run_id_3
```

Outputs a Markdown table and, for exactly two runs, shows `run2 − run1` differences per metric.

---

### `puma report`

Generate a Markdown report for a completed run.

```bash
puma report <run_id>
puma report <run_id> --format pdf          # convert via Pandoc (if installed)
puma report <run_id> --db data/puma.db
```

The report is written to `results/<run_id>/report.md` and includes: executive summary, metrics table, per-model breakdown, perturbation analysis, sustainability section, and latency percentiles.

---

### `puma dashboard`

Launch the interactive Streamlit dashboard.

```bash
puma dashboard
puma dashboard --port 8502
```

The dashboard is also available as a persistent Docker service:

```bash
docker compose up -d puma_dashboard
open http://localhost:8501
```

---

### `puma db`

Manage the SQLite database schema.

```bash
puma db migrate               # create or update tables
puma db status                # show database file size
```

---

### `puma cache`

Manage the inference response cache.

```bash
puma cache stats              # show entry count and cache size
puma cache clear              # delete all cached responses
```

---

## Run-Spec Format

Every benchmark is fully described by a YAML run-spec. Example:

```yaml
id: my_benchmark_v1
description: "Triage with few-shot and typo perturbations"
scenario: triage_jira           # triage_jira | estimation_tawos | prioritization_jira
sample_size: 50
models:
  - qwen2.5:3b
  - qwen2.5:1.5b
adaptation:
  strategy:
    - zero-shot
    - few-shot-3
inference:
  temperature: 0.0
  seed: 42
  max_tokens: 256
  logprobs: false
perturbations:
  - typos_5pct                  # also: case_upper, case_lower, truncate_50pct, tech_noise
metrics:
  - f1_macro
sustainability:
  codecarbon: false
repeat: 1
```

Run it:

```bash
puma run my_benchmark_v1.yaml --dry-run    # validate pipeline
puma run my_benchmark_v1.yaml              # live run
```

---

## Scenarios

| Scenario | Task | Dataset | Primary Metric |
|----------|------|---------|----------------|
| `triage_jira` | Assign priority (Critical/Major/Minor/Trivial) to a Jira issue | Jira balanced (200 issues) | F1 macro |
| `estimation_tawos` | Estimate story points (Fibonacci) for a user story | TAWOS (9 020 items) | MAE |
| `prioritization_jira` | Given two issues A/B, which has higher priority? | Jira pairwise | Accuracy |

---

## Prompting Strategies

| Strategy | Key | Description |
|----------|-----|-------------|
| Zero-shot | `zero-shot` | Direct question, no examples |
| Zero-shot CoT | `zero-shot-cot` | Ask model to think step-by-step |
| One-shot | `one-shot` | Single example |
| Few-shot (k=3) | `few-shot-3` | Three stratified examples |
| Few-shot (k=5) | `few-shot-5` | Five stratified examples |
| Few-shot (k=8) | `few-shot-8` | Eight stratified examples |
| Chain-of-Thought few-shot | `cot-few-shot` | Few-shot with CoT rationales |
| RCOIF | `rcoif` | Role + Context + Output + Instruction + Format |
| Contextual Anchoring | `contextual-anchoring` | Grounds prediction to project context |
| Self-Consistency | `self-consistency` | Multiple samples + majority vote (requires temperature > 0) |
| EGI | `egi` | Example-Guided Inference |

---

## Dashboard Views

Open `http://localhost:8501` after `docker compose up -d puma_dashboard`.

| View | Description |
|------|-------------|
| **Overview** | Cards for each run: status, F1, accuracy, parse failure rate |
| **Model Comparison** | Interactive heatmap of all metrics across runs |
| **Reliability** | Reliability diagrams (calibration curves) |
| **Robustness** | Bar chart: prediction consistency under each perturbation |
| **Fairness** | Per-model accuracy breakdown and fairness gap |
| **Sustainability Frontier** | Pareto scatter: F1 vs latency across runs |
| **Instance Drill-down** | Raw LLM response, parsed label, gold label, token counts, prompt hash |

---

## Development

```bash
make build    # build the puma_runner Docker image
make lint     # ruff check + format check (src/puma/ and tests/)
make test     # run unit + integration tests inside Docker
make smoke    # smoke tests (AppTest, no Ollama required)
```

All dev tooling runs inside the container. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Documentation

| Document | Contents |
|----------|---------|
| [docs/architecture.md](docs/architecture.md) | Data flow, package map, Docker services, design decisions |
| [docs/user_guide.md](docs/user_guide.md) | Step-by-step guide: provision → run → compare → report → dashboard |
| [docs/metrics_reference.md](docs/metrics_reference.md) | Formula for every metric (classification, regression, calibration, efficiency) |
| [docs/scenarios_reference.md](docs/scenarios_reference.md) | Scenario specs, parse logic, gold label definition |
| [docs/adding_models.md](docs/adding_models.md) | How to add a model to the catalog |
| [docs/adding_scenarios.md](docs/adding_scenarios.md) | How to implement a new benchmark scenario |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common problems and fixes |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Code conventions, commit format, PR process |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
