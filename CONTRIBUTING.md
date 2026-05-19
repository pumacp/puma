# Contributing to PUMA

Thank you for considering a contribution. There are two ways to contribute
to the PUMA ecosystem:

1. **Code** — bug fixes, new features, documentation, tests. Read this
   document first.
2. **Benchmark results** — share runs of PUMA with the community via the
   companion repository
   [`pumacp/puma-community`](https://github.com/pumacp/puma-community).
   The PUMA tool's built-in `puma share-results` command opens the Pull
   Request for you.

All interactions on this repository are governed by the
[`Code of Conduct`](CODE_OF_CONDUCT.md).

---

## Development setup

### Docker (recommended)

The full toolchain runs inside Docker for reproducibility:

```bash
git clone https://github.com/pumacp/puma.git
cd puma
docker compose up -d
docker compose run --rm puma_runner pytest tests/ -v
```

### Manual install (advanced)

```bash
git clone https://github.com/pumacp/puma.git
cd puma
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

The manual path requires Python ≥ 3.11 and a local Ollama install for any
test that exercises a real model
(<https://ollama.com/download>). Tests that need Ollama are gated
on the `ollama` pytest marker and skipped otherwise.

---

## Testing

The full suite runs inside Docker for reproducibility:

```bash
docker compose run --rm puma_runner pytest tests/ -v
```

Targeted runs:

```bash
docker compose run --rm puma_runner pytest tests/community/ -v
docker compose run --rm puma_runner pytest tests/unit/ -v
docker compose run --rm puma_runner pytest tests/integration/ -v
```

Coverage report:

```bash
docker compose run --rm puma_runner pytest tests/ --cov=src/puma --cov-report=term
```

---

## Code style

Three tools must all pass before opening a PR:

- **Formatter:** `ruff format`
- **Linter:** `ruff check`
- **Type checker:** `mypy src/puma/`

Run them locally:

```bash
docker compose run --rm puma_runner ruff format --check src tests
docker compose run --rm puma_runner ruff check src tests
docker compose run --rm puma_runner mypy src/puma/
```

The CI workflow (`lint-and-test.yml`) runs the same checks on every PR.

---

## Commit conventions

This repository follows [Conventional Commits](https://www.conventionalcommits.org/).
Commit types in use: `feat`, `fix`, `docs`, `chore`, `test`, `refactor`,
`style`, `ci`. Scope is optional but recommended (e.g.,
`feat(community): add credential store`).

Example:

```
feat(dashboard): add Community view to academic dashboard

Composes the schema, builder, and validator into a 4-state Streamlit
wizard. Adds 9 new tests under tests/community/.
```

---

## Pull request process

1. Open an issue describing the change before sending a large PR.
2. Branch from `develop` (the integration branch).
3. Write tests for new code; target ≥ 80 % coverage for new modules.
4. Run `ruff`, `mypy`, and `pytest` locally before pushing.
5. Open the PR against `develop`. CI must be green before review.
6. PRs are squash-merged into `develop`; `develop` is fast-forwarded to
   `main` on release.

---

## Reporting bugs

Open a GitHub issue with the `bug` label. Include:

- PUMA version (output of `puma --version`).
- Python version (`python3 --version`).
- Operating system and architecture (`uname -srm` on POSIX).
- Docker version (if running via Docker).
- The exact command that triggered the bug.
- The expected behaviour and the observed behaviour.

For runtime-only issues (e.g., Ollama model not loading), include the
output of `puma preflight` and `ollama list`.

---

## Feature requests

Open an issue with the `enhancement` label. Describe the use case, the
proposed CLI or API surface, and any backward-compatibility implications.
Major features warrant a design discussion (an architecture decision
record under `docs/decisions/`) before implementation.

---

## Code of Conduct

By participating you agree to the
[Contributor Covenant v2.1](CODE_OF_CONDUCT.md). Concerns can be reported
privately to `puma-community-conduct@pumacp.org`.
