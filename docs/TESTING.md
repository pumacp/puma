# Testing — structure, coverage, and execution

This document describes PUMA's test organisation and records the
coverage breakdown by module group as of v2.5.0. It exists so that
contributors can see *where* tests are dense and *where* gaps are
acceptable, rather than guessing from a single global number.

## Test layout

| Directory | Purpose | Typical fixtures |
|---|---|---|
| `tests/unit/` | Pure-Python unit tests; no Ollama, no Docker volumes. | Module-local YAML, in-memory SQLite |
| `tests/integration/` | Cross-module integration. Sub-marked `@pytest.mark.ollama` when a live Ollama server is required. | `puma.db` fixture, real Ollama for marked tests |
| `tests/cli/` | One file per `puma <command>`; covers `--help` exposure, happy path, error paths. | Typer `CliRunner`, `monkeypatch` of `_run_baseline_for_validation` and similar helpers |
| `tests/smoke/` | End-to-end smoke runs gated by long-running marks. | Real Ollama, small N, abbreviated specs |

## Markers

| Marker | Meaning | Default behaviour |
|---|---|---|
| `@pytest.mark.unit` | Pure-Python; no external dependencies. | Always selected |
| `@pytest.mark.integration` | Cross-module; may touch the filesystem. | Always selected |
| `@pytest.mark.ollama` | Requires a live Ollama server with at least one pulled model. | **Deselected by default** (`-m "not ollama"` in CI's lint-and-test job). Run by the separate `integration-tests-ollama` CI job on push to `main`/`develop` (see `.github/workflows/lint-and-test.yml`, added in v2.5.0 — I8). |

To run every test locally including Ollama-marked:

```bash
docker compose up -d puma_ollama puma_runner
docker exec puma_runner pytest tests/ -v
```

To run only the deselect-by-default suite (the same set CI's
lint-and-test job runs):

```bash
docker exec puma_runner pytest tests/ -m "not ollama" --cov=puma --cov-report=term-missing
```

## Coverage by module group — v2.5.0

Measured with `pytest --cov=puma -m "not ollama"` on commit
`d5996f1` (Sprint 8 head). 354 tests passing, 7 deselected.

Aggregate global coverage: **61 %** (3 159 statements, 1 241 missing).

| Module group | Statements | Missing | Coverage |
|---|---:|---:|---:|
| `puma.perturbations.*` | 76 | 0 | **100 %** |
| `puma.datasets.*` | 140 | 16 | 89 % |
| `puma.storage.*` | 192 | 39 | 80 % |
| `puma.preflight.*` | 302 | 70 | 77 % |
| `puma.metrics.*` | 242 | 58 | 76 % |
| `puma.runtime.*` | 164 | 48 | 71 % |
| `puma.orchestrator.*` | 346 | 125 | 64 % |
| `puma.cli` (single module) | 471 | 189 | 60 % |
| `puma.scenarios.*` | 280 | 127 | 55 % |
| `puma.sustainability.*` | 51 | 32 | 37 % |
| `puma.dashboard.*` | 683 | 431 | 37 % |
| `puma.reporting.*` | 87 | 87 | **0 %** |

## Modules with 100 % coverage

- All `__init__.py` package files (trivially covered by imports).
- `puma.perturbations.*` (`text.py`, `gender_swap_prefix.py`,
  `register_shift.py`) — fully covered. Each perturbation is a
  pure function with deterministic SHA-256 indexing and is exercised
  by both unit tests and the bias-evaluation sweep.
- `puma.preflight.catalog` and `puma.preflight.profile` — the catalog
  loader and the profile-selection logic are central to dispatch and
  are exhaustively tested in `tests/unit/test_catalog_metadata.py`
  and `tests/unit/test_preflight_profile.py`.
- `puma.orchestrator.runspec` — every RunSpec YAML field is covered
  by `tests/unit/test_runspec.py`.
- `puma.storage.models` — SQLAlchemy ORM definitions are covered by
  every test that opens the database.
- `puma.scenarios._reasoning`, `puma.scenarios.base` — the reasoning
  parser shim and the abstract scenario base class.

## Modules with < 40 % coverage — and why

| Module | Coverage | Reason |
|---|---:|---|
| `puma.reporting.report` | 0 % | Markdown/PDF report generation. Exercised manually during release prep; output is reviewed by eye. Adding unit tests is on the backlog but low priority — failures here are visual and immediately obvious. |
| `puma.dashboard.components` | 26 % | Streamlit widget wrappers. Streamlit's runtime is not amenable to fine-grained unit testing; smoke tests in `tests/unit/test_dashboard_smoke.py` cover the rendering path end-to-end via `streamlit.testing.AppTest`. |
| `puma.dashboard.views.*` | 9–21 % | Same rationale as `components`. Each view is a `render()` function that pulls filtered data from session state and renders Plotly/Streamlit primitives. Smoke tests validate they import and render without crashing on representative data; deeper coverage would require a Streamlit harness we have chosen not to build. |
| `puma.orchestrator.compare` | 0 % | Inter-run comparison helper. Exercised via `puma compare` in manual workflows; CLI happy-path coverage is in `tests/cli/`. The Python function `compare_runs` is currently called only through the CLI shim. |
| `puma.preflight.report` | 34 % | Rich-formatted CLI report builder. Output is verified by reading the `puma preflight` output during dev. The branches that go untested are detector-specific formatting paths (NVIDIA vs CPU-only vs AMD) — hard to exercise without varied hardware. |
| `puma.sustainability.codecarbon_wrapper` | 37 % | Wraps the CodeCarbon `EmissionsTracker`. The Sprint-2 D15 fix is covered by tests/unit/test_emissions_d15.py for the critical paths; remaining missing lines are vendor-init branches (cold-start `cpu_power_meter` etc.) that PUMA does not control. |
| `puma.dashboard.app` (router) | 81 % | Above the 40 % threshold and listed for completeness; uncovered lines are the dark-mode CSS branch and one fallback path used only on first-load with no runs in the DB. |

## Modules in the 40–80 % band

These are the natural focus areas for incremental test additions
without invoking the Streamlit/Plotly testing barrier:

- `puma.scenarios.estimation_tawos` (45 %), `prioritization_jira`
  (64 %), `triage_jira` (53 %) — scenario-level branches and edge
  cases (malformed Ollama responses, retry behaviour) are partially
  covered. v2.5.0 added the canonical estimation baseline; future
  Sprints may add fuzz tests of the parser.
- `puma.orchestrator.runner` (64 %) — covers the happy path; less
  covered: perturbation-cascade error paths and emissions integration.
- `puma.cli` (60 %) — Typer command handlers; happy-path coverage is
  thorough, but option-validation edge cases are partially tested.
- `puma.runtime.client` (61 %), `puma.runtime.cache` (88 %) — Ollama
  client wrapper; some branches require a live Ollama and are
  covered by the `@pytest.mark.ollama` tests.

## Tests excluded by default

| Exclusion mechanism | Count | Reason |
|---|---:|---|
| `-m "not ollama"` in CI's lint-and-test job | 7 | Tests require a live Ollama server. Run instead by the `integration-tests-ollama` CI job (push to main/develop only) introduced in v2.5.0. |

No `slow` marker is currently in use; long-running smoke runs are in
`tests/smoke/` and gated by being in a separate directory rather than
by a pytest marker.

## What the global number means

61 % global coverage is the right floor *for this codebase*, not a
target to chase. The Streamlit dashboard contributes 683 of the 1 241
missing statements (55 % of the gap); excluding the dashboard, the
non-UI code is around **75 % covered** (`(3 159 − 683)`
statements − `(1 241 − 431)` missing = `2 476` statements with
`810` missing = 67 %; further excluding `puma.reporting.report`
at 0 % gives 70 %). Future Sprint budgets are better spent on
methodology (statistical tests, new scenarios, hardware tiers)
than on chasing the Streamlit view percentages, which would
require a Streamlit testing harness investment with limited
defect-detection upside.

If a regression slips through the existing suite, the right response
is to add a *targeted* test for that specific failure mode, not to
generally raise the coverage number.
