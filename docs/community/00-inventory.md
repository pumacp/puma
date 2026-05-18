# PUMA Community v1 — Inventory (Prompt 0)

**Generated:** 2026-05-18
**Branch at time of inventory:** `feature/community-v1` (just created from `develop@321ff26`)
**Academic safety tag:** `v2.7.0-academic` (annotated, local, not pushed)
**Repository baseline:** v2.7.0 (latest tag on `origin/main` is `v2.7.0`; `develop` is one
commit ahead with the technical-closure document).

This document is the read-only inventory required by Prompt 0 of the PUMA Community v1
implementation plan. **No source file was modified.** This file is the only addition.

---

## 1. Top-level directory structure (depth 2)

```
.
├── .claude/                       # Claude Code config (gitignored)
├── .git/
├── .githooks/                     # Project-managed commit-msg hooks
├── .github/
│   └── workflows/                 # 3 workflows: lint-and-test.yml, release.yml, smoke.yml
├── .gitnexus/                     # GitNexus index (gitignored)
├── .ruff_cache/, .pytest_cache/   # tooling caches (gitignored)
├── .streamlit/                    # Streamlit local config
├── alembic/
│   └── versions/                  # Alembic migrations (DB schema source of truth)
├── assets/                        # Logos, images
├── config/                        # Runtime configs (profiles.yaml, models_catalog.yaml)
├── data/                          # Datasets + runtime DB (puma.db is untracked)
│   └── cache/                     # Inference cache (untracked)
├── db/                            # Placeholder only — large dumps NOT committed
├── docs/
│   ├── RELEASES/                  # v2.1.0.md … v2.7.0.md
│   ├── internal/                  # Internal notes (gitignored)
│   └── results/                   # Generated figures + result write-ups
├── logs/
├── results/                       # 431 sub-directories — historic run artefacts (gitignored)
├── scripts/                       # Helper scripts (prepare_datasets.py, generate_phase_b_plots.py …)
├── specs/                         # SDD specs (single source of truth)
│   ├── prompts/                   # Prompt templates
│   ├── runs/                      # Run-spec YAMLs (baseline_triage.yaml, …)
│   └── scenarios/                 # Scenario configs
├── src/
│   ├── puma/                      # **All package code (src layout)**
│   └── puma.egg-info/             # Build artefact
└── tests/
    ├── cli/                       # CLI command tests (6 files)
    ├── integration/               # Integration tests (8 files)
    ├── smoke/                     # Smoke (1 file)
    ├── unit/                      # Unit tests (29 test_*.py files, flat — no subfolders)
    └── conftest.py                # Single top-level pytest fixture file
```

Top-level files at repo root: `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md` (1100+ lines),
`CONTRIBUTING.md`, `INDEX.md`, `README.md`, `Makefile`, `Dockerfile`,
`docker-compose.yml`, `pyproject.toml`, `pytest.ini`, `requirements.txt`,
`requirements-dev.txt`, `alembic.ini`, `start_puma.sh`, `stop_puma_native.sh`,
`.gitignore`, `.pre-commit-config.yaml`, `.env`, `.env.example`.

`results/` count: **431 subdirectories** (e.g. `b3_sweep__gemma3_12b__estimation_tawos__…`).
Not expanded.

---

## 2. Key files read (summary)

### `README.md` (first 100 lines)

Title: **PUMA — Project Understanding and Management with Agents**.
Badges: tests=407 passing, version=v2.7.0, python=3.11+, license=MIT, runs-on Docker.
Status table lists v2.7.0, 407 tests, **58 %** coverage (badge claims 61 % elsewhere —
both numbers live in different files, see §Surprises). Section headers visible in the first
100 lines: *Related resources*, *Status*, *Requirements*, *Quickstart*, *CLI Reference*
(begins around line 81 with `puma preflight`, `puma models`, …).

### `pyproject.toml` (FULL)

- **`name = "puma"`**
- **`version = "2.1.0-dev"`**  ← STALE (git tag is v2.7.0). *No* `setuptools_scm` or
  `hatch-vcs` configuration; version is **NOT derived from git tags**. The canonical version
  string in code lives in three disjoint places that already disagree (see §Surprises).
- `requires-python = ">=3.11"`, license MIT.
- Runtime deps (alphabetised): `alembic≥1.13`, `codecarbon≥2.4`, `httpx≥0.27`,
  `jinja2≥3.1`, `langdetect≥1.0.9`, `numpy≥1.26`, `pandas≥2.2`, `psutil≥5.9`,
  `pydantic≥2.7`, `pyyaml≥6.0`, **`requests≥2.31`** (already present),
  `rich≥13.7`, `scikit-learn≥1.4`, `scipy≥1.13`, `sqlalchemy≥2.0`, `streamlit≥1.35`,
  `structlog≥24.1`, `typer≥0.12`.
