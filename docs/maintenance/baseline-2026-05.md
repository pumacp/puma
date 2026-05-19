# Technical-debt baseline — Phase 0 (May 2026)

| Field | Value |
| --- | --- |
| Date captured | 2026-05-19 |
| Academic repo branch | `feature/community-v1` |
| Academic HEAD | `9b4666a` |
| Academic base tag | `v2.7.0-academic` (`321ff26`) |
| Community repo branch | `main` |
| Community HEAD | `0223642` |
| mypy version | `mypy >= 1.10` (project dep, executed inside `puma_runner` container) |
| ruff version | `0.15.12` |
| Test count | 571 collected (570 passing + 1 skipped) |

This document is the **input** for the Phase 1–4 remediation effort. No
source files are modified in Phase 0; only this report is added under
`docs/maintenance/`.

## 1. Executive summary

The academic codebase currently emits **104 mypy errors across 29 files**
when checked under the project's `[tool.mypy]` configuration. The
identical count of 104 errors is observed at the pre-v5 baseline
(`v2.7.0-academic`), confirming that **Plan v5 introduced zero net
regressions**: the five "introduced" and five "fixed" entries in the
sorted diff are the same five `cli.py` errors with line numbers shifted
by three (a consequence of `puma.cli` gaining the `auth` and
`share-results` sub-app registrations). The ruff lint suite is clean
across `src/puma/` and `tests/`; the full pytest suite passes (571
collected, 570 passing, 1 explicitly skipped). The community repository
audit found no defects: all nine GitHub Actions workflows parse as valid
YAML, `schema/submission.v1.json` self-validates as a JSON Schema
2020-12 document, `notebooks/sample_submission.json` validates against
it, and ruff on `scripts/` reports "All checks passed". The single
material CI gap is that the `lint-and-test.yml` workflow runs ruff +
pytest only — it does **not** invoke mypy, which is why the 104 errors
have accumulated silently.

## 2. Academic repo: mypy baseline

### 2.1 Pre-v5 baseline (`v2.7.0-academic`, commit `321ff26`)

- Total errors: **104** in 29 files (checked 63 source files).
- The baseline tag does not contain the `puma.community.*` package, so
  the 13-file delta in "checked source files" between pre-v5 (63) and
  post-v5 (76) is entirely the new community package.

First 20 lines of `/tmp/mypy-pre-v5-raw.txt`:

```
src/puma/scenarios/base.py:28: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/examples.py:14: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/examples.py:47: error: Returning Any from function declared to return "list[dict[Any, Any]]"  [no-any-return]
src/puma/perturbations/text.py:74: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:85: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:89: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/puma/scenarios/estimation_tawos.py:95: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:156: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:206: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:206: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:228: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:238: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:49: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:53: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/puma/scenarios/triage_jira.py:59: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:90: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:118: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/triage_jira.py:161: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/triage_jira.py:161: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/prioritization_jira.py:27: error: Cannot override instance variable (previously declared on base class "Scenario") with class variable  [misc]
```

### 2.2 Current baseline (`feature/community-v1`, commit `9b4666a`)

- Total errors: **104** in 29 files (checked 76 source files).
- The 13 new files in `src/puma/community/` (introduced by Plan v5)
  contribute **zero** mypy errors — the community package was written
  fully type-annotated from the start.

First 20 lines of `/tmp/mypy-post-v5-raw.txt`:

```
src/puma/scenarios/base.py:28: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/examples.py:14: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/examples.py:47: error: Returning Any from function declared to return "list[dict[Any, Any]]"  [no-any-return]
src/puma/perturbations/text.py:74: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:85: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:89: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/puma/scenarios/estimation_tawos.py:95: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:156: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:206: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:206: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:228: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:238: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:49: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:53: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/puma/scenarios/triage_jira.py:59: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:90: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:118: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/triage_jira.py:161: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/triage_jira.py:161: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/prioritization_jira.py:27: error: Cannot override instance variable (previously declared on base class "Scenario") with class variable  [misc]
```

### 2.3 Delta

Sorted-diff comparison (`comm -13 pre post`, `comm -23 pre post`):

| Bucket | Count | Interpretation |
| --- | --- | --- |
| Errors introduced by Plan v5 | **5** (all in `src/puma/cli.py`) | Line-number shifts only |
| Errors fixed by Plan v5 | **5** (all in `src/puma/cli.py`) | Same five errors at the old line numbers |
| Net regressions | **0** | Identical error set, modulo line drift |

The five entries in each direction are pairwise identical except for
line numbers that drift by exactly 3 (e.g. `cli.py:460 → cli.py:463`,
`cli.py:849 → cli.py:852`). The drift is the inline insertion of `auth`
and `share-results` sub-app registrations in the CLI module between
v2.7.0 and HEAD; the underlying defects (missing type arguments on
`dict` / `list`) are the same five untouched lines of code, just
relocated. **Plan v5 introduced no genuine mypy regressions.**

