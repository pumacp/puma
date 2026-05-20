<p align="center">
  <img src="https://raw.githubusercontent.com/pumacp/puma/main/assets/img/PUMA.png" alt="PUMA Logo" width="220">
</p>

<h1 align="center">PUMA</h1>

<p align="center">
  <em>Local LLM benchmarking platform for ICT Project Management tasks. Reproducible by design, sustainability-aware, fully open-source.</em>
</p>

<p align="center">
  <!-- Group A: build & quality -->
  <a href="https://github.com/pumacp/puma/actions/workflows/lint-and-test.yml">
    <img src="https://github.com/pumacp/puma/actions/workflows/lint-and-test.yml/badge.svg" alt="Lint and test">
  </a>
  <img src="https://img.shields.io/badge/python-3.11+-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License: MIT">
  <img src="https://img.shields.io/badge/runs%20on-Docker-2496ED?logo=docker&logoColor=white" alt="Runs on Docker">
  <br>
  <!-- Group B: methodology & ecosystem -->
  <a href="https://codecarbon.io">
    <img src="https://img.shields.io/badge/sustainability-CodeCarbon-2EA44F" alt="CodeCarbon">
  </a>
  <a href="https://ollama.com">
    <img src="https://img.shields.io/badge/inference-Ollama-7C3AED" alt="Ollama">
  </a>
  <a href="https://github.com/pumacp/puma/releases/latest">
    <img src="https://img.shields.io/github/v/tag/pumacp/puma?label=release" alt="Latest release">
  </a>
  <br>
  <!-- Group C: community -->
  <a href="https://github.com/pumacp/puma-community">
    <img src="https://img.shields.io/badge/PUMA-Community-orange" alt="PUMA Community">
  </a>
</p>

<p align="center">
  <a href="../../wiki">Wiki</a> ·
  <a href="https://github.com/pumacp/puma-community">PUMA Community</a> ·
  <a href="CONTRIBUTING.md">Contribute</a> ·
  <a href="../../issues">Issues</a>
</p>

---

## Overview

