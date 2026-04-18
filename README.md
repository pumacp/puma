# PUMA

**Platform for Understanding & Management with Agents** — local, reproducible benchmarking of open LLMs on project management tasks (triage, estimation, prioritization).

![Tests](https://img.shields.io/badge/tests-209%20passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Docker](https://img.shields.io/badge/runs%20on-Docker-2496ED)

## Quickstart (3 commands)

```bash
# 1. Start PUMA services (Ollama + runner + dashboard)
docker compose up -d

# 2. Run a benchmark
docker compose run --rm puma_runner puma run specs/runs/smoke_triage.yaml

# 3. Open the dashboard
open http://localhost:8501
```

> **Requirements**: Docker + docker compose. Hardware: ≥8 GB RAM for CPU-only, ≥4 GB VRAM for GPU-accelerated.

## Features

| Capability | Details |
|------------|---------|
| Scenarios | Triage (Jira), Story-point estimation (TAWOS), Prioritization (Jira) |
| Models | Any model available via Ollama (qwen2.5:3b, llama3.2:3b, mistral:7b, …) |
| Strategies | 9 prompting strategies: zero-shot, CoT, few-shot, RCOIF, EGI, self-consistency, … |
| Perturbations | typos, case changes, truncation, tech noise |
| Metrics | F1, MAE, ECE, robustness, fairness, latency percentiles, CO₂ |
| Dashboard | Streamlit: 7 interactive views including instance drill-down |
| Reports | `puma report <run_id>` → Markdown (+ optional PDF via Pandoc) |

## CLI

```bash
puma preflight              # detect hardware, select execution profile
puma models list            # list compatible models
puma datasets verify        # verify data integrity
puma run <spec.yaml>        # execute a benchmark
puma run <spec.yaml> --dry-run   # build prompts without calling Ollama
puma compare <id1> <id2>    # compare two runs
puma report <run_id>        # generate report.md
puma dashboard              # launch Streamlit on :8501
puma db migrate             # apply DB schema
puma cache stats            # show inference cache
```

## Documentation

- [INDEX.md](index.md) — full project index
- [docs/architecture.md](docs/architecture.md) — data flow and package map
- [docs/metrics_reference.md](docs/metrics_reference.md) — formula for every metric
- [docs/scenarios_reference.md](docs/scenarios_reference.md) — scenario specs
- [docs/adding_models.md](docs/adding_models.md) — adding a model to the catalog
- [docs/adding_scenarios.md](docs/adding_scenarios.md) — implementing a new scenario
- [docs/troubleshooting.md](docs/troubleshooting.md) — common problems and fixes
- [CONTRIBUTING.md](CONTRIBUTING.md) — code conventions and PR process

## Development

```bash
make build    # build Docker image
make lint     # ruff check + format
make test     # run unit + integration tests
make smoke    # smoke tests (requires Ollama)
```

All dev tooling runs inside Docker. See [CONTRIBUTING.md](CONTRIBUTING.md).