- Optional `dev` extras: `pytest≥8.2`, `pytest-cov≥5.0`, `pytest-asyncio≥0.23`,
  `respx≥0.21`, **`ruff==0.15.12`** (pinned), `mypy≥1.10`, `pre-commit≥3.7`.
- `[project.scripts] puma = "puma.cli:app"`.
- `[tool.setuptools.packages.find] where = ["src"]` — confirms src layout.
- `[tool.ruff]` line-length=100, target-version=py311, src=["src","tests"], excludes
  `src/cleanup.py`, `src/data_prep.py`, `src/evaluate_estimation.py`, `src/evaluate_triage.py`,
  `agents/`, `scripts/`; selects `E F W I UP B C4 PT SIM RUF`, ignores `E501`.
- `[tool.mypy]` strict=false; `puma.metrics.*`, `puma.runtime.*`, `puma.preflight.*`
  upgraded to `strict = true`.
- `[tool.pytest.ini_options]` testpaths=tests, strict-markers; markers `integration`,
  `unit`, `slow`, `ollama`, `smoke`, `requires_gpu`.
- `[tool.isort]` profile=black, line_length=100.

### `requirements.txt`

Mirrors pyproject runtime deps plus `matplotlib≥3.8` and `seaborn≥0.13` (not declared in
`pyproject.dependencies` — divergence between the two files exists).

### `requirements-dev.txt`

`pytest≥8.2`, `pytest-cov≥5.0`, `pytest-asyncio≥0.23`, `respx≥0.21`, `ruff==0.15.12`,
`mypy≥1.10`, `pre-commit≥3.7`.

### `pytest.ini`

Same `testpaths = tests`, same six markers as in `pyproject.toml` (duplicated).
`filterwarnings = ignore::DeprecationWarning` (`[tool:pytest]` block).

### `Makefile` (FULL — targets and commands)

```
COMPOSE = docker compose
RUNNER  = $(COMPOSE) run --rm puma_runner

build       → $(COMPOSE) build puma_runner
lint        → $(RUNNER) ruff check src/ tests/
            → $(RUNNER) ruff format --check src/ tests/
fmt         → $(RUNNER) ruff format src/ tests/
            → $(RUNNER) ruff check --fix src/ tests/
typecheck   → $(RUNNER) mypy src/puma/metrics src/puma/runtime src/puma/preflight || true
test        → $(RUNNER) pytest tests/unit/ tests/integration/ -v
smoke       → $(RUNNER) pytest tests/smoke/ -v -m smoke
up          → $(COMPOSE) up -d puma_ollama puma_runner
down        → $(COMPOSE) down
clean       → find __pycache__ + *.pyc → remove
uninstall   → docker compose down --remove-orphans --volumes; rmi puma-*; rm -rf results/ logs/ …
reinstall   → uninstall + bash start_puma.sh
```

**Canonical test invocation = `make test`** (which is
`docker compose run --rm puma_runner pytest tests/unit/ tests/integration/ -v`).
Note: `make test` runs **only** `unit/` + `integration/`; `tests/cli/` and `tests/smoke/`
are NOT included in the default `test` target.

### `src/puma/__init__.py`

```python
__version__ = "2.0.0-dev"
```

**STALE** — does not match `pyproject.toml` (`2.1.0-dev`) nor the git tag (`v2.7.0`).

### `src/puma/cli.py` (1010 lines, single file)

- **Typer app instance:** `app = typer.Typer(name="puma", help="…", no_args_is_help=True)`
  at **line 7**.
- **Existing `app.add_typer` registration:** `db_app` is registered **inline mid-file**
  at **line 309** (`app.add_typer(db_app, name="db")`).
- **Bottom of file:** `if __name__ == "__main__": app()` at **lines 1009-1010**.
- **Natural extension point for new sub-typers (e.g. `auth_app`, `share_results_app`):**
  insert **after line 1007** (the blank line that follows the last command body) and
  **before line 1009** (the `if __name__ == "__main__":` block).

#### Ordered top-level CLI commands