## 3. Academic repo: error categorisation

### 3.1 By error-type

```
     59 Missing type arguments for generic type "dict"
     10 Missing type arguments for generic type "list"
      7 Function is missing a return type annotation
      4 Incompatible types in assignment (expression has type "Callable[[Any], str]", target has type "Callable[[Any, Any], str]")
      4 Function is missing a type annotation for one or more parameters
      4 Cannot infer type of lambda
      2 Returning Any from function declared to return "list[str]"
      2 Returning Any from function declared to return "dict[Any, Any]"
      2 Missing type arguments for generic type "Callable"
      1 Returning Any from function declared to return "list[dict[Any, Any]]"
      1 "object" has no attribute "sample"
      1 "object" has no attribute "parse_response"
      1 "object" has no attribute "gold_label"
      1 "Engine" has no attribute "execute"
      1 Cannot override instance variable (previously declared on base class "Scenario") with class variable
      1 Call to untyped function "get_session_factory" in typed context
      1 Call to untyped function "_empty_dataframe" in typed context
      1 Argument 2 to "expected_calibration_error" has incompatible type "list[int]"; expected "list[bool]"
      1 Argument 1 to "build_prompt" of "Strategy" has incompatible type "object"; expected "Scenario"
```

Total: 104 errors / 19 distinct error texts.

### 3.2 By file

```
     30 src/puma/orchestrator/runner.py
      8 src/puma/scenarios/estimation_tawos.py
      7 src/puma/scenarios/triage_jira.py
      7 src/puma/runtime/client.py
      5 src/puma/storage/db.py
      5 src/puma/cli.py
      5 src/puma/adaptation/strategies.py
      3 src/puma/sustainability/codecarbon_wrapper.py
      3 src/puma/runtime/cache.py
      3 src/puma/metrics/accuracy.py
      3 src/puma/dashboard/views/fairness.py
      3 src/puma/dashboard/components.py
      2 src/puma/scenarios/prioritization_jira.py
      2 src/puma/metrics/fairness.py
      2 src/puma/dashboard/views/_base.py
      2 src/puma/adaptation/examples.py
      2 src/puma/adaptation/base.py
      1 src/puma/storage/models.py
      1 src/puma/storage/history.py
      1 src/puma/scenarios/base.py
      1 src/puma/preflight/report.py
      1 src/puma/perturbations/text.py
      1 src/puma/orchestrator/runspec.py
      1 src/puma/orchestrator/compare.py
      1 src/puma/metrics/stability.py
      1 src/puma/metrics/efficiency.py
      1 src/puma/metrics/calibration.py
      1 src/puma/dashboard/views/robustness.py
      1 src/puma/dashboard/data.py
```

Total: 104 errors / 29 files. Two files concentrate the bulk:
`orchestrator/runner.py` alone holds 28.8 % (30/104) and the two
scenario implementations (`estimation_tawos.py` + `triage_jira.py`) add
another 14.4 % (15/104).

### 3.3 Risk classification

Each of the 19 distinct error texts is labelled as **MECHANICAL** (safe
to fix in batch with a typing rule), **JUDGEMENT** (requires reading the
function body to choose a correct annotation), or **POTENTIAL BUG** (a
mypy complaint that may surface a real defect once typed properly).

