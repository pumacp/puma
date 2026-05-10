# Contributing to PUMA

## Pre-commit hooks

PUMA uses pre-commit to enforce formatting and lint. Hooks are not
installed automatically as git hooks because the typical workflow
involves cross-container development (host has source, container has
Python deps). Installing pre-commit as a git hook in this setup
causes commits from inside the container to fail.

### Recommended setup (host-only development)

Install pre-commit globally via pipx:

    pipx install pre-commit

From the repository root, install the git hooks:

    pre-commit install

Hooks will then run on every git commit from the host. Run manually
on demand:

    pre-commit run --all-files

### Cross-container workflow (development inside puma_runner)

If you commit from inside the container, do NOT run `pre-commit
install`. Instead, run pre-commit manually from the host before
pushing:

    pre-commit run --all-files

Or use the GitHub Actions CI workflow as your safety net (runs on
push to main and develop, blocks merges that violate the configured
rules).

## Branch and commit conventions

- Feature branches: `feature/<scope>` (e.g., `feature/sprint-1-debt-cleanup`)
- Commits: conventional commit style. See existing commit log for
  examples. Common types: `feat`, `fix`, `chore`, `docs`, `test`,
  `refactor`, `style`, `ci`.
- Atomic where possible. Multi-concern commits should clearly
  structure the body in sections.

## Tests

All tests must pass before opening a PR:

    pytest tests/unit/ tests/integration/ -v --no-cov

TDD is encouraged for changes to the modules listed under
`[[tool.mypy.overrides]]` strict (puma.metrics, puma.runtime,
puma.preflight). See `tests/integration/test_alembic_migrations.py`
for an example of TDD-first integration tests with explicit
acceptance criteria.

## Commit message hygiene

The repository's `core.hooksPath` is set to `.githooks/`. The
`commit-msg` hook automatically strips `Co-authored-by:`,
`Signed-off-by: Claude`, and `Generated-by:` trailers from commit
messages. Commits are attributed exclusively to the git identity
configured in `~/.gitconfig` (or the per-repository config).

New contributors who clone the repository should ensure
`core.hooksPath` is set:

    git config core.hooksPath .githooks

Without this, the hook does not run and commit messages may
accumulate unwanted trailers.
