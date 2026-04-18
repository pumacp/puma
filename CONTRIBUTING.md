# Contributing to PUMA

## Setup

All development happens inside Docker. You only need Docker + docker compose on the host.

```bash
git clone <repo>
cd puma
docker compose build puma_runner
```

## Running tests

```bash
make test        # unit + integration tests
make smoke       # smoke tests (requires Ollama)
make lint        # ruff check + format check
```

Or directly:

```bash
docker compose run --rm --no-deps puma_runner pytest tests/unit/ -q
docker compose run --rm --no-deps puma_runner ruff check src/puma/ tests/
```

## Code conventions

- **Python 3.11+** — use `X | Y` unions, `match` statements where appropriate.
- **Type annotations** on all public functions and class attributes.
- **Pydantic v2** for data models; **SQLAlchemy 2.0** for ORM.
- **No comments** unless the *why* is non-obvious (hidden constraint, workaround).
- Line length: 100 characters (`ruff` enforced).
- Import order: `ruff` I001 enforced (stdlib → third-party → local).

## Commit messages (Conventional Commits)

```
<type>(<scope>): <short description>

[optional body]
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`.

Examples:
```
feat(scenarios): add prioritization_jira scenario
fix(runner): prevent UNIQUE constraint on instance re-insert
test(metrics): add ECE calibration edge cases
docs: update troubleshooting for Ollama port conflict
```

## Pull requests

1. One logical change per PR.
2. All tests must pass: `make test lint`.
3. Update `docs/` if you add a public module or change behaviour.
4. New scenarios require: scenario class + prompt templates + unit tests + a smoke run-spec.
5. New metrics require: implementation in `puma.metrics.*` + unit tests + entry in `docs/metrics_reference.md`.

## Phase gate process

Each phase ends with a gate (see `CLAUDE_CODE_INSTRUCTIONS.md`). Gates must pass before moving on:
- All unit tests green.
- `ruff check src/puma/ tests/` passes.
- Smoke test (dry-run) completes without errors.

## File structure

```
src/puma/          ← main package (PYTHONPATH=/app/src)
tests/unit/        ← fast, no external deps
tests/integration/ ← require data files
tests/smoke/       ← require Docker + Ollama
specs/             ← run-specs, prompt templates, scenario specs
docs/              ← extended documentation
config/            ← model catalog, runtime profile
```