| # | Error text (truncated) | Count | Risk | Rationale |
| --- | --- | --- | --- | --- |
| 1 | Missing type arguments for generic type "dict" | 59 | **MECHANICAL** | Bulk rename `dict` → `dict[str, Any]` (or narrower) by visual inspection. Cannot regress runtime behaviour. |
| 2 | Missing type arguments for generic type "list" | 10 | **MECHANICAL** | Bulk rename `list` → `list[T]`. Same reasoning. |
| 3 | Missing type arguments for generic type "Callable" | 2 | **MECHANICAL** | `Callable` → `Callable[..., Any]` or precise signature. |
| 4 | Function is missing a return type annotation | 7 | **JUDGEMENT** | Must read each function to determine the return type. Trivial in most cases, but not blind. |
| 5 | Function is missing a type annotation for one or more parameters | 4 | **JUDGEMENT** | Same as above for parameters. |
| 6 | Cannot infer type of lambda | 4 | **JUDGEMENT** | All four are paired with the assignment error (#7) on the same lines (`runner.py:480`, `:482`, `:484`, `:492`); resolving the assignment fixes the lambda inference too. |
| 7 | Incompatible types in assignment (`Callable[[Any], str]` vs `Callable[[Any, Any], str]`) | 4 | **POTENTIAL BUG** | This may indicate a real arity mismatch in the metrics-formatter dispatch table at `orchestrator/runner.py:480-492`. Review each lambda against the call site before annotating. |
| 8 | Returning Any from function declared to return "list[str]" | 2 | **POTENTIAL BUG** | The function claims `list[str]` but returns something mypy can only see as `Any`. The fix may be a `cast`, or it may surface a genuine type mismatch (e.g. returning `list[int]`). Review one-by-one. |
| 9 | Returning Any from function declared to return "dict[Any, Any]" | 2 | **POTENTIAL BUG** | Same pattern; investigate whether the declared type is truthful. |
| 10 | Returning Any from function declared to return "list[dict[Any, Any]]" | 1 | **POTENTIAL BUG** | Same pattern. |
| 11 | "object" has no attribute "sample" | 1 | **POTENTIAL BUG** | `runner.py:190` — the variable is typed as `object` (too wide). Likely needs a `Scenario`-aware annotation; see #14. |
| 12 | "object" has no attribute "parse_response" | 1 | **POTENTIAL BUG** | `runner.py:257` — same root cause. |
| 13 | "object" has no attribute "gold_label" | 1 | **POTENTIAL BUG** | `runner.py:218` — same root cause. |
| 14 | Argument 1 to "build_prompt" of "Strategy" has incompatible type "object"; expected "Scenario" | 1 | **POTENTIAL BUG** | `runner.py:225` — confirms #11/#12/#13: a `Scenario` is being passed as `object`. A single, well-placed `Scenario` annotation likely closes all four. |
| 15 | "Engine" has no attribute "execute" | 1 | **POTENTIAL BUG** | `storage/db.py:65` — SQLAlchemy 2.0 deprecated `Engine.execute()`; this is real code smell to investigate. Probably needs `with engine.connect() as conn: conn.execute(...)`. |
| 16 | Cannot override instance variable (previously declared on base class "Scenario") with class variable | 1 | **JUDGEMENT** | `scenarios/prioritization_jira.py:27` — re-declaring a parent's instance attribute at class level. Decide intent: change parent to `ClassVar` or remove the override. |
| 17 | Call to untyped function "get_session_factory" in typed context | 1 | **JUDGEMENT** | Cascade fix: annotate `get_session_factory` and the error vanishes. |
| 18 | Call to untyped function "_empty_dataframe" in typed context | 1 | **JUDGEMENT** | Same; annotate `_empty_dataframe`. |
| 19 | Argument 2 to "expected_calibration_error" has incompatible type "list[int]"; expected "list[bool]" | 1 | **POTENTIAL BUG** | `orchestrator/runner.py:360` — passing 0/1 integers where the metric expects booleans. Either widen the metric signature, or fix the caller to pass `bool` values. Either way, worth confirming before annotating. |

Aggregate:

- **MECHANICAL**: 71 errors (68.3 %) — items 1-3.
- **JUDGEMENT**: 17 errors (16.3 %) — items 4-6, 16-18.
- **POTENTIAL BUG**: 16 errors (15.4 %) — items 7-15, 19.

The MECHANICAL bucket is large enough that a single Phase-1 pass on
`dict` / `list` / `Callable` generic arguments closes roughly two-thirds
of the backlog and leaves the smaller, judgement-heavy work for
Phase 2+.

## 4. Academic repo: configuration

### 4.1 Current `[tool.mypy]` section

```toml
[tool.mypy]
python_version = "3.11"
strict = false
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
exclude = ["alembic/versions/", "scripts/"]

[[tool.mypy.overrides]]
module = ["puma.metrics.*", "puma.runtime.*", "puma.preflight.*"]
strict = true
```

Notes:

- `strict = false` globally, with an opt-in `strict = true` override
  for three modules (`metrics`, `runtime`, `preflight`).
- `warn_unused_configs = true` is on — if the override module patterns
  did not match any source, mypy itself would warn. No such warning
  appears in the current output, indicating the override block is
  effective.
- `warn_return_any = true` is the reason items 8/9/10 in §3.3 surface as
  errors rather than silently passing.

### 4.2 Unused-overrides analysis

The three module patterns in the `[[tool.mypy.overrides]]` block are
checked against the filesystem:

| Pattern | Target directory | Exists? | Files (sample) |
| --- | --- | --- | --- |
| `puma.metrics.*` | `src/puma/metrics/` | ✅ Present | `accuracy.py`, `calibration.py`, `efficiency.py`, `fairness.py`, `stability.py` |
| `puma.preflight.*` | `src/puma/preflight/` | ✅ Present | `apple_silicon.py`, `catalog.py`, `report.py` |
| `puma.runtime.*` | `src/puma/runtime/` | ✅ Present | `cache.py`, `client.py` |

All three modules exist as packages with current source files. **No
unused overrides.** The "unused mypy overrides" hypothesis raised
during pre-Phase-0 triage is not supported by the evidence: the
`warn_unused_configs = true` flag would emit a `[unused-configs]`
warning if any of the patterns matched nothing, and no such warning
appears in `/tmp/mypy-post-v5-raw.txt`.

The stricter `[[overrides]]` block is in fact contributing to the
error count: items 7–10, 11–14, and 19 from §3.3 are predominantly in
`runtime/client.py`, `metrics/*.py`, and `orchestrator/runner.py`
(where `runner.py` is **not** under strict mode but imports symbols
from the strict modules). Loosening the override would mask the
`POTENTIAL BUG` cluster — **the override should be preserved through
the remediation**.

## 5. Academic repo: CI workflows

### 5.1 Workflow files

```
.github/workflows/
├── lint-and-test.yml   2615 bytes  (89 lines)
├── release.yml         1902 bytes  (51 lines)
└── smoke.yml           1656 bytes  (52 lines)
```

### 5.2 Per-workflow audit

#### `lint-and-test.yml`

- **Trigger**: `push` to `main` / `develop`, and `pull_request` against
  `main` / `develop`.
- **Scope**: `src/puma/` and `tests/`.
- **Steps**:
  1. `ruff check src/puma/ tests/` — fails on any lint violation.
  2. `ruff format --check src/puma/ tests/` — fails on any format
     deviation.
  3. `pytest tests/unit/ -q --no-header --tb=short` — fails on any unit
     test failure.
  4. `pytest tests/integration/ -q --no-header --tb=short -m "not
     ollama"` — runs the non-ollama-marked integration tests.
  5. Second job `integration-tests-ollama` installs Ollama + `qwen2.5:1.5b`
     and runs the ollama-marked tests. **Marked `continue-on-error:
     true`** so failures are surfaced but non-blocking.
- **Strictness**: fail-fast on ruff + non-ollama tests; non-blocking on
  ollama tests.
- ⚠️ **mypy is not invoked anywhere in this workflow.** This is the
  primary reason the 104 mypy errors have accumulated silently across
  the project's history. Adding a `mypy src/puma/` step is the obvious
  Phase 4 gate — but only after Phase 1–3 have driven the count to
  zero.

#### `release.yml`

- **Trigger**: `push` to tags matching `v*`.
- **Scope**: build and upload a wheel artifact.
- **Strictness**: the workflow only **uploads** to an existing release;
  it polls up to 60 s for a `gh release create` to have completed
  manually. No lint/test gates here (already enforced upstream by
  `lint-and-test.yml`).
- **Note**: the workflow contains a long inline comment explaining a
  prior race condition with manual release creation (duplicated draft on
  `v2.2.0`). Unrelated to the type-debt remediation.

#### `smoke.yml`

- **Trigger**: `push` / `pull_request` to `main` / `develop`, plus
  `workflow_dispatch`.
- **Scope**: dashboard smoke tests (`pytest tests/smoke/ -m smoke`)
  followed by a one-iteration dry-run benchmark against
  `qwen2.5:0.5b`.
- **Strictness**: fails the run on any smoke-test or dry-run failure;
  Ollama installation is in-line.

### 5.3 Recent run status

The five most recent `lint-and-test.yml` runs (via `gh run list`):

```
completed  success  docs: formal closure of technical implementation phase at v2.7.0    Lint and Test  develop                                  push          25959124317  2m21s  2026-05-16T10:01:49Z
completed  success  docs(release): consolidate v2.7.0 — catalog expansion + Kimi K2.6  Lint and Test  main                                     push          25953236804  2m12s  2026-05-16T04:54:29Z
completed  success  docs(release): consolidate v2.7.0 — catalog expansion + Kimi K2.6  Lint and Test  develop                                  push          25953233929  1m56s  2026-05-16T04:54:18Z
completed  success  Merge pull request #12 from pumacp/feature/sprint-10-models-...    Lint and Test  develop                                  push          25953130372  1m37s  2026-05-16T04:48:40Z
completed  success  Sprint 10 (v2.7.0): Qwen3 catalog expansion (gpu-high, pending...  Lint and Test  feature/sprint-10-models-expansion        pull_request  25952759676  1m1s   2026-05-16T04:29:17Z
```

All five recent runs are **green** on `develop` and `main`. The current
`feature/community-v1` branch has not yet been pushed to `origin`, so
no CI run exists for it; the local docker container check (ruff clean,
pytest 570 passed + 1 skipped, mypy 104 errors) is the proxy.

## 6. Community repo: audit

### 6.1 Inventory

| Category | Count | Notes |
| --- | --- | --- |
| Workflow YAMLs | 9 | `auto-merge-valid`, `mirror-{huggingface,kaggle,zenodo}`, `notify-{discord,telegram}`, `update-badges`, `validate-submission`, `wiki-sync` |
| Top-level docs | 5 | `README`, `CONTRIBUTING`, `CODE_OF_CONDUCT`, `MAINTAINERS`, `LICENSE` |
| `docs/` markdown | 5 | `colab-demo`, `maintainer-guide`, `mirrors-setup`, `notifiers-setup`, `oracle-cloud-deployment` |
| `wiki/` markdown | 3 | `FAQ`, `Home`, `Submission-Format` |
| Python scripts | 4 | `build_demo_notebook.py`, `generate_badges.py`, `mirror_zenodo.py`, `notify.py` |
| Schema artifacts | 1 | `schema/submission.v1.json` |
| Sample submission | 1 | `notebooks/sample_submission.json` |
| Demo notebook | 1 | `notebooks/puma_community_demo.ipynb` |
| Badge JSONs | 4 | `submission-count`, `models-count`, `scenarios-count`, `latest-submission` |

### 6.2 YAML workflow syntax

All nine workflow YAMLs parse cleanly under `yaml.safe_load`:

```
  ✓ .github/workflows/auto-merge-valid.yml
  ✓ .github/workflows/mirror-huggingface.yml
  ✓ .github/workflows/mirror-kaggle.yml
  ✓ .github/workflows/mirror-zenodo.yml
  ✓ .github/workflows/notify-discord.yml
  ✓ .github/workflows/notify-telegram.yml
  ✓ .github/workflows/update-badges.yml
  ✓ .github/workflows/validate-submission.yml
  ✓ .github/workflows/wiki-sync.yml
```

**Result**: 9/9 valid. No failures.

### 6.3 JSON Schema self-validation

`schema/submission.v1.json` was checked with
`jsonschema.Draft202012Validator.check_schema(...)`:

```
✓ schema/submission.v1.json is a valid JSON Schema 2020-12 document
```

**Result**: pass.

### 6.4 Sample submission validation

`notebooks/sample_submission.json` was validated against
`schema/submission.v1.json`:

```
✓ notebooks/sample_submission.json validates against the schema
```

**Result**: pass.

### 6.5 Python script linting

`ruff check /community/scripts/` (executed inside `puma_runner` against
the mounted community working tree):

```
All checks passed!
```

**Result**: clean across all four scripts.

### 6.6 Markdown file inventory

```
 20  ./CODE_OF_CONDUCT.md
130  ./CONTRIBUTING.md
 52  ./docs/colab-demo.md
190  ./docs/maintainer-guide.md
106  ./docs/mirrors-setup.md
102  ./docs/notifiers-setup.md
168  ./docs/oracle-cloud-deployment.md
 20  ./.github/PULL_REQUEST_TEMPLATE.md
 44  ./MAINTAINERS.md
213  ./README.md
 39  ./submissions/README.md
 97  ./wiki/FAQ.md
 41  ./wiki/Home.md
119  ./wiki/Submission-Format.md
```

Total: 14 markdown files / 1,341 lines. **No markdown lint applied at
Phase 0** — that is reserved for Phase 1 (documentation polish).

## 7. Remediation plan reference

This baseline document is the **Phase 0 deliverable** for the
multi-phase remediation effort that begins after the
`feature/community-v1` work is merged. The subsequent phases are
expected to be:

- **Phase 1** — mechanical typing pass: close the 71 generic-arity
  errors (`dict`, `list`, `Callable`) in a single sweep without altering
  runtime behaviour.
- **Phase 2** — judgement-heavy typing pass: annotate the 17 missing
  return/parameter types and the 4 lambda assignments, reading each
  function before writing the annotation.
- **Phase 3** — potential-bug triage: investigate the 16 errors in the
  `POTENTIAL BUG` bucket (notably the `Engine.execute` call, the
  `bool` vs `int` mismatch in `expected_calibration_error`, and the
  `object`-typed `Scenario` parameter cluster in `runner.py`).
- **Phase 4** — CI gating: once the error count reaches zero, add a
  `mypy src/puma/` step to `.github/workflows/lint-and-test.yml` so
  any regression fails CI.

The community repository is **not** included in the remediation plan —
its audit confirms a clean state at v1.0.0.

## 8. Appendix A — full current (post-v5) mypy output

```
src/puma/scenarios/base.py:28: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/examples.py:14: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/examples.py:47: error: Returning Any from function declared to return "list[dict[Any, Any]]"  [no-any-return]
src/puma/perturbations/text.py:74: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:85: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:89: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/puma/scenarios/estimation_tawos.py:95: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:156: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:206: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:206: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:228: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:238: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:49: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:53: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/puma/scenarios/triage_jira.py:59: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:90: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:118: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/triage_jira.py:161: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/triage_jira.py:161: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/prioritization_jira.py:27: error: Cannot override instance variable (previously declared on base class "Scenario") with class variable  [misc]
src/puma/scenarios/prioritization_jira.py:60: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/preflight/report.py:48: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src/puma/orchestrator/runspec.py:20: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/storage/models.py:144: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/base.py:37: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/base.py:38: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/storage/history.py:122: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/metrics/stability.py:25: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/fairness.py:16: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/fairness.py:63: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/efficiency.py:30: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/accuracy.py:28: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/accuracy.py:59: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/accuracy.py:89: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/strategies.py:42: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/strategies.py:43: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/strategies.py:65: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/strategies.py:66: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/strategies.py:128: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/storage/db.py:27: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/storage/db.py:65: error: "Engine" has no attribute "execute"  [attr-defined]
src/puma/storage/db.py:69: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/storage/db.py:75: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/storage/db.py:84: error: Call to untyped function "get_session_factory" in typed context  [no-untyped-call]
src/puma/runtime/client.py:37: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:40: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:64: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:67: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:88: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:125: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:185: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/compare.py:8: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/cache.py:28: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/cache.py:52: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/cache.py:113: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/dashboard/data.py:19: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/dashboard/views/_base.py:19: error: Returning Any from function declared to return "list[str]"  [no-any-return]
src/puma/dashboard/views/_base.py:24: error: Returning Any from function declared to return "list[str]"  [no-any-return]
src/puma/metrics/calibration.py:76: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/dashboard/components.py:89: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/dashboard/components.py:114: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/dashboard/components.py:135: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src/puma/sustainability/codecarbon_wrapper.py:89: error: Missing type arguments for generic type "Callable"  [type-arg]
src/puma/sustainability/codecarbon_wrapper.py:99: error: Missing type arguments for generic type "Callable"  [type-arg]
src/puma/sustainability/codecarbon_wrapper.py:136: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/dashboard/views/robustness.py:37: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/dashboard/views/fairness.py:40: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/dashboard/views/fairness.py:41: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/dashboard/views/fairness.py:46: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:94: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:172: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:190: error: "object" has no attribute "sample"  [attr-defined]
src/puma/orchestrator/runner.py:193: error: Call to untyped function "_empty_dataframe" in typed context  [no-untyped-call]
src/puma/orchestrator/runner.py:199: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:218: error: "object" has no attribute "gold_label"  [attr-defined]
src/puma/orchestrator/runner.py:225: error: Argument 1 to "build_prompt" of "Strategy" has incompatible type "object"; expected "Scenario"  [arg-type]
src/puma/orchestrator/runner.py:232: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/orchestrator/runner.py:257: error: "object" has no attribute "parse_response"  [attr-defined]
src/puma/orchestrator/runner.py:306: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:360: error: Argument 2 to "expected_calibration_error" has incompatible type "list[int]"; expected "list[bool]"  [arg-type]
src/puma/orchestrator/runner.py:365: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:403: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:424: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:430: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/orchestrator/runner.py:456: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/orchestrator/runner.py:456: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:470: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:480: error: Cannot infer type of lambda  [misc]
src/puma/orchestrator/runner.py:480: error: Incompatible types in assignment (expression has type "Callable[[Any], str]", target has type "Callable[[Any, Any], str]")  [assignment]
src/puma/orchestrator/runner.py:482: error: Cannot infer type of lambda  [misc]
src/puma/orchestrator/runner.py:482: error: Incompatible types in assignment (expression has type "Callable[[Any], str]", target has type "Callable[[Any, Any], str]")  [assignment]
src/puma/orchestrator/runner.py:484: error: Cannot infer type of lambda  [misc]
src/puma/orchestrator/runner.py:484: error: Incompatible types in assignment (expression has type "Callable[[Any], str]", target has type "Callable[[Any, Any], str]")  [assignment]
src/puma/orchestrator/runner.py:492: error: Cannot infer type of lambda  [misc]
src/puma/orchestrator/runner.py:492: error: Incompatible types in assignment (expression has type "Callable[[Any], str]", target has type "Callable[[Any, Any], str]")  [assignment]
src/puma/orchestrator/runner.py:496: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src/puma/orchestrator/runner.py:496: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:506: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:517: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src/puma/cli.py:463: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/cli.py:574: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/cli.py:852: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/cli.py:853: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/cli.py:904: error: Missing type arguments for generic type "dict"  [type-arg]
Found 104 errors in 29 files (checked 76 source files)
```

## 9. Appendix B — full pre-v5 mypy output (`v2.7.0-academic`, `321ff26`)

```
src/puma/scenarios/base.py:28: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/examples.py:14: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/examples.py:47: error: Returning Any from function declared to return "list[dict[Any, Any]]"  [no-any-return]
src/puma/perturbations/text.py:74: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:85: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:89: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/puma/scenarios/estimation_tawos.py:95: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:156: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:206: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:206: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/estimation_tawos.py:228: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/estimation_tawos.py:238: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:49: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:53: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/puma/scenarios/triage_jira.py:59: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:90: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/triage_jira.py:118: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/triage_jira.py:161: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/scenarios/triage_jira.py:161: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/scenarios/prioritization_jira.py:27: error: Cannot override instance variable (previously declared on base class "Scenario") with class variable  [misc]
src/puma/scenarios/prioritization_jira.py:60: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/preflight/report.py:48: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src/puma/orchestrator/runspec.py:20: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/storage/models.py:144: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/base.py:37: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/base.py:38: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/storage/history.py:122: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/metrics/stability.py:25: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/fairness.py:16: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/fairness.py:63: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/efficiency.py:30: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/accuracy.py:28: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/accuracy.py:59: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/metrics/accuracy.py:89: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/strategies.py:42: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/strategies.py:43: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/strategies.py:65: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/strategies.py:66: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/adaptation/strategies.py:128: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/storage/db.py:27: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/storage/db.py:65: error: "Engine" has no attribute "execute"  [attr-defined]
src/puma/storage/db.py:69: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/storage/db.py:75: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/storage/db.py:84: error: Call to untyped function "get_session_factory" in typed context  [no-untyped-call]
src/puma/runtime/client.py:37: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:40: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:64: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:67: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:88: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:125: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/client.py:185: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/compare.py:8: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/cache.py:28: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/cache.py:52: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/runtime/cache.py:113: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/dashboard/data.py:19: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/dashboard/views/_base.py:19: error: Returning Any from function declared to return "list[str]"  [no-any-return]
src/puma/dashboard/views/_base.py:24: error: Returning Any from function declared to return "list[str]"  [no-any-return]
src/puma/metrics/calibration.py:76: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/dashboard/components.py:89: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/dashboard/components.py:114: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/dashboard/components.py:135: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src/puma/sustainability/codecarbon_wrapper.py:89: error: Missing type arguments for generic type "Callable"  [type-arg]
src/puma/sustainability/codecarbon_wrapper.py:99: error: Missing type arguments for generic type "Callable"  [type-arg]
src/puma/sustainability/codecarbon_wrapper.py:136: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/dashboard/views/robustness.py:37: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/dashboard/views/fairness.py:40: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/dashboard/views/fairness.py:41: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/dashboard/views/fairness.py:46: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:94: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:172: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:190: error: "object" has no attribute "sample"  [attr-defined]
src/puma/orchestrator/runner.py:193: error: Call to untyped function "_empty_dataframe" in typed context  [no-untyped-call]
src/puma/orchestrator/runner.py:199: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:218: error: "object" has no attribute "gold_label"  [attr-defined]
src/puma/orchestrator/runner.py:225: error: Argument 1 to "build_prompt" of "Strategy" has incompatible type "object"; expected "Scenario"  [arg-type]
src/puma/orchestrator/runner.py:232: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/orchestrator/runner.py:257: error: "object" has no attribute "parse_response"  [attr-defined]
src/puma/orchestrator/runner.py:306: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:360: error: Argument 2 to "expected_calibration_error" has incompatible type "list[int]"; expected "list[bool]"  [arg-type]
src/puma/orchestrator/runner.py:365: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:403: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:424: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:430: error: Function is missing a return type annotation  [no-untyped-def]
src/puma/orchestrator/runner.py:456: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/orchestrator/runner.py:456: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:470: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:480: error: Cannot infer type of lambda  [misc]
src/puma/orchestrator/runner.py:480: error: Incompatible types in assignment (expression has type "Callable[[Any], str]", target has type "Callable[[Any, Any], str]")  [assignment]
src/puma/orchestrator/runner.py:482: error: Cannot infer type of lambda  [misc]
src/puma/orchestrator/runner.py:482: error: Incompatible types in assignment (expression has type "Callable[[Any], str]", target has type "Callable[[Any, Any], str]")  [assignment]
src/puma/orchestrator/runner.py:484: error: Cannot infer type of lambda  [misc]
src/puma/orchestrator/runner.py:484: error: Incompatible types in assignment (expression has type "Callable[[Any], str]", target has type "Callable[[Any, Any], str]")  [assignment]
src/puma/orchestrator/runner.py:492: error: Cannot infer type of lambda  [misc]
src/puma/orchestrator/runner.py:492: error: Incompatible types in assignment (expression has type "Callable[[Any], str]", target has type "Callable[[Any, Any], str]")  [assignment]
src/puma/orchestrator/runner.py:496: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src/puma/orchestrator/runner.py:496: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:506: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/orchestrator/runner.py:517: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src/puma/cli.py:460: error: Missing type arguments for generic type "list"  [type-arg]
src/puma/cli.py:571: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/cli.py:849: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/cli.py:850: error: Missing type arguments for generic type "dict"  [type-arg]
src/puma/cli.py:901: error: Missing type arguments for generic type "dict"  [type-arg]
Found 104 errors in 29 files (checked 63 source files)
```

## 10. Appendix C — full CI workflow contents

```yaml
=== .github/workflows/lint-and-test.yml ===
name: Lint and Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Ruff lint
        run: ruff check src/puma/ tests/

      - name: Ruff format check
        run: ruff format --check src/puma/ tests/

      - name: Unit tests
        env:
          PYTHONPATH: src
        run: pytest tests/unit/ -q --no-header --tb=short

      - name: Integration tests
        env:
          PYTHONPATH: src
        run: pytest tests/integration/ -q --no-header --tb=short -m "not ollama"

  integration-tests-ollama:
    name: Integration tests with Ollama
    runs-on: ubuntu-latest
    # Only run on push to main/develop, not on PRs — installing Ollama and
    # pulling a model is too expensive for every PR push. The job exists to
    # catch Ollama-side regressions on the integration branches.
    if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop')
    timeout-minutes: 30
    # Non-blocking for PR merges (different trigger). Failures here are
    # surfaced via the workflow run page and notify the maintainers without
    # gating the merge queue.
    continue-on-error: true

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Install Ollama
        run: |
          curl -fsSL https://ollama.com/install.sh | sh
          ollama serve > /tmp/ollama.log 2>&1 &
          # Wait for the server to accept connections (≤30 s)
          for i in $(seq 1 30); do
            if curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
              echo "Ollama ready after ${i}s"
              break
            fi
            sleep 1
          done

      - name: Pull minimal model (qwen2.5:1.5b)
        run: ollama pull qwen2.5:1.5b

      - name: Run ollama-marked tests
        env:
          PYTHONPATH: src
          OLLAMA_HOST: http://localhost:11434
          PUMA_OLLAMA_HOST: http://localhost:11434
        timeout-minutes: 15
        run: pytest tests/ -m ollama -v --no-cov --tb=short

=== .github/workflows/release.yml ===
name: Release

on:
  push:
    tags:
      - "v*"

permissions:
  contents: write   # required for softprops/action-gh-release@v2 to create releases

jobs:
  release:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install build tools
        run: pip install build

      - name: Build wheel
        run: python -m build --wheel

      - name: Upload wheel to release
        # The release itself is created manually via `gh release create` in
        # the Phase E (and E.bis) release procedure with curated notes from
        # docs/RELEASES/<tag>.md. Before this change, the workflow also
        # created the release with auto-generated notes, which raced the
        # manual create on tag push and produced a duplicate draft (e.g.
        # v2.2.0 1:02:06 UTC, both manual and workflow creates landed in
        # the same second). The workflow now only uploads the wheel to an
        # existing release, polling for up to 60 s in case the manual
        # `gh release create` is still in flight.
        run: |
          set -euo pipefail
          for i in $(seq 1 12); do
            if gh release view "${GITHUB_REF_NAME}" \
                 --repo "${GITHUB_REPOSITORY}" >/dev/null 2>&1; then
              gh release upload "${GITHUB_REF_NAME}" dist/*.whl --clobber
              exit 0
            fi
            echo "Release ${GITHUB_REF_NAME} not found yet (attempt ${i}/12); retrying in 5 s..."
            sleep 5
          done
          echo "::error::Release ${GITHUB_REF_NAME} not found after 60 s. Create it manually with 'gh release create ${GITHUB_REF_NAME} --notes-file docs/RELEASES/${GITHUB_REF_NAME}.md', then re-run this workflow."
          exit 1
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

=== .github/workflows/smoke.yml ===
name: Smoke Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:

jobs:
  smoke:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install Ollama
        run: |
          curl -fsSL https://ollama.ai/install.sh | sh
          ollama serve &
          sleep 5

      - name: Pull small model
        run: ollama pull qwen2.5:0.5b

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Dashboard smoke tests (no Ollama needed)
        env:
          PYTHONPATH: src
        run: pytest tests/smoke/ -v --no-header -m smoke

      - name: Dry-run benchmark
        env:
          PYTHONPATH: src
          OLLAMA_HOST: http://localhost:11434
        run: |
          python -c "
          from puma.orchestrator.runspec import RunSpec
          from puma.orchestrator.runner import Runner
          import tempfile, pathlib
          spec = RunSpec(
            id='ci_smoke', scenario='triage_jira', sample_size=3,
            models=['qwen2.5:0.5b'],
            adaptation={'strategy': ['zero-shot']},
            inference={'temperature': 0.0, 'seed': 42},
            metrics=['f1_macro'],
          )
          with tempfile.TemporaryDirectory() as d:
            r = Runner(spec, db_path=pathlib.Path(d)/'test.db', dry_run=True)
            s = r.run()
            assert s['n_predictions'] >= 3, s
          print('Dry-run smoke OK')
          "
```