| # | Line | Decorator name             | Function                  | Docstring headline |
|---|------|----------------------------|---------------------------|---------------------|
| 1 | 14   | `@app.command()`           | `preflight`               | Detect hardware, select execution profile, and report readiness. |
| 2 | 58   | `@app.command(name="models")` | `models_cmd`           | List available models for the current profile, or pull a specific model. |
| 3 | 97   | `@app.command()`           | `datasets`                | Verify dataset integrity and show statistics. |
| 4 | 118  | `@app.command()`           | `cache`                   | Manage the inference cache. |
| 5 | 140  | `@app.command()`           | `run`                     | Execute a benchmark run-spec. |
| 6 | 186  | `@app.command(name="validate-baseline")` | `validate_baseline` | Validate a canonical baseline metric (F1 or MAE) against its reference. |
| 7 | 276  | `@app.command()`           | `compare`                 | Compare metrics across two or more runs. |
| — | 304-309 | `db_app = typer.Typer(...)` + `app.add_typer(db_app, name="db")` | — | Sub-typer registration (mid-file). |
| 7a | 312 | `@db_app.command("migrate")` | `db_migrate`            | Apply Alembic migrations up to the target revision. |
| 7b | 327 | `@db_app.command("downgrade")` | `db_downgrade`        | Reverse Alembic migrations down to the target revision. |
| 7c | 342 | `@db_app.command("history")` | `db_history`            | Show the Alembic revision chain for the database. |
| 7d | 355 | `@db_app.command("status")`  | `db_status`             | Show the database file status. |
| 8 | 369  | `@app.command()`           | `dashboard`               | Launch the Streamlit dashboard. |
| 9 | 395  | `@app.command()`           | `report`                  | Generate a Markdown (or PDF) run report. |
| 10 | 415 | `@app.command(name="list-runs")` | `list_runs`         | List runs registered in the database with their headline metrics (Anexo F § A.2.5). |
| 11 | 536 | `@app.command(name="list-ollama-models")` | `list_ollama_models` | List models effectively present in the Ollama volume (Anexo F § A.2.6). |
| 12 | 600 | `@app.command(name="prepare-datasets")` | `prepare_datasets` | Prepare canonical datasets (Anexo F § A.2.1). |
| 13 | 669 | `@app.command(name="wilcoxon")` | `wilcoxon_cmd`      | Wilcoxon signed-rank pairwise comparison of two runs (Anexo F § A.2.2). |
| 14 | 795 | `@app.command(name="bias-analysis")` | `bias_analysis_cmd` | Bias analysis from perturbed runs already in DB (Anexo F § A.2.3). |
| 15 | 958 | `@app.command(name="generate-plots")` | `generate_plots_cmd` | Generate consolidated plots from runs in the DB (Anexo F § A.2.4). |

### `src/puma/dashboard/app.py` (155 lines)

- Streamlit entry point. No `if __name__` — Streamlit imports this module directly.
- **Views registry is a dict named `VIEWS`** at **lines 29-37**:

  ```python
  VIEWS = {
      "📊 Overview":              overview.render,           # line 30
      "🆚 Model Comparison":      model_comparison.render,   # line 31
      "🎯 Reliability":           reliability.render,        # line 32
      "🛡️ Robustness":            robustness.render,         # line 33
      "⚖️ Fairness":              fairness.render,           # line 34
      "🌱 Sustainability Frontier": sustainability.render,   # line 35
      "🔍 Instance Drill-down":   instance_drilldown.render, # line 36
  }
  ```

- View dispatch: `VIEWS[selected_view]()` at **line 155** (last line of file).
- Selection control: `st.sidebar.radio("View", list(VIEWS.keys()))` at line 80.
- **Insertion point for a "Community" view entry**: add a new key/value inside the dict
  **between lines 36 and 37** (i.e. just before the closing `}` on line 37). The view's
  position in the radio menu equals its position in the dict (Python 3.7+ insertion order).

### `src/puma/dashboard/views/` — view modules

`__init__.py` re-exports the seven view modules. Each module exposes a `render()` function:

| View module | `render()` line |
|-------------|-----------------|
| `overview.py`            | 23 |
| `model_comparison.py`    | 16 |
| `reliability.py`         | 14 |
| `robustness.py`          | 15 |
| `fairness.py`            | 16 |
| `sustainability.py`      | 13 |
| `instance_drilldown.py`  | 16 |

### `src/puma/storage/models.py`

SQLAlchemy 2.0 Mapped-style ORM. `class Base(DeclarativeBase)` at line 34. Naming
convention dict at lines 21-27 (Alembic-friendly).

