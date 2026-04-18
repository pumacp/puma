# PUMA User Guide

This guide walks through the complete workflow: provisioning → running benchmarks → comparing results → generating reports → exploring the dashboard.

---

## Table of Contents

1. [Installation and provisioning](#1-installation-and-provisioning)
2. [Hardware preflight](#2-hardware-preflight)
3. [Managing models](#3-managing-models)
4. [Managing datasets](#4-managing-datasets)
5. [Writing a run-spec](#5-writing-a-run-spec)
6. [Running a benchmark](#6-running-a-benchmark)
7. [Comparing runs](#7-comparing-runs)
8. [Generating reports](#8-generating-reports)
9. [Using the dashboard](#9-using-the-dashboard)
10. [Managing the database](#10-managing-the-database)
11. [Managing the inference cache](#11-managing-the-inference-cache)
12. [Advanced: perturbations](#12-advanced-perturbations)
13. [Advanced: multiple strategies](#13-advanced-multiple-strategies)
14. [Advanced: sustainability tracking](#14-advanced-sustainability-tracking)

---

## 1. Installation and Provisioning

### Prerequisites

- **Docker Engine 24+** and **Docker Compose v2** installed on the host.
- At least **8 GB RAM** (16 GB recommended for 3B parameter models).
- Internet access for initial model and dataset download.

No Python installation is needed on the host.

### One-shot provisioning

```bash
git clone <repo-url>
cd puma
./start_puma.sh
```

`start_puma.sh` performs six steps automatically:

| Step | Action |
|------|--------|
| 1 | Verify Docker and Docker Compose are available |
| 2 | Build the `puma_runner` Docker image |
| 3 | Run `puma preflight` to detect hardware and select a profile |
| 4 | Start `puma_ollama` and `puma_dashboard` services |
| 5 | Pull the two smallest models for the detected profile |
| 6 | Verify / download datasets and apply the database schema |

**Flags:**

```bash
./start_puma.sh --profile cpu-standard   # override hardware detection
./start_puma.sh --skip-models            # skip model download (models already pulled)
./start_puma.sh --skip-datasets          # skip dataset verification
./start_puma.sh --smoke-only             # run a dry-run smoke test after provisioning
./start_puma.sh --observability          # start optional Grafana overlay
./start_puma.sh --verbose                # print every shell command (set -x)
```

### Accessing the CLI

All `puma` commands run inside the `puma_runner` container:

```bash
docker compose run --rm puma_runner puma <command> [options]
```

For convenience, create an alias:

```bash
alias puma='docker compose run --rm puma_runner puma'
```

---

## 2. Hardware Preflight

Before running benchmarks, PUMA detects your hardware and selects a compatible execution profile.

```bash
puma preflight
```

**Example output:**

```
Hardware capabilities
  CPU:    Intel Core i7-12700K
  RAM:    32.0 GB
  GPU:    NVIDIA RTX 3080 (10.0 GB VRAM)
  Ollama: 0.12.15

Selected profile: gpu-entry

Provisioning checks
  [OK]  Ollama is running
  [OK]  VRAM sufficient for qwen2.5:7b (4.7 GB < 10.0 GB)
  [OK]  Disk space: 87.2 GB free
  [WARN] Ollama version 0.12.15 — logprobs supported

Profile written to config/runtime_profile.yaml
```

**Override the detected profile:**

```bash
puma preflight --profile cpu-standard
```

**Skip writing the config file:**

```bash
puma preflight --no-write-config
```

Profiles and their requirements:

| Profile | RAM | VRAM | Notes |
|---------|-----|------|-------|
| `cpu-lite` | 8 GB | — | Tiny models (≤1.5B) only |
| `cpu-standard` | 16 GB | — | Models up to 7B on CPU |
| `gpu-entry` | 16 GB | 4 GB | 7B models on GPU |
| `gpu-mid` | 32 GB | 8 GB | 14B models |
| `gpu-high` | 64 GB | 16 GB+ | 32B+ models |

---

## 3. Managing Models

### List all catalog models

```bash
puma models list
```

Output shows model tag, parameter count, disk size, and compatible profiles:

```
Model                          Params     Size  Profiles
---------------------------------------------------------------------------
qwen2.5:0.5b                      0.5B   0.4 GB  cpu-lite, cpu-standard, gpu-entry
qwen2.5:1.5b                      1.5B   1.0 GB  cpu-lite, cpu-standard, gpu-entry
qwen2.5:3b                        3.0B   2.0 GB  cpu-standard, gpu-entry, gpu-mid
qwen2.5:7b                        7.0B   4.7 GB  cpu-standard, gpu-entry, gpu-mid
llama3.2:3b                       3.0B   2.0 GB  cpu-standard, gpu-entry, gpu-mid
mistral:7b                        7.0B   4.1 GB  cpu-standard, gpu-entry, gpu-mid
deepseek-r1:7b                    7.0B   4.7 GB  gpu-entry, gpu-mid, gpu-high
```

### Pull a model

```bash
puma models pull qwen2.5:3b
```

This runs `ollama pull` inside the `puma_ollama` container. The model is stored in the shared `ollama_models` volume.

---

## 4. Managing Datasets

### Verify datasets

```bash
puma datasets verify
```

Checks file existence, row counts, and checksums for:
- `data/jira_balanced_200.csv` — 200 Jira issues, 50 per priority class
- `data/tawos_clean.csv` — 9 020 TAWOS agile backlog items

**Example output:**

```
============================================================
PUMA Dataset Verification
============================================================
[OK] jira_balanced_200.csv — 200 rows, 4 classes, hash OK
[OK] tawos_clean.csv — 9020 rows, 10 SP values, hash OK
============================================================
```

If datasets are missing, download them:

```bash
docker compose run --rm puma_runner python scripts/download_datasets.py
```

---

## 5. Writing a Run-Spec

A run-spec is a YAML file that fully defines a benchmark. Place it in `specs/runs/`.

### Minimal example

```yaml
id: quick_triage
description: "Quick zero-shot triage test"
scenario: triage_jira
sample_size: 10
models:
  - qwen2.5:3b
adaptation:
  strategy: [zero-shot]
inference:
  temperature: 0.0
  seed: 42
metrics:
  - f1_macro
```

### Full reference

```yaml
id: full_benchmark_v1              # unique identifier (used in run_id and results path)
description: "Full benchmark"      # human-readable description

scenario: triage_jira              # triage_jira | estimation_tawos | prioritization_jira
sample_size: 50                    # number of dataset instances (1–10000)

models:                            # one or more Ollama model tags
  - qwen2.5:3b
  - qwen2.5:1.5b

adaptation:
  strategy:                        # one or more strategy IDs
    - zero-shot
    - few-shot-3
    - cot-few-shot

inference:
  temperature: 0.0                 # 0.0 for greedy; > 0 required for self-consistency
  seed: 42                         # fixed for reproducibility
  max_tokens: 256                  # maximum tokens in model response
  logprobs: false                  # set true to enable calibration metrics (Ollama ≥0.12.11)
  top_logprobs: 0                  # number of top logprob tokens to return

perturbations:                     # optional: list of text perturbations
  - typos_5pct                     # 5% character substitution
  - case_upper                     # uppercase entire text
  # - case_lower
  # - truncate_50pct
  # - tech_noise

metrics:                           # metrics to compute and store
  - f1_macro
  # - mae (for estimation_tawos)
  # - accuracy

sustainability:
  codecarbon: false                # set true to track CO₂ emissions via CodeCarbon
  country_iso: ESP                 # ISO 3166-1 alpha-3 for carbon intensity lookup

repeat: 1                          # number of independent repeats (for stability metrics)
profile_required: null             # null = use active profile; or force a specific one
```

### Validation rules

- `scenario` must be one of the three registered scenarios.
- `models` must have at least one entry.
- `sample_size` must be between 1 and 10 000.
- `self-consistency` strategy requires `temperature > 0`.
- `perturbations` generates one additional prediction set per perturbation per instance.

---

## 6. Running a Benchmark

### Dry run (no Ollama required)

A dry run builds all prompts, runs the full persistence pipeline, and writes artifacts — but returns `[dry-run]` instead of calling Ollama.

```bash
puma run specs/runs/smoke_triage.yaml --dry-run
```

Use this to validate your run-spec, test the DB schema, and check prompt templates.

### Live run

```bash
puma run specs/runs/smoke_triage.yaml
```

The runner shows a Rich progress bar and structured logs:

```
2026-04-18 12:00:00 [info] run.start  run_id=smoke_triage_v1__abc123__20260418T120000
  smoke_triage_v1__abc123__20260418T120000 ━━━━━━━━━━━━ 20/20 0:01:23

Run complete: smoke_triage_v1__abc123__20260418T120000
Predictions: 40
  f1_macro: 0.6218
  accuracy: 0.6500
  parse_failure_rate: 0.0500
```

### Run artifacts

After a run, results are stored in two places:

**File system (`results/<run_id>/`):**
```
results/smoke_triage_v1__abc123__20260418T120000/
├── runspec.yaml     # frozen copy of the run-spec used
├── metrics.json     # computed metrics as JSON
└── report.md        # generated after puma report (or --report flag)
```

**Database (`data/puma.db`):**
- `runs` — run record with status and timestamps
- `predictions` — one row per model × strategy × instance × perturbation
- `metrics` — flat metric values for dashboard and comparison
- `profile_snapshots` — hardware state at run time

### Custom Ollama host

```bash
puma run spec.yaml --ollama-host http://192.168.1.10:11434
```

The `OLLAMA_HOST` environment variable is also respected.

---

## 7. Comparing Runs

### Compare two runs

```bash
puma compare run_id_1 run_id_2
```

Output:

```
| Metric              | run_id_1 | run_id_2 |
|---------------------|----------|----------|
| accuracy            | 0.6500   | 0.7100   |
| f1_macro            | 0.6218   | 0.6891   |
| parse_failure_rate  | 0.0500   | 0.0250   |

Differences (run2 - run1):
  accuracy: +0.0600
  f1_macro: +0.0673
  parse_failure_rate: -0.0250
```

### Compare three or more runs

```bash
puma compare run_a run_b run_c
```

Produces the comparison table without the `diffs` section.

### Save comparison to file

```bash
puma compare run_id_1 run_id_2 --output comparison.json
```

---

## 8. Generating Reports

```bash
puma report <run_id>
```

The report is written to `results/<run_id>/report.md` and contains:

- **Executive summary** — scenario, models, strategies, sample size, timestamps
- **Metrics table** — all metrics computed for the run
- **Per-model breakdown** — predictions and parse failures per model (if multiple models)
- **Robustness section** — perturbation coverage (if perturbations were used)
- **Sustainability section** — CO₂ and energy data (if CodeCarbon was enabled)
- **Latency section** — p50/p95/p99 latency in ms

### Convert to PDF (requires Pandoc)

```bash
puma report <run_id> --format pdf
```

If `pandoc` and `xelatex` are available inside the container, a `report.pdf` is created alongside `report.md`. If not installed, the command silently produces only the Markdown file.

### Custom database path

```bash
puma report <run_id> --db /path/to/custom.db
```

---

## 9. Using the Dashboard

The dashboard is a read-only Streamlit application that reads directly from `data/puma.db`.

### Start the dashboard service

```bash
docker compose up -d puma_dashboard
open http://localhost:8501
```

Or launch from the CLI:

```bash
puma dashboard
puma dashboard --port 8502 --host 127.0.0.1
```

### Dashboard views

#### Overview

Shows a card for each run. Each card displays:
- Run ID and status
- F1 macro (or accuracy for other scenarios)
- Parse failure rate

Use the **Runs** multiselect in the sidebar to filter which runs appear.

#### Model Comparison

Renders an interactive heatmap: rows are runs, columns are metrics. Color scale is green (high) → red (low) via `RdYlGn`.

Below the heatmap, a raw metrics table is shown with download option (PNG).

#### Reliability

Plots reliability diagrams (calibration curves) comparing model confidence to actual accuracy per bin. Requires `logprobs: true` in the run-spec and Ollama ≥ 0.12.11. Falls back to synthetic data if no logprob data is available.

#### Robustness

For runs with perturbations, shows a bar chart of prediction consistency rates per perturbation type. A consistency rate of 1.0 means the model gives the same answer whether or not the text was perturbed.

#### Fairness

Breaks down accuracy by model. Displays the fairness gap (max − min accuracy across models). When group attributes are available in predictions, per-group metrics are shown.

#### Sustainability Frontier

A Pareto scatter plot of F1 macro (y-axis) vs latency proxy (x-axis). Each point is a run. The ideal model is top-left (high quality, low latency / energy).

#### Instance Drill-down

Select any run and any instance to inspect:
- Gold label (ground truth)
- Parsed label (what PUMA extracted from the response)
- Raw LLM response text
- Latency in ms, token counts (in/out)
- Prompt hash (for cache lookup)

### Sidebar filters

| Filter | Effect |
|--------|--------|
| **Runs** | Restrict all views to selected run IDs |
| **Date range** | Filter runs by start date |
| **Models** | Filter predictions by model name |

---

## 10. Managing the Database

### Apply schema (first time or after updates)

```bash
puma db migrate
```

Lists all created tables:

```
Schema applied to data/puma.db
  table: emissions
  table: instances
  table: metrics
  table: predictions
  table: profile_snapshots
  table: runs
```

### Check database size

```bash
puma db status
```

```
data/puma.db: 1.4 MB
```

### Direct SQL inspection

```bash
docker compose run --rm puma_runner python3 -c "
import sqlite3
conn = sqlite3.connect('data/puma.db')
for (name,) in conn.execute(\"SELECT run_id FROM runs ORDER BY started_at DESC LIMIT 5\"):
    print(name)
"
```

---

## 11. Managing the Inference Cache

PUMA caches Ollama responses by prompt hash in `data/cache/inferences.db`. Cached responses are returned instantly on repeated runs with identical prompts, seeds, and models.

### Show cache statistics

```bash
puma cache stats
```

```
Inference cache: 342 entries, 128.4 KB
```

### Clear the cache

```bash
puma cache clear
```

Use this when you want to force fresh inference (e.g., after updating a model or changing temperature).

---

## 12. Advanced: Perturbations

Perturbations test model robustness by applying text transformations to the input and comparing predictions against the unperturbed baseline.

### Available perturbations

| ID | Effect |
|----|--------|
| `typos_5pct` | Replace 5% of characters with homoglyphs (a→а, o→0, …) |
| `case_upper` | Convert all text to UPPERCASE |
| `case_lower` | Convert all text to lowercase |
| `truncate_50pct` | Keep only the first 50% of the text |
| `tech_noise` | Insert random technical jargon tokens |

### How it works

For each instance, PUMA produces **1 + len(perturbations)** predictions:
- One with the original text (`perturbation = null`)
- One per perturbation (`perturbation = <name>`)

All predictions are stored in the `predictions` table and the Robustness view in the dashboard shows consistency rates.

### Example run-spec with perturbations

```yaml
id: robustness_test
scenario: triage_jira
sample_size: 30
models: [qwen2.5:3b]
adaptation:
  strategy: [zero-shot]
inference:
  temperature: 0.0
  seed: 42
perturbations:
  - typos_5pct
  - case_upper
  - truncate_50pct
metrics: [f1_macro]
```

This generates 30 × 4 = 120 predictions (original + 3 perturbations).

---

## 13. Advanced: Multiple Strategies

Running multiple strategies in a single spec is efficient — the dataset is sampled once and each strategy builds its own prompts from the same rows.

```yaml
id: strategy_comparison
scenario: triage_jira
sample_size: 50
models: [qwen2.5:3b]
adaptation:
  strategy:
    - zero-shot
    - few-shot-3
    - rcoif
    - contextual-anchoring
inference:
  temperature: 0.0
  seed: 42
metrics: [f1_macro, accuracy]
```

This produces 50 × 4 = 200 predictions. After the run, use `puma compare` to see which strategy performs best.

### Self-consistency (majority vote)

Self-consistency samples the model multiple times and takes the majority vote. It requires `temperature > 0`:

```yaml
adaptation:
  strategy: [self-consistency]
inference:
  temperature: 0.7
  seed: 42
```

---

## 14. Advanced: Sustainability Tracking

Enable CodeCarbon to record CO₂ and energy consumption for each run:

```yaml
sustainability:
  codecarbon: true
  country_iso: ESP        # used for regional carbon intensity lookup
```

The `@track_emissions` decorator wraps the inference loop. Emissions are:
- Written to `results/<run_id>/emissions_data.csv`
- Stored in the `emissions` table in `data/puma.db`
- Shown in the report under the **Sustainability** section
- Plotted in the **Sustainability Frontier** dashboard view

### Quality-adjusted cost metric

After a run with emissions tracking, PUMA computes:

```
gCO₂_per_F1_point = total_gCO₂ / (f1_macro × 100)
```

This lets you compare models not just by accuracy but by their carbon cost per unit of quality gained.

---

## Quick Reference Card

```bash
# Provision a clean machine
./start_puma.sh

# Hardware check
puma preflight

# List available models
puma models list

# Pull a model
puma models pull qwen2.5:3b

# Verify datasets
puma datasets verify

# Dry-run (no Ollama needed)
puma run specs/runs/smoke_triage.yaml --dry-run

# Live benchmark
puma run specs/runs/smoke_triage.yaml

# Compare two runs
puma compare <run_id_1> <run_id_2>

# Generate a report
puma report <run_id>

# Generate a PDF report
puma report <run_id> --format pdf

# Open the dashboard
open http://localhost:8501   # (or puma dashboard)

# Database schema
puma db migrate
puma db status

# Inference cache
puma cache stats
puma cache clear
```