PUMA is a local-first benchmarking platform for open-weight language models on
ICT Project Management tasks. PUMA runs entirely on your hardware via
[Ollama](https://ollama.com); it never calls an external inference API and
never needs an account or token to evaluate a model. The platform exercises
two production scenarios end to end — **issue triage** (multi-class
classification on the Jira Social Repository dataset) and **effort estimation**
(story-point regression on the TAWOS dataset) — plus an experimental
backlog-prioritisation scenario. Every run reports both quality metrics
(F1-macro, accuracy, MAE, MdAE, calibration / ECE, confusion matrix) and a
full sustainability footprint (CO2 grams, energy kWh, tracking mode) via
[CodeCarbon](https://codecarbon.io). Results are persisted to a local SQLite
database with a bi-temporal schema so historical runs are reproducible
bit-exact. Users who want to share their evaluations can publish to the
companion data hub at
[`pumacp/puma-community`](https://github.com/pumacp/puma-community) with a
single CLI command.

## Features

- **Local-first execution via Ollama.** CPU-only and GPU configurations
  supported on Linux; native Apple Silicon support on macOS.
- **Two production scenarios:** `triage_jira` (issue classification) and
  `effort_tawos` (story-point estimation), plus experimental
  `prioritization_jira`.
- **Multi-strategy prompting:** zero-shot, zero-shot-CoT, few-shot (k=3 / k=6),
  CoT few-shot, RCOIF, contextual anchoring, EGI, self-consistency.
- **Multi-dimensional metrics:** F1-macro, accuracy, MAE, MdAE, ECE, per-class
  breakdown, confusion matrix, Wilcoxon signed-rank pairwise tests.
- **Sustainability tracking** via CodeCarbon with chip-aware tracking modes on
  Apple Silicon and Linux.
- **15 hardware profiles** spanning CPU-only, GPU-equipped, and Apple Silicon
  M3 / M4 / M5 generations; 17 supported model tags in the catalog.
- **Streamlit dashboard** for browsing runs, comparing models, exploring
  metrics, and publishing results to PUMA Community.
- **Reproducible by design:** deterministic seed, temperature 0.0,
  Ollama logprobs API for calibration, predictions-hash integrity check.

## Quick start

### Docker (recommended)

```bash
git clone https://github.com/pumacp/puma.git
cd puma
docker compose up -d
```

Run a benchmark:

```bash
docker compose run --rm puma_runner puma run \
  --scenario triage_jira \
  --model qwen2.5:3b \
  --strategy zero_shot \
  --instances 50
```

Open the dashboard:

```bash
docker compose run --rm -p 8501:8501 puma_runner \
  streamlit run src/puma/dashboard/app.py
# Then open http://localhost:8501
```

### Manual install (advanced)

```bash
git clone https://github.com/pumacp/puma.git
cd puma
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
# Install Ollama separately: https://ollama.com/download
puma --help
```

### Share your results with the community (optional)

```bash
puma auth login github                       # store a Personal Access Token (one-off)
puma share-results --dry-run --run-id <id>   # preview the payload as a local JSON file
puma share-results --run-id <id>             # fork, branch, commit, and open the PR
```

The tool builds the payload from your local SQLite results, scans for
personal data, signs the integrity hash, and opens the Pull Request on
your behalf against
[`pumacp/puma-community`](https://github.com/pumacp/puma-community).

## CLI overview

The `puma` entry point exposes a Typer-based hierarchy of commands. The most
useful top-level commands:

- `puma preflight` — detect hardware capabilities and select an execution
  profile.
- `puma models` — list supported model tags from the catalog or pull a tag
  via Ollama.
- `puma run` — execute a benchmark for a given scenario / model / strategy.
- `puma compare` — compare two runs side by side.
- `puma validate-baseline` — verify reproducibility against a published
  baseline.
- `puma list-runs` — show the runs stored in the local SQLite database.
- `puma list-ollama-models` — show locally-installed Ollama tags.
- `puma prepare-datasets` — fetch and pre-process the supported datasets.
- `puma wilcoxon` — Wilcoxon signed-rank pairwise comparison.
- `puma bias-analysis` — gendered-prefix robustness sweep.
- `puma generate-plots` — render result plots (Sustainability Frontier,
  reliability diagrams, etc.).
- `puma db` — inspect or migrate the local results database
  (`migrate`, `downgrade`, `history`, `status`).
- `puma auth` — manage credentials for community publishing
  (`login`, `status`, `logout`).
- `puma share-results` — publish a run to PUMA Community.
- `puma dashboard` — launch the Streamlit dashboard.

## Architecture

The platform is organised in layered modules under `src/puma/`:

- **Orchestrator** schedules instances against the model under test, applies
  the chosen prompting strategy, and records per-prediction latency.
- **Inference cache** keeps runs deterministic by caching `(prompt, seed,
  model)` results when the user explicitly opts in.
- **Scenarios** are pluggable task modules — `triage`, `effort`,
  `prioritization` — each owning its prompt templates and label space.
- **Metrics engine** computes performance, calibration, sustainability, and
  pairwise-test metrics on top of the stored predictions.
- **Storage** is a SQLite database with a bi-temporal schema (`runs`,
  `instances`, `predictions`, `metrics`, `emissions`, `profile_snapshots`)
  managed by SQLAlchemy + Alembic.
- **Dashboard** is a Streamlit app with eight views (Overview, Model
  Comparison, Reliability, Robustness, Fairness, Sustainability Frontier,
  Instance Drill-down, and PUMA Community).
- **Community integration** composes the data-layer modules with a
  credential store, a local rate limiter, and a narrow PyGithub wrapper to
  open Pull Requests against `pumacp/puma-community`.

## Repository structure

```
puma/
├── .github/workflows/    # CI: lint-and-test, smoke, release
├── alembic/              # Database migrations
├── assets/img/           # Logo and visual assets
├── config/               # Hardware profiles and model catalog
├── data/                 # SQLite database and cache (gitignored)
├── docs/                 # Internal documentation
├── scripts/              # Helper scripts
├── src/puma/             # Python source
│   ├── cli.py            # Top-level CLI entry point
│   ├── community/        # PUMA Community submission flow
│   ├── dashboard/        # Streamlit dashboard and views
│   ├── orchestrator/     # Run scheduling and run-spec parsing
│   ├── scenarios/        # Task modules (triage, effort, prioritization)
│   ├── metrics/          # Metric computation
│   ├── sustainability/   # CodeCarbon integration
│   ├── preflight/        # Hardware detection and profile selection
│   └── storage/          # SQLite ORM (SQLAlchemy + Alembic)
├── tests/                # pytest suite (unit, integration, smoke, community)
├── CODE_OF_CONDUCT.md    # Contributor Covenant v2.1
├── CONTRIBUTING.md       # Development guide
├── docker-compose.yml    # Docker stack definition
├── Dockerfile            # Runner image
├── LICENSE               # MIT
├── pyproject.toml        # Package metadata and dependencies
└── README.md             # This file
```

## Documentation

- [Contributing guide](CONTRIBUTING.md) — development setup, tests, commit
  conventions, PR process.
- [Code of Conduct](CODE_OF_CONDUCT.md) — Contributor Covenant v2.1.
- [PUMA Community](https://github.com/pumacp/puma-community) — public hub
  for community-contributed benchmark results.
- [Wiki](../../wiki) — extended documentation (when populated).
- [Releases](../../releases) — semantic-versioned releases and changelogs.

## Related projects

- [**PUMA Community**](https://github.com/pumacp/puma-community) — companion
  data repository for community submissions, with auto-validation and
  outward mirrors to Hugging Face, Zenodo, and Kaggle.
- [**Ollama**](https://ollama.com) — local LLM runtime that PUMA delegates
  to for all model execution.
- [**CodeCarbon**](https://codecarbon.io) — sustainability tracking library
  PUMA uses for energy and emissions reporting.
- **Datasets used** — Jira Social Repository (Zenodo
  [DOI 5901893](https://zenodo.org/records/5901893)) and TAWOS.

## Citation

If you use PUMA in your work, please cite the repository:

```bibtex
@software{puma_project,
  author  = {{PUMA Project contributors}},
  title   = {PUMA: PUMA Understanding and Management with Agents},
  url     = {https://github.com/pumacp/puma},
  version = {2.7.0},
  year    = {2026}
}
```

Update `version` to match the tag you used.

## License

PUMA is released under the MIT License. See [`LICENSE`](LICENSE) for the
full text. Third-party dependencies retain their own licenses; the
canonical list lives in [`pyproject.toml`](pyproject.toml).

## Code of Conduct

This project follows the
[Contributor Covenant v2.1](CODE_OF_CONDUCT.md). Conduct concerns can be
reported privately to `pumacapstoneproject@gmail.com`.