| Class            | `__tablename__`        | Primary column(s)                    |
|------------------|------------------------|--------------------------------------|
| `Run`            | `runs`                 | `run_id` (String 64)                 |
| `Instance`       | `instances`            | `instance_id` (String 64); unique `(dataset, source_id)` |
| `Prediction`     | `predictions`          | `pred_id` (Integer autoincrement) — FKs `run_id`, `instance_id` |
| `Metric`         | `metrics`              | `metric_id` (Integer autoincrement) — FK `run_id` |
| `Emission`       | `emissions`            | `emission_id` (Integer autoincrement) — FK `run_id` |
| `ProfileSnapshot`| `profile_snapshots`    | `snapshot_id` (Integer autoincrement) — FK `run_id` unique |

`ProfileSnapshot` already contains a `puma_version: String(32)` column. This is the
natural field a federation client would need to read (already populated by the runner).

### `src/puma/storage/db.py`

- Schema lifecycle is **Alembic-driven** (decision I3: no `Base.metadata.create_all`
  fallback).
- Helpers: `init_db(db_path)`, `get_engine()`, `get_session_factory()`,
  **`session_scope()`** (context manager that commits / rolls back / closes).
- Tests should obtain sessions via the **`session_scope()`** context manager (preferred)
  or via `get_session_factory()()`.

### `src/puma/orchestrator/runspec.py`

- Imports `from pydantic import BaseModel, Field, model_validator`. The use of
  `model_validator` confirms **Pydantic v2**. `requires` pyproject pins `pydantic>=2.7`.
- Uses `Literal` for `VALID_SCENARIOS = Literal["triage_jira", "estimation_tawos",
  "prioritization_jira"]`.

### `CHANGELOG.md` — headers of v2.0.0 → v2.7.0 (release dates)

| Version | Date       | Summary headline |
|---------|------------|-------------------|
| 2.7.0   | 2026-05-16 | Sprint 10 — catalog expansion (Qwen3 dense + MoE) + formal Kimi K2.6 exclusion |
| 2.6.0   | 2026-05-16 | Sprint 9 — Apple Silicon M3/M4/M5 detection + native runtime mode |
| 2.5.0   | 2026-05-16 | Sprint 8 — hardening (I5-I10) |
| 2.4.0   | 2026-05-13 | Sprint 7 — CLI completeness for Anexo F |
| 2.3.0   | 2026-05-13 | Sprint 6 — dashboard polish + structural refactor |
| 2.2.0   | 2026-05-13 | Workflow consolidation |
| 2.1.0   | 2026-05-10 | Multi-model sweep |
| 2.0.0   | 2026-05-10 | Foundations |

### `docs/RELEASES/v2.{3,4,5,6,7}.0.md` (headlines)

| File | Headline (first lines) |
|------|------------------------|
| v2.3.0.md | "Sprint 6 (dashboard polish + structural refactor) and retrospective documentation work (INDEX.md + …)." |
| v2.4.0.md | "Sprint 7 (CLI completeness for Anexo F) onto the v2.3.0 base. Resolves the long-standing gap between the academic anexo and the CLI." |
| v2.5.0.md | "Sprint 8 (hardening) onto the v2.4.0 base. Resolves the six inconsistencies (I5–I10) detected." |
| v2.6.0.md | "Sprint 9 (Apple Silicon M3/M4/M5 support) onto the v2.5.0 base. Adds first-class detection of Apple Silicon." |
| v2.7.0.md | "Sprint 10 (catalog expansion) onto the v2.6.0 base. Adds two Alibaba Qwen3 family entries." |

### `.gitignore` (verification of expected patterns)

- `__pycache__/` ✓ (line 13)
- `*.egg-info/` ✓ (line 18)
- `.pytest_cache/` ✓ (line 28)
- `data/cache/` ✗ — **not explicitly ignored.** `data/.gitkeep` and `data/README.md` are
  whitelisted via `!data/.gitkeep` / `!data/README.md`, but `data/cache/` is currently
  untracked simply because nothing was ever staged from it. **Federation tooling that writes
  to `data/cache/` MUST add an explicit `data/cache/` ignore line.**
- `data/puma.db` ✗ — **not explicitly ignored either.** Same situation. **Federation tooling
  MUST NOT publish or stage `data/puma.db`; this needs an explicit ignore.**
- `.streamlit/cache/` ✓ (line 65)
- `emissions.csv` ✓ (line 68)

### `docker-compose.yml` (FULL, NOT modified)

Three services + one network + two volumes (`ollama_models`, `puma_data`):

