# Contributing to PUMA

Thank you for contributing. This document covers code conventions, the development workflow, commit format, and the PR process.

---

## Development setup

All development happens inside Docker — the only host requirement is Docker + Docker Compose v2.

```bash
git clone <repo-url>
cd puma
docker compose build puma_runner   # build the dev container
```

No Python virtualenv, no conda environment, no local pip installs.

---

## Running the dev workflow

### Tests

```bash
make test                  # unit + integration tests inside Docker
make smoke                 # smoke / AppTest tests (no Ollama needed)
```

Or run specific test files:

```bash
docker compose run --rm --no-deps puma_runner pytest tests/unit/test_metrics_accuracy.py -v
docker compose run --rm --no-deps puma_runner pytest tests/unit/ -k "calibration" -v
```

### Lint

```bash
make lint
# equivalent to:
docker compose run --rm --no-deps puma_runner ruff check src/puma/ tests/
docker compose run --rm --no-deps puma_runner ruff format --check src/puma/ tests/
```

Auto-fix most lint errors:

```bash
docker compose run --rm --no-deps puma_runner ruff check src/puma/ tests/ --fix
docker compose run --rm --no-deps puma_runner ruff format src/puma/ tests/
```

### Build the image

```bash
make build
# equivalent to:
docker compose build puma_runner
```

---

## Code conventions

### Language and typing

- Python **3.11+** syntax throughout.
- Use `X | Y` union types (not `Optional[X]` or `Union[X, Y]`).
- Use `datetime.UTC` (not `timezone.utc`).
- All public functions and class attributes must have **type annotations**.
- Use `from __future__ import annotations` at the top of every module.

### Formatting

- Line length: **100 characters** (enforced by `ruff`).
- Import order: stdlib → third-party → local (enforced by `ruff I001`).
- No trailing whitespace; Unix line endings.

### Comments

- Write **no comments** by default.
- Only add a comment when the *why* is non-obvious: a hidden constraint, a subtle invariant, a workaround for a specific external bug.
- Never describe *what* the code does — well-named identifiers do that.
- One short line maximum. No multi-line comment blocks.

### Dependencies

- **Pydantic v2** for all data models.
- **SQLAlchemy 2.0** for database access (use `session_scope()` context manager).
- **Jinja2** for prompt templates.
- **structlog** for structured logging (JSON renderer).
- **Rich** for CLI progress bars.
- No inline `print()` statements — use `structlog` or `typer.echo`.

### Error handling

- Do not add error handling for scenarios that cannot happen.
- Validate at system boundaries (user input via RunSpec, external responses via `parse_response()`).
- Trust internal framework guarantees (`session_scope()` rollbacks, Pydantic validators).

---

## Commit message format (Conventional Commits)

```
<type>(<scope>): <short imperative description>

[optional body — wrap at 72 chars]
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New feature or behaviour |
| `fix` | Bug fix |
| `refactor` | Code change with no behaviour change |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `ci` | CI/CD workflow changes |
| `chore` | Maintenance (deps bump, gitignore, etc.) |

### Scopes (optional but recommended)

`scenarios`, `metrics`, `runner`, `preflight`, `runtime`, `dashboard`, `cli`, `storage`, `reporting`, `adaptation`, `perturbations`

### Examples

```
feat(scenarios): add risk_detection_jira scenario
fix(runner): prevent UNIQUE constraint on instance re-insert with perturbations
test(metrics): add ECE calibration edge cases for empty bins
docs(user_guide): add sustainability tracking section
ci: add release workflow for v* tags
```

---

## Pull request process

1. **One logical change per PR.** Split unrelated changes into separate PRs.
2. **All checks must pass** before requesting review:
   ```bash
   make lint && make test && make smoke
   ```
3. **Documentation:** update `docs/` if you:
   - Add a public module or class
   - Change user-visible behaviour (CLI flags, metric names, run-spec fields)
   - Add a new scenario (see `docs/adding_scenarios.md`)
   - Add a new model entry (see `docs/adding_models.md`)
4. **Changelog:** add an entry to `CHANGELOG.md` under an `[Unreleased]` section.
5. **Tests:** new scenarios require parse tests; new metrics require formula tests; new CLI commands require at least one integration or smoke test.

---

## Phase gate process

Each development phase ends with a gate that must pass before work on the next phase begins:

1. All unit tests pass: `make test`
2. Ruff reports no errors: `make lint`
3. Smoke dry-run completes: `puma run specs/runs/smoke_triage.yaml --dry-run`
4. The specific gate conditions listed in `CLAUDE_CODE_INSTRUCTIONS.md` are met.

---

## Project structure

```
src/puma/               ← Main package (imported via PYTHONPATH=/app/src)
  adaptation/           ← Prompting strategies and example selection
  dashboard/            ← Streamlit app and components
  datasets/             ← Dataset loaders and verification
  metrics/              ← All metric computation functions
  orchestrator/         ← RunSpec, Runner, compare_runs
  perturbations/        ← Text perturbation functions
  preflight/            ← Hardware detection and profile selection
  reporting/            ← Markdown / PDF report generation
  runtime/              ← OllamaClient and InferenceCache
  scenarios/            ← Benchmark task definitions
  storage/              ← SQLAlchemy ORM (6 tables)
  sustainability/       ← CodeCarbon wrapper
  cli.py                ← Unified CLI (Typer)

tests/
  unit/                 ← Fast tests, no external dependencies
  integration/          ← Require dataset files in data/
  smoke/                ← AppTest + dry-run end-to-end tests

specs/
  prompts/              ← Jinja2 templates per scenario × strategy
  runs/                 ← Example and gate run-specs
  scenarios/            ← Scenario YAML specifications

docs/                   ← Extended documentation (this directory)
config/                 ← models_catalog.yaml, runtime_profile.yaml
data/                   ← Datasets + SQLite DB (gitignored)
results/                ← Run artifacts per run_id (gitignored)
```

---

## What not to do

- **Do not install** anything on the host machine (Python packages, system tools). All tooling runs inside Docker.
- **Do not commit** files from `data/`, `results/`, `logs/`, or `.env` — they are gitignored.
- **Do not use** external APIs during inference (OpenAI, Anthropic, etc.). All inference goes through Ollama.
- **Do not send** CodeCarbon telemetry — always use `tracking_mode="process"`.
- **Do not skip** git hooks with `--no-verify` unless the hook has a confirmed false positive.
- **Do not amend** published commits — create a new commit instead.
