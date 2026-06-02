# Development workflow

This guide is the canonical procedural reference for contributing to
PUMA through the standard IDE-based git workflow: branch from
`develop`, edit in your editor, run the local quality gates, push, open
a Pull Request, wait for CI, and merge.

It is written for an external contributor who has cloned the repository
for the first time, but it is also the maintainer's own reference for
day-to-day routine work.

If you are looking for a 60-second summary instead, read
[`CONTRIBUTING.md`](https://github.com/pumacp/puma/blob/develop/CONTRIBUTING.md)
at the repository root — this page is the long form.

---

## 1. Overview

PUMA is developed as a small set of atomic Pull Requests against the
`develop` branch. Each PR addresses **one purpose** (a single feature,
a single bug fix, a documentation pass, a single refactor) and must
pass three CI workflows before it can be merged:

- **Lint and Test** — `ruff check`, `ruff format --check`, `mypy
  src/puma/`, `pytest -m "not ollama"`.
- **Smoke Test** — a minimal end-to-end check that the package
  installs and the CLI starts.
- **Docs** — `mkdocs build --strict` over the published nav.

A fourth workflow, **Integration tests with Ollama**, runs only on
pushes to `main` (it needs a live Ollama daemon).

`develop` is the integration branch. `main` is fast-forwarded from
`develop` at release time. Tags follow Semantic Versioning. Direct
commits to `develop` or `main` are not permitted — every change lands
through a PR.

This page covers the procedure end-to-end. If you are looking for
*what* to change (architecture, scenarios, metrics, the CLI surface),
the rest of the documentation is the reference; this page is only
about *how* to land a change.

---

## 2. Prerequisites

| Tool | Required? | Why |
|---|---|---|
| [git](https://git-scm.com/) ≥ 2.30 | yes | Source control. |
| [GitHub CLI (`gh`)](https://cli.github.com/) ≥ 2.40 | strongly recommended | Opening PRs and inspecting CI status from the terminal. |
| Python ≥ 3.11 | yes | Building and testing the package. |
| [Docker](https://docs.docker.com/get-docker/) + Docker Compose | recommended | The supported runtime for end-to-end testing (`puma_runner`, `puma_ollama`, `puma_dashboard`). |
| An IDE | yes | VSCode, Cursor, JetBrains PyCharm — see §7. |
| [Ollama](https://ollama.com/download) | optional | Only needed if you run the `ollama`-marked tests or do manual benchmark validation locally. |

You should also have a GitHub account, with the right permissions on
`pumacp/puma` if you are submitting from a fork, or push access if you
are a maintainer.

---

## 3. Repository layout

A short tour of the top-level directories. Anything marked **locked**
should not be modified in a documentation, feature, or refactor PR
without an explicit change-management discussion.

| Path | Purpose | Locked? |
|---|---|---|
| `src/puma/` | The PUMA Python package (CLI, runtime, metrics, dashboard, ...). | partially — see sub-paths below |
| `src/puma/community/integrity.py` | Hash-and-verify code for community submissions. | **locked** — schema-bearing |
| `src/puma/orchestrator/runner.py` | The benchmark run executor. | **locked** — touching it can shift baselines |
| `src/puma/runtime/retry.py` | Deterministic retry policy. | **locked** — affects metric reproducibility |
| `src/puma/models/` | ORM models (SQLAlchemy). | **locked** — schema |
| `src/puma/preflight/` | Hardware detection + profile selection. | **locked** — affects which runs are eligible |
| `tests/` | Pytest suite (`unit/`, `integration/`, `community/`). | not locked |
| `docs/` | mkdocs Material source for the published site. | mostly not locked |
| `docs/sprints/` | Internal sprint records. | **locked** — chronological log |
| `docs/known_debt.md` | Debt tracker. | **locked** except surgical `D-NN` status updates as part of resolving the debt entry itself |
| `schema/` | JSON Schema for community submissions and run-specs. | **locked** — semantic versioning |
| `specs/runs/` | Canonical benchmark run-specs. | **locked** — reference inputs |
| `config/profiles.yaml` | Hardware-profile definitions. | **locked** — affects which models a machine is allowed to run |
| `config/models_catalog.yaml` | The curated model catalog. | **locked** — affects `puma models recommended` |
| `mkdocs.yml` | Docs site config. | not locked |
| `pyproject.toml` | Package metadata and dependency pins. | not locked, but coordinate dependency changes through a PR |
| `.github/workflows/` | CI definitions. | not locked, but a workflow change is its own atomic PR |
| `.githooks/` | Local git hooks (notably `commit-msg`). | not locked |
| `CONTRIBUTING.md` | Repo-root canonical entry point. | not locked |
| `CODE_OF_CONDUCT.md` | Contributor Covenant v2.1 adoption. | not locked |
| `CHANGELOG.md` | Keep a Changelog format. | not locked |

If you need to touch a locked path, the right move is to open an
issue first describing the motivation, the proposed change, and the
expected impact on baselines / schema / reproducibility. The maintainer
will decide whether to lift the lock and under what conditions.

---

## 4. Setting up Git identity

Before your first commit, configure a Git identity that matches your
GitHub account. This is what every future commit will be attributed
to, and the repository's commit-msg hook (see §10) keeps that
identity as the **only** author on every commit.

```bash
git config --global user.name  "Your Real Name"
git config --global user.email "your-email@example.com"
```

If you contribute to multiple GitHub identities, set the identity
**per-repository** instead of globally:

```bash
cd ~/Projects/tfg/puma
git config user.name  "Your Real Name"
git config user.email "your-email@example.com"
```

Verify:

```bash
git config user.name
git config user.email
```

A mismatched email is the most common reason a commit appears as
"unverified" on GitHub or fails to be associated with your profile.

---

## 5. Cloning the repository

If you are a maintainer with push access:

```bash
git clone git@github.com:pumacp/puma.git
cd puma
```

If you are contributing from a fork:

```bash
# 1. Fork pumacp/puma on GitHub.
# 2. Clone your fork.
git clone git@github.com:<your-handle>/puma.git
cd puma
# 3. Add the upstream remote.
git remote add upstream git@github.com:pumacp/puma.git
git fetch upstream
```

Initial sanity check:

```bash
git status              # should show: nothing to commit, working tree clean
git branch --show-current  # should be: develop
git log -1 --oneline    # most recent commit on develop
```

---

## 6. Installing development dependencies

The recommended runtime is Docker — it isolates Python, Ollama, the
dashboard, and the SQLite database in their own containers and matches
what CI runs.

### Docker (recommended)

```bash
docker compose up -d
docker compose run --rm puma_runner pytest tests/ -v
```

### Manual install (advanced)

If you prefer a host-side install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

The manual path requires Python ≥ 3.11. Tests that need a real Ollama
daemon are gated on the `ollama` pytest marker and are skipped by
default; you can opt in with `pytest -m ollama` once Ollama is running
locally.

### Set the commit-msg hook path

Once per fresh clone, point Git at the repository's hooks directory:

```bash
git config core.hooksPath .githooks
```

This activates the `commit-msg` hook documented in §10.

### Verify the CLI is wired up

After install, confirm the canonical command surface is reachable:

```bash
puma --help                 # top-level entry point
puma doctor                 # environment health check (Python, Ollama,
                            # CodeCarbon, models, hardware profile, DB)
puma models list            # tags Ollama already has locally
puma models show qwen2.5:3b # per-model details from /api/show
puma models recommended     # curated catalog with availability
puma run --help             # benchmark execution
```

If `puma --help` does not work, re-run the install step and check
`which puma`. The full command reference lives in
[`docs/cli_reference.md`](cli_reference.md).

---

## 7. IDE setup recommendations

PUMA is editor-agnostic. The recommendations below cover the three
editors maintainers and external contributors have used so far. None
of them is required.

### 7.1 VSCode

Recommended extensions:

| Extension | Why |
|---|---|
| Python (ms-python.python) | Interpreter selection, Pylance type checking. |
| Ruff (charliermarsh.ruff) | In-editor lint + format with the project's pyproject configuration. |
| GitLens (eamodio.gitlens) | Inline blame and a richer file-history view. |
| GitHub Pull Requests (github.vscode-pull-request-github) | Review and merge PRs from the editor. |

A minimal `.vscode/settings.json` that matches the project style:

```jsonc
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": "explicit",
    "source.organizeImports.ruff": "explicit"
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "python.analysis.typeCheckingMode": "strict"
}
```

Do not commit a personal `.vscode/settings.json` to the repository;
keep it local.

### 7.2 Cursor

Cursor is a VSCode fork, so the VSCode extension list and settings
above apply unchanged. The one Cursor-specific note: project-level
AI features are entirely opt-in and do not write commits on your
behalf. If you choose to use them, the `commit-msg` hook (§10) is the
safety net that keeps the project's commit attribution policy intact.

### 7.3 JetBrains PyCharm

1. **Open** the project root directory.
2. **Python interpreter** — set to `.venv/bin/python` (manual install)
   or the Docker Compose-provided `puma_runner` interpreter.
3. **Inspections** — enable PEP 8 plus the bundled type-checker; the
   project formatting style matches the Ruff defaults configured in
   `pyproject.toml`.
4. **External tools** (optional) — add `ruff format`, `ruff check`,
   `mypy src/puma/`, and `pytest -m "not ollama"` as run
   configurations so the keyboard shortcuts match the local quality
   gates listed in §10.

PyCharm's bundled Git client is compatible with the `.githooks/`
hook path set in §6.

---

## 8. The standard contribution workflow

The full procedure for a single PR, from sync to merge. The commands
are linear and can be copy-pasted into your shell of choice (bash,
zsh, fish — all work).

### Step 1 — Sync `develop`

```bash
git checkout develop
git pull --ff-only
git fetch --prune
```

`--ff-only` refuses to silently create a merge commit if your local
`develop` has drifted; `--prune` cleans up references to branches
that have been deleted on the remote.

### Step 2 — Branch from `develop`

Branch names follow a `<type>/<scope>` convention. The type matches
one of the conventional-commits types (see §9); the scope is a short
kebab-case description.

| Example branch name | Type |
|---|---|
| `docs/improve-quickstart` | documentation pass |
| `feat/add-mistral-recommended-profile` | new feature |
| `fix/dashboard-render-on-empty-data` | bug fix |
| `test/coverage-runner-retry-paths` | test additions |
| `chore/bump-ruff-to-0-15` | dependency bump |
| `refactor/extract-prompt-loader` | internal refactor |
| `ci/cache-pip-on-docs-workflow` | CI pipeline change |

```bash
git checkout -b docs/improve-quickstart
```

### Step 3 — Edit in your IDE

Open the project in your editor of choice (§7) and make the changes.
Avoid touching any path marked **locked** in §3 unless you have agreed
the change in an issue first.

### Step 4 — Verify your changes

```bash
git status               # see what has changed
git diff                 # inspect the changes
git diff --stat          # summary view, useful for large edits
```

If you see unintended changes (e.g. auto-formatter rewrote unrelated
files), revert them with `git restore <file>` before staging.

### Step 5 — Stage selectively

Prefer explicit `git add <files>` over `git add .` — it forces you to
inspect every file that enters a commit.

```bash
git add docs/quickstart.md
git add tests/integration/test_quickstart_doc.py
```

If a file has both wanted and unwanted hunks, use:

```bash
git add -p <file>        # interactively pick hunks
```

### Step 6 — Commit (conventional commits format)

```bash
git commit -m "docs(quickstart): clarify Ollama install step for Apple Silicon

The previous wording assumed amd64 binaries. Adds an explicit pointer
to ollama.com/download for arm64 builds and notes the brew tap."
```

The first line is the **subject**: `type(scope): description`. Keep
it under 72 characters. The body, separated by a blank line, explains
the *why* — leave the *what* to the diff.

### Step 7 — Push the branch

```bash
git push -u origin docs/improve-quickstart
```

The `-u` (`--set-upstream`) flag links the local branch to its remote
counterpart so future `git push` and `git pull` calls don't need
arguments.

### Step 8 — Open a PR

```bash
gh pr create \
  --base develop \
  --title "docs(quickstart): clarify Ollama install step for Apple Silicon" \
  --body  "$(cat <<'BODY'
## Summary

The Quick start page assumed amd64 Ollama binaries. This PR adds an
explicit pointer to the arm64 build for Apple Silicon contributors.

## Changes

- docs/quickstart.md: new note in the Ollama install step.
- tests/integration/test_quickstart_doc.py: assert the page mentions
  both amd64 and arm64 install paths.

## Test plan

- mkdocs build --strict → exit 0
- pytest tests/integration/test_quickstart_doc.py → all pass
BODY
)"
```

A good PR body has three parts: a one-paragraph **summary**, a short
**changes** list (per-file or per-commit), and a **test plan** that
states what you ran locally.

### Step 9 — Wait for CI

GitHub will queue the three CI workflows almost immediately. Check
status from the terminal:

```bash
sleep 60
gh pr checks       # in the branch's working tree
gh pr view 123     # detailed view of a specific PR by number
```

Iterate on local fixes, push again with `git push`, and the CI
re-runs automatically.

### Step 10 — Merge on green

```bash
gh pr merge --rebase --delete-branch
```

`--rebase` keeps a linear history on `develop`; `--delete-branch`
cleans up the remote feature branch and the local one.

### Step 11 — Sync local `develop`

```bash
git checkout develop
git pull --ff-only
git fetch --prune
```

You are now ready for the next contribution from a clean base.

---

## 9. Conventional commit message format

PUMA follows [Conventional Commits](https://www.conventionalcommits.org/).
The format is:

```
type(scope): description

[optional body]

[optional footer(s)]
```

### Types in use

| Type | When |
|---|---|
| `feat` | A new user-facing capability (CLI command, dashboard view, scenario, metric). |
| `fix` | A bug fix in existing behavior. |
| `docs` | Documentation-only changes (mkdocs site, README, CHANGELOG, in-source docstrings if pure rewording). |
| `test` | Adding or refactoring tests; no behavior change. |
| `chore` | Maintenance: dependency bumps, CI config, formatting passes, lockfile updates. |
| `refactor` | Code change that neither adds a feature nor fixes a bug. |
| `ci` | Changes to GitHub Actions workflows or pre-commit configuration. |
| `build` | Build-system or external dependency changes (`pyproject.toml`, `Dockerfile`). |
| `style` | Whitespace, formatting, missing semicolons — no functional change. |

### Scope

A short kebab-case identifier for the area of the change. Common
scopes:

- `cli` — Typer command surface.
- `runner` / `runtime` — orchestrator and retry path.
- `metrics` — metric implementations.
- `dashboard` — Streamlit views.
- `community` — community submissions.
- `docs` (as a sub-scope of `feat` / `fix`) — when a non-`docs`-typed
  change also touches docs.
- `mkdocs` — the docs site config.
- `ci` — workflow files.

### Examples

```
feat(dashboard): add Multi-model view with side-by-side metrics

Composes the per-model results loader, the delta-aware metric panel,
the four bar charts (F1-macro, MAE, p95 latency, carbon), and a
reproducibility fingerprint check. Reads persisted SQLite rows only —
no live inference.

Closes #123.
```

```
fix(runner): handle empty per-class metric dicts on zero-prediction runs

The post-run reporter assumed metrics["per_class"] always contained at
least one label. On a dry-run with 0 successful predictions the dict
is empty; the reporter now skips the per-class section instead of
raising KeyError.
```

```
docs: skip acrostic immutability tests + restructure README header
```

```
chore(docker): pin python:3.12-slim to a specific digest
```

### When to add a body

Add a body when the *why* is not obvious from the diff. Pure mechanical
changes (renaming a variable, applying `ruff format`) can stand on
their subject line alone.

### Referencing issues

GitHub auto-links `#123` in the commit body. Use `Closes #123` to
auto-close the issue when the PR merges; use `Refs #123` for a
non-closing reference.

---

## 10. Running local quality gates before pushing

The same three CI workflows that run on every PR can be reproduced
locally. Running them before pushing saves a CI cycle and surfaces
problems faster.

### 10.1 Lint and format

```bash
ruff check src/ tests/                # static checks; 0 violations expected
ruff format --check src/ tests/       # formatting check; 0 reformats expected
```

To auto-fix:

```bash
ruff check --fix src/ tests/
ruff format src/ tests/
```

### 10.2 Type checking

```bash
mypy --strict src/puma/
```

`--strict` is what CI runs. The project keeps the source tree at 0
strict-mode errors.

### 10.3 Tests

```bash
pytest -m "not ollama"   # default suite, no live Ollama dependency
pytest -m ollama         # opt-in: requires a local Ollama daemon
pytest tests/integration/test_foo.py -v   # a single file, verbose
pytest -k "test_name_substring"           # filter by test name
```

Common pytest flags:

| Flag | Use |
|---|---|
| `-v` / `-vv` | More verbose output. |
| `-x` | Stop on first failure. |
| `--no-cov` | Skip coverage collection for faster iteration. |
| `--lf` | Re-run only the tests that failed in the last run. |
| `-p no:cacheprovider` | Disable pytest's cache (CI runs with it disabled in some workflows). |

### 10.4 Docs build (if you touched `docs/`)

```bash
mkdocs build --strict
```

`--strict` aborts the build on broken links and unused docs. If you
added a new page, also add it to `mkdocs.yml`'s `nav:` section.

### 10.5 Pre-commit (optional)

The project ships with no `.pre-commit-config.yaml` at the time of
writing. If you prefer to run formatters and linters automatically
on `git commit`, install `pre-commit` (`pipx install pre-commit`)
and add your own configuration locally — do not commit it without
discussion, as pre-commit hooks interact with the cross-container
workflow described in §6.

### 10.6 The commit-msg hook

`.githooks/commit-msg` strips three classes of footer lines from
every commit message you author:

- `Co-authored-by:` lines.
- `Signed-off-by: …<AI tool>` lines.
- `Generated-by:` lines.

This is a tool-agnostic policy: regardless of which assistant (if
any) helped draft a change, commits are attributed exclusively to
the git identity you configured in §4. The repository tracks no
co-author trailers and surfaces no AI-tool branding in its history.

The hook is activated by the one-time `git config core.hooksPath
.githooks` step in §6.

---

## 11. Handling conflicts

### 11.1 `git pull --ff-only` fails after a sync

Someone pushed to `develop` while you were working. Rebase your
feature branch on top of the updated `develop`:

```bash
git fetch origin
git checkout <your-feature-branch>
git rebase origin/develop
# Resolve conflicts in the editor; for each conflicted file:
git add <file>
git rebase --continue
# When the rebase completes, push with --force-with-lease.
git push --force-with-lease
```

`--force-with-lease` refuses to push if the remote has changed since
your last fetch — safer than plain `--force`.

### 11.2 `gh pr merge` fails due to conflicts with `develop`

Same procedure as 11.1: rebase your branch on `origin/develop`,
resolve, and force-push. CI re-runs automatically; once green, retry
the merge.

### 11.3 You committed to the wrong branch

If you committed to `develop` by mistake but haven't pushed:

```bash
git branch <new-branch-name>            # save your commits on a new branch
git reset --hard origin/develop         # rewind develop
git checkout <new-branch-name>          # continue from the saved commits
```

If you have already pushed to `develop`: stop and contact the
maintainer. **Never rebase or force-push `develop` or `main` directly.**

### 11.4 You need to drop a commit before pushing

```bash
git rebase -i HEAD~3
# Mark the unwanted commit's line as 'drop' (or delete the line).
# Save and exit. The history is rewritten.
```

If the unwanted commit has already been pushed, the safer move is to
add a `revert` commit instead of rewriting history.

---

## 12. Cosmetic and visual edits

Two areas of the project are explicitly relaxed for cosmetic
contributions:

- **The acrostic block** in `README.md` and `docs/index.md` — the
  block spells out FOLLOW THE WHITE PUMA in a structured paragraph
  set. PR #47 relaxed the byte-immutability assertion that previously
  guarded its content; the three pytest tests that enforced it are
  marked `@pytest.mark.skip` and **must stay skipped**:
    - `tests/integration/test_pages_content_audit.py::test_landing_page_has_acrostic_block`
    - `tests/integration/test_readme_acrostic_and_resources.py::test_acrostic_block_present_and_verbatim`
    - `tests/integration/test_readme_acrostic_and_resources.py::test_acrostic_spells_follow_the_white_puma`

  You can reposition, restyle, or change the visual layout of the
  acrostic freely (PR #47 turned it into a two-column HTML table).
  What you should not do is gratuitously rewrite the prose, or
  re-introduce a byte-identical assertion that would re-lock the
  block.

- **The categorized channel directory** in the README header (PUMA
  Platform / PUMA Info / PUMA Contact / PUMA Community / PUMA Code).
  Introduced in PR #47, mirrored onto `docs/index.md` in PR #48 (the
  S12.17 mkdocs content sync). Keep the two surfaces visually
  coherent if you edit either one.

If your visual change passes `mkdocs build --strict` and the existing
content-audit tests (`tests/integration/test_pages_content_audit.py`,
`tests/integration/test_pages_no_sensitive_content.py`), it is good
to land.

---

## 13. What NOT to do

- **Do not commit directly to `develop` or `main`.** All changes go
  through a PR.
- **Do not force-push `develop` or `main`.** Tags and downstream
  consumers depend on a stable history on both.
- **Do not modify locked files** without an issue-level discussion
  (see §3 for the list).
- **Do not introduce Spanish content** in public surfaces (`README.md`,
  `docs/` pages that appear in the mkdocs nav, in-CLI text). The
  audit set in `tests/integration/test_pages_content_audit.py`
  enforces this.
- **Do not reference** the following tokens in any new content:
  Anexo, TFG, memoria, Federación, federation hub, HELM, Stanford,
  AgentPM, MIT Student Method. The first three are leftovers from an
  academic framing that the project has consciously moved away from;
  the last five are unrelated benchmark / methodology brands that
  PUMA does not claim a relationship with.
- **Do not include AI-tool trailers** in commit messages. The
  `.githooks/commit-msg` hook strips them for you, but reviewers will
  also call them out — the project's history is intentionally clean
  of `Co-authored-by:` and `Generated-by:` lines from any assistant.
- **Do not include `Generated with <AI tool>` footers** in PR bodies
  for the same reason.
- **Do not bypass `mkdocs --strict`** by relaxing the gate locally.
  The site is meant to be link-checked on every build.

---

## 14. Submitting a benchmark result via PUMA Community

If your contribution is a *benchmark result* — a run of PUMA on a
model + scenario pairing that you want to add to the shared
leaderboard — the canonical path is **not** this repository. Instead,
use the companion repository
[`pumacp/puma-community`](https://github.com/pumacp/puma-community)
and the built-in `puma share-results` command:

```bash
puma auth login github      # one-time, stores the token at 0600
puma share-results --run-id <your-run-id>
```

`puma share-results --dry-run` packages the artifact locally without
opening a PR — useful for inspecting the submission shape before
pushing.

The submission flow, the schema, and the verification path are
documented separately at the `puma-community` repository's own
`CONTRIBUTING.md`.

---

## 15. Getting help

- **GitHub Discussions** — questions, ideas, RFC-level proposals:
  <https://github.com/pumacp/puma-community/discussions>.
- **Discord** — informal chat, async questions:
  <https://discord.gg/fVhcpHREJv>.
- **GitHub Issues** — bug reports, feature requests with a concrete
  surface change: <https://github.com/pumacp/puma/issues>.

For Code-of-Conduct concerns, see
[`CODE_OF_CONDUCT.md`](https://github.com/pumacp/puma/blob/develop/CODE_OF_CONDUCT.md)
for the private reporting channel.

---

## 16. Appendix — worked example (PR #47)

A short walk-through of a real PR, useful as a concrete template for
your first contribution.

### What it did

PR #47 ("docs: skip acrostic immutability tests + restructure README
header") was a maintainer cosmetic edit that did two things:

1. Restructured `README.md`'s header into a categorized channel
   directory (Code / Documentation sites / Hugging Face / Archives /
   Community channels) and repositioned the acrostic block into a
   two-column HTML table inside a collapsible-style wrapper.
2. Relaxed the three acrostic-immutability tests by adding
   `@pytest.mark.skip` decorators, so future cosmetic edits to the
   acrostic block would not break the suite.

### What the commands looked like

```bash
# Sync.
git checkout develop && git pull --ff-only && git fetch --prune

# Branch.
git checkout -b docs/cosmetic-edits-and-relax-acrostic-tests

# Edit README.md in the IDE.
# Edit the two test files to add @pytest.mark.skip.

# Verify.
git status
git diff README.md
ruff check src/ tests/
pytest tests/integration/test_pages_content_audit.py \
       tests/integration/test_readme_acrostic_and_resources.py -v

# Commit.
git add README.md tests/integration/test_pages_content_audit.py \
        tests/integration/test_readme_acrostic_and_resources.py
git commit -m "docs: skip acrostic immutability tests + restructure README header"

# Push.
git push -u origin docs/cosmetic-edits-and-relax-acrostic-tests

# PR.
gh pr create --base develop \
  --title "docs: skip acrostic immutability tests + restructure README header" \
  --body  "Visual restructure of the README header into a categorized
channel directory; the acrostic block moves into a two-column table.
The three acrostic-immutability tests are relaxed (@pytest.mark.skip)
so future cosmetic edits do not break the suite."

# Wait for CI.
sleep 60
gh pr checks

# Merge on green.
gh pr merge --rebase --delete-branch

# Sync.
git checkout develop && git pull --ff-only
```

### What CI did

Three workflows ran, all green:

| Workflow | Job | Result |
|---|---|---|
| Lint and Test | `lint-and-test` | SUCCESS |
| Smoke Test | `smoke` | SUCCESS |
| Docs | `build` | SUCCESS |

`Integration tests with Ollama` was SKIPPED (PR-only; that workflow
gates on a label and only runs on pushes to `main`).

### What got merged

A single rebased commit on top of `develop`, with the maintainer's
identity as the sole author. No `Co-authored-by:` lines, no
`Generated-by:` footers — the `.githooks/commit-msg` hook keeps the
attribution clean.

The commit hash (`ba00edb`) is recoverable in `git log`; the PR
remains visible at <https://github.com/pumacp/puma/pull/47>.

---

If anything in this guide is wrong or out of date, open a PR with
the fix — `docs/` is not locked.