- **`puma_ollama`** — `ollama/ollama:latest`, port 11434, healthcheck, NVIDIA CDI GPU passthrough.
- **`puma_runner`** — builds from `Dockerfile`, mounts repo at `/app` and `puma_data` at
  `/app/data`, `PYTHONPATH=/app/src`, depends on `puma_ollama` healthy. NVIDIA CDI GPU
  passthrough. Command: `tail -f /dev/null` (long-lived, for `docker compose run` invocations).
- **`puma_dashboard`** — same Dockerfile, port 8501, runs
  `streamlit run src/puma/dashboard/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true`.
- Network: `puma_network` (driver=bridge, name=puma_network).

### `docs/PROJECT_TECHNICAL_CLOSURE.md` (headers + conclusion)

Sections: *Releases published (8)*, *Quality metrics at closure*, *Defensive invariants
enforced by tests* (gemma4 exclusions × 2 + 3 qwen3 pending-validation guards), *Open
hypotheses (formalised)* (H0-H3 cross-arch reproducibility), *Empirical validation pending
(post-defence work)*, *Methodology preserved across the full release sequence*, *Formally
excluded from v2.7.0 catalog* (Kimi K2.6), *Deferred to future Sprints*, *Rationale for
closure at v2.7.0*.

**Closure conclusion (verbatim):**

> "The originally-planned multi-Sprint scope (Sprint 8 hardening + Sprint 9 Apple Silicon
> + Sprint 10 catalog expansion) is complete. Every quality gate passes. … Further
> technical work would introduce risk of regression on 407 passing tests without empirical
> contrapartida on the validation hardware available to the project. The marginal value of
> further infrastructure work is now exceeded by the marginal value of memoria redaction
> for the TFG defence cycle."

The closure document explicitly contemplates future **additive** work post-defence; the
federation v1 fits this profile if introduced under a strict opt-in mechanism that does not
touch the empirical pipeline.

---

## 3. ADR (Architectural Decision Records) location

| Candidate path                    | Exists? |
|-----------------------------------|---------|
| `docs/decisions/`                 | NO      |
| `docs/architecture/decisions/`    | NO      |
| `docs/adr/`                       | NO      |
| `specs/decisions/`                | NO      |
| `**/ADR-*.md` (any path)          | NO      |

**No ADR convention exists in the repository.** Cross-cutting decisions are currently
captured in three places that all coexist:

1. **`specs/*.md`** for spec-level decisions (single source of truth per SDD philosophy).
2. **`docs/RELEASES/v*.md`** for per-release rationale (Sprints 4-10 enshrine each
   non-trivial decision in the release notes).
3. **`CHANGELOG.md`** entries are organised as `Added / Changed / Fixed / Preserved
   (regression guards) / Empirical validation status / Highlights` and contain the
   condensed why-statements.

**Proposed home for ADR-005 (federation):**
**`docs/decisions/`** as a new directory.

Rationale for choosing `docs/decisions/` over `specs/decisions/`: `specs/` is the
SDD single-source-of-truth zone — every file there is normative and binds the empirical
pipeline ("All generated code must pass pytest before merge", "Mandatory reproducibility:
seed=42, temperature=0.0"). The federation v1 is by design **non-normative for the
academic artefact**: it is opt-in, side-channel, and must NOT bind the benchmark
pipeline. Placing ADR-005 under `docs/decisions/` keeps `specs/` semantically pure (any
file inside `specs/` continues to bind the benchmark) and creates a clean home for future
ADRs that are about *project* decisions rather than *benchmark* decisions.

---

## 4. `specs/constitution.md` and `specs/architecture.md`

### `specs/constitution.md` (12 lines — every line is normative)

Role: **Project constitution.** Verbatim principles the federation MUST NOT contradict:

- *Single source of truth: the .spec.md files.*
- *All generated code must pass pytest before merge.*
- *Mandatory reproducibility: seed=42, temperature=0.0.*
- *Output always in the JSON Schema defined in each spec.*
- *Measure CodeCarbon in every experimental run.*
- *Human-in-the-loop: no final action without human validation.*
- *License: MIT.*
- *Methodology: Spec-First Development (SDD).*
- *Context: RAG + Context Engineering for optimised prompts.*

→ The federation must be **opt-in** (HITL), produce its own JSON-schema-validated payloads
(if it persists anything), and MUST NOT silently mutate run-time behaviour or reduce
reproducibility guarantees.

### `specs/architecture.md` (38 lines)

Role: **Project architecture.** Documents the agent-graph topology (Orchestrator → Triage
/ Estimation / CodeGen / Tester / Reviewer), the SDD workflow loop, the RAG/ChromaDB layer,
Docker + Ollama + CodeCarbon stack, and the reproducibility contract
(*"docker-compose down && up must produce identical results"*).

→ The federation must respect: (a) **identical-results contract** — no side-effect of
publishing a result may change the next run's output; (b) **no extra agents** are introduced
on the inference path.

---

## 5. CI workflows present (`.github/workflows/`)

| Workflow | Triggers | What it does |
|----------|----------|--------------|
| `lint-and-test.yml` | push/PR on `main`,`develop` | Job 1: ruff lint + ruff format check + `pytest tests/unit/ -q` + `pytest tests/integration/ -q -m "not ollama"`. Job 2 (`integration-tests-ollama`, push-only, `continue-on-error: true`): installs Ollama, pulls `qwen2.5:1.5b`, runs `pytest tests/ -m ollama`. |
| `release.yml`       | push of tag `v*` | Builds wheel via `python -m build --wheel`, uploads to existing GitHub Release (manual creation expected first). |
| `smoke.yml`         | push/PR on `main`,`develop` + manual | Installs Ollama, pulls `qwen2.5:0.5b`, `pytest tests/smoke/ -m smoke`, dry-run benchmark via inline Python. |

→ Federation CI work should land **as an additional job** in `lint-and-test.yml`, not as a
new top-level workflow, to keep PR signals consolidated.

---

## 6. Integration points identified

### Existing wiring

| Concern                       | Canonical location                                  |
|-------------------------------|-----------------------------------------------------|
| Typer app instance            | `puma.cli:app` (declared at `src/puma/cli.py:7`)    |
| Streamlit dashboard module    | `src/puma/dashboard/app.py` (155 lines)              |
| Dashboard view registry       | `VIEWS` dict at `src/puma/dashboard/app.py:29-37`   |
| SQLAlchemy session helper     | `puma.storage.db.session_scope()` (context manager) |
| Session factory               | `puma.storage.db.get_session_factory()`             |
| Run-spec Pydantic version     | Pydantic v2 (`model_validator`, `Field`)            |
| Project version (3 disagreeing sources) | pyproject `version="2.1.0-dev"`, `src/puma/__init__.py:__version__ = "2.0.0-dev"`, git tag `v2.7.0` — **canonical version for downstream tooling = the latest git tag** |
| `requests` dependency         | Already declared, `requests>=2.31` (both files)     |
| Existing add_typer precedent  | `app.add_typer(db_app, name="db")` at `src/puma/cli.py:309` |
| Canonical test invocation     | `make test` ≡ `docker compose run --rm puma_runner pytest tests/unit/ tests/integration/ -v` |

### New paths for PUMA Community v1

- **New package path:** `src/puma/community/` — placed at the same nesting level as
  `src/puma/dashboard/` and `src/puma/orchestrator/`. Matches `[tool.setuptools.packages.find]
  where = ["src"]`, so it is auto-discovered by setuptools without changes to `pyproject.toml`.
- **New tests path: `tests/community/` (flat, parallel to `tests/unit/` /
  `tests/integration/` / `tests/cli/` / `tests/smoke/`).**

  *Justification:* the existing test organisation is **by purpose, not by package** —
  `tests/cli/` holds CLI-command tests, `tests/integration/` holds tests that touch
  alembic/ollama/codecarbon, `tests/smoke/` holds end-to-end dashboard smoke. **None of the
  existing test trees has package-shaped subfolders** (`tests/unit/` is flat: 29 test files
  in one directory). A community feature spans CLI + storage + HTTP I/O + dashboard, which
  does not map cleanly onto any single existing folder. Creating `tests/community/`
  preserves the "purpose-shaped" convention and keeps federation tests collocated for the
  reviewer of the memoria. (Alternative `tests/unit/community/` would be the first nested
  subfolder ever in `tests/unit/` and would split federation tests across multiple
  directories.) The Makefile `test` target currently runs only `tests/unit/` and
  `tests/integration/`, so a `tests/community/` folder will need to be added to the test
  invocation in a later prompt (note for Prompt 12 — *not in scope of Prompt 0*).

### Integration line in `src/puma/cli.py`

Insert the new sub-typer registrations **between current lines 1007 (blank line at end of
`generate_plots_cmd`) and 1009 (`if __name__ == "__main__":`)**. Target form:

```python
# end of generate_plots_cmd at line 1006-1007 (existing)

from puma.community.auth_cli import auth_app          # new
from puma.community.share_results_cli import share_results_app  # new
app.add_typer(auth_app, name="auth")
app.add_typer(share_results_app, name="share-results")

if __name__ == "__main__":   # existing line 1009
    app()
```

This is consistent with the existing precedent at line 304-309 (`db_app` sub-typer
registration). Imports are lazy at function level today; both styles are present, and a
top-of-file import here would be acceptable — the choice can be deferred to Prompt 1.

### Integration line in `src/puma/dashboard/app.py`

The `VIEWS` dict lives at **lines 29-37**. Insert a new entry **immediately before the
closing `}` on line 37**:

```python
VIEWS = {
    "📊 Overview":              overview.render,
    "🆚 Model Comparison":      model_comparison.render,
    "🎯 Reliability":           reliability.render,
    "🛡️ Robustness":            robustness.render,
    "⚖️ Fairness":              fairness.render,
    "🌱 Sustainability Frontier": sustainability.render,
    "🔍 Instance Drill-down":   instance_drilldown.render,
    "🤝 Community":             community.render,   # ← new entry, prefix the import at line 16-24
}
```

The corresponding import of `community` joins the existing `from puma.dashboard.views
import (…)` block at lines 16-24.

### Integration line in `requirements.txt`

Add **after line 21** (last existing line is `seaborn>=0.13`):

```
# Community federation v1 (opt-in publication of results)
jsonschema>=4.21      # validate community payloads against the JSON Schema
PyGithub>=2.3         # create PRs against pumacp/puma-community
tomli-w>=1.0          # write per-user community config (toml)
```

The same three pins should also be added to `pyproject.toml` `dependencies = [ … ]`
between lines 29 (`"requests>=2.31",`) and 30 (`]`). **Both files** must be kept in sync
(this is an existing pre-condition of the repo — they already diverge on matplotlib/seaborn
and the federation prompt MUST NOT introduce a third divergence).

### Other files needing 1-2 line additions in later prompts (NOT edited here)

| File | Probable addition |
|------|-------------------|
| `pyproject.toml`            | three new runtime deps mirroring `requirements.txt` (lines 11-30). |
| `Makefile`                  | extend the `test` target (line 20-21) to include `tests/community/`. |
| `.github/workflows/lint-and-test.yml` | extend Job 1 with `pytest tests/community/ -q`. |
| `.gitignore`                | explicit ignores for `data/cache/`, `data/puma.db`, and any new federation cache (e.g. `data/community/`). |
| `docs/community/` (this folder) | future federation docs — guide, ADR-005 link, payload schema, etc. |
| `CHANGELOG.md`              | `Unreleased` section will accrue federation entries. |
| `docs/RELEASES/v2.8.0.md` (future) | release notes for the federation feature. |

---

## 7. Surprises and risks for subsequent prompts

1. **Baseline is v2.7.0, not v2.3.0.** The implementation plan assumes v2.3.0 as baseline,
   but the repo is four releases ahead. Features that have landed between v2.3.0 and v2.7.0
   and the federation MUST respect (each is enforced by tests or by the closure document):
   - **v2.4.0** — Sprint 7 CLI completeness: six Anexo-F-shaped commands already exist
     (`list-runs`, `list-ollama-models`, `prepare-datasets`, `wilcoxon`, `bias-analysis`,
     `generate-plots`). The federation's new commands must not name-collide with these.
   - **v2.5.0** — Sprint 8 hardening: the new `--expected-mae` path of
     `validate-baseline` and the cross-scenario KV-cache state-contamination invariant
     (documented in `docs/baseline_references.md`); `validate-baseline` no-args
     default of F1=0.5867 must stay backward-compatible. The federation must not call
     `validate-baseline` implicitly anywhere on the publish path.
   - **v2.6.0** — Sprint 9 Apple Silicon detection: nine `apple-silicon-*` profiles in
     `config/profiles.yaml`; `SystemCapabilities` gained `chip_brand` /
     `unified_memory_gb`; `CodeCarbon` has a platform-aware tracking mode. A federation
     payload must therefore carry **chip identity** (Apple Silicon vs Linux+NVIDIA vs
     CPU-only) alongside model+seed+temperature.
   - **v2.7.0** — Sprint 10 catalog expansion: two `qwen3:30b*` entries are catalogued as
     **pending validation** with explicit defensive tests
     (`test_qwen3_entries_excluded_from_gpu_entry`,
     `test_qwen3_entries_excluded_from_all_apple_silicon`,
     `test_qwen3_entries_target_gpu_high_only`). The federation MUST NOT label
     pending-validation results as canonical, and Kimi K2.6 is **formally excluded** from
     the catalog (13 registry probes, all 404) — federation tooling must refuse to publish
     results for non-catalogued models without explicit flag and warning.

2. **Src layout (`src/puma/`) — not root.** The package code is under `src/puma/`, not
   `puma/` at the repo root. Imports inside the federation code must use
   `from puma.community.<module> import …`; the PYTHONPATH inside the runner container is
   already `/app/src`. The `puma.cli:app` import path (per `[project.scripts]`) is
   independent of the src layout — it works because setuptools installs the package as
   `puma`.

3. **The CLI is a single file `src/puma/cli.py`** (1010 lines), **not** a package
   `src/puma/cli/`. There is no `cli/__init__.py` to import additional command modules
   from. Therefore `app.add_typer(auth_app, name="auth")` and
   `app.add_typer(share_results_app, name="share-results")` must be added **directly in
   that single file**, between current lines 1007 and 1009. The pattern is already
   established at line 309 with `db_app`. Splitting the CLI into a package is out of
   scope.

4. **Test organisation is purpose-shaped, not package-shaped, and `tests/unit/` is flat.**
   Existing `tests/unit/` contains 29 `test_*.py` files in one directory with **zero
   subfolders** other than `__pycache__`. The federation introduces concerns spanning CLI,
   storage, HTTP, and dashboard. The convention that best matches existing organisation is
   a new top-level `tests/community/` (parallel to `tests/unit`, `tests/integration`,
   `tests/cli`, `tests/smoke`). **Caveat:** the Makefile `test` target only runs `tests/unit/`
   and `tests/integration/`. A later prompt must extend that target — until then,
   federation tests run only on the GitHub CI workflow (which itself currently runs only
   `tests/unit/` + `tests/integration/`).

5. **Constitution + architecture set hard constraints the federation must NOT contradict:**
   - **HITL**: "no final action without human validation" → every publish must require an
     explicit user-typed confirmation; no silent or scheduled publication.
   - **Reproducibility**: "docker-compose down && up must produce identical results" →
     the federation must NOT introduce any non-determinism on the inference path, must
     not write to `data/puma.db` from the publish flow, and must not touch
     `config/runtime_profile.yaml`.
   - **SDD single source of truth**: `specs/*.md` files are normative. ADR-005 must NOT
     live inside `specs/` (it would then bind the benchmark pipeline).
   - **CodeCarbon mandatory**: federation tooling must not gate the codecarbon hook on
     publish state.
   - **JSON Schema for all outputs**: federation payloads must be JSON-schema-validated
     (motivates the `jsonschema>=4.21` dependency).

6. **No ADR location exists today → ADR-005 should live in `docs/decisions/`** (new
   directory), not in `specs/decisions/`. Rationale: anything inside `specs/` binds the
   benchmark per the constitution; the federation is opt-in non-normative project
   tooling. `docs/decisions/` keeps `specs/` semantically pure and gives future
   project-level ADRs a stable home.

7. **(Extra) Three disagreeing version strings.** `pyproject.toml` declares
   `version = "2.1.0-dev"`, `src/puma/__init__.py` declares `__version__ = "2.0.0-dev"`,
   the latest git tag is `v2.7.0`. There is **no `setuptools_scm` / `hatch-vcs`** wiring
   to reconcile them. The federation payload's `puma_version` field MUST derive from the
   git tag (or from the `ProfileSnapshot.puma_version` column which the runner already
   populates) and NOT from `pyproject.toml.version` or `puma.__version__`. This is a
   pre-existing inconsistency the federation should not try to fix in v1 — flag for a
   follow-up cleanup.

8. **(Extra) `requirements.txt` and `pyproject.toml` already disagree.** `requirements.txt`
   includes `matplotlib>=3.8` and `seaborn>=0.13`, which are **not** in
   `pyproject.toml.dependencies`. The federation must add `jsonschema`, `PyGithub`,
   `tomli-w` to **both** files (Prompt 1 to wire) and resist the temptation to
   "fix matplotlib/seaborn while we are at it" — that is scope creep.

9. **(Extra) `data/cache/` and `data/puma.db` are NOT explicitly gitignored.** They are
   simply untracked. Any federation cache layer that writes new files under `data/` risks
   accidental staging. The first prompt that introduces a federation cache must add
   explicit `.gitignore` lines.

---

## 8. Verification commands (re-runnable)

```bash
git tag -l v2.7.0-academic       # → v2.7.0-academic
git branch --show-current         # → feature/community-v1
git status --short                # → only `?? data/cache/`, `?? data/puma.db`, plus this file
ls docs/community/                # → 00-inventory.md
```

No existing file has been touched. The working tree is clean except for the two
pre-existing untracked items and the new `docs/community/00-inventory.md`.
