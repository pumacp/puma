# CLI reference

The `puma` command-line interface is the single entry point to the platform.
This page is the source of truth for the current command surface; every command
here is verifiable with `puma <command> --help`.

## Global options

These apply to every command (place them before the subcommand):

| Option | Description |
|---|---|
| `--no-banner`, `-B` | Suppress the startup banner. |
| `--theme <name>` | Terminal color theme: `amber` (default) or `green`. Overrides `PUMA_THEME`. |
| `--quiet`, `-q` | Suppress the progress display. |
| `--verbose`, `-v` | Show the full traceback on errors. |
| `--no-summary` | Suppress the post-run summary table. |
| `--help` | Show help for any command or subcommand. |

```bash
puma --help            # top-level help
puma run --help        # help for a specific command
puma models list --help
```

## Benchmarking

### `puma run`
Execute a benchmark run-spec.

```bash
puma run specs/runs/baseline_triage.yaml
```
Runs the spec against a local Ollama model, evaluates the task metric, tracks
sustainability via CodeCarbon, and stores results in the database. Prints
`Run complete: <run_id>` on success.

### `puma compare`
Compare metrics across two or more runs.

```bash
puma compare <run_id_a> <run_id_b>
```

### `puma validate-baseline`
Validate a canonical baseline metric against its reference value (used to detect
drift; e.g. F1 triage and MAE estimation).

### `puma report`
Generate a Markdown (or PDF) run report from a stored run.

### `puma list-runs`
List runs registered in the database with their headline metrics
(`run_id`, scenario, model, strategy, N, F1/MAE, parse-failure rate, duration).

## Discovery & diagnostics

### `puma doctor`
Run read-only environment health checks (Python, CodeCarbon, Ollama reachability,
models present, hardware profile, database, baseline specs). Reports `OK`/`WARN`/`FAIL`
per check and exits `1` if any check fails. Makes no changes.

### `puma env`
Print the resolved PUMA environment: version, platform, active theme, detected
hardware profile, and key paths.

### `puma preflight`
Detect hardware, select the execution profile, and report readiness. Optionally
writes `config/runtime_profile.yaml`.

### `puma datasets`
Verify dataset integrity and show statistics.

### `puma prepare-datasets`
Prepare the canonical datasets (`jira_balanced_200`, `tawos`, `prioritization`).

## Models

`puma models` is a read-only sub-group that inspects the models available to PUMA
via the local Ollama daemon. It never pulls or modifies models.

### `puma models list`
List models pulled locally in Ollama (via `/api/tags`).

```bash
puma models list
```

### `puma models show <name>`
Show details for one locally-pulled model (via `/api/show`).

```bash
puma models show qwen2.5:3b
```

### `puma models recommended`
Show the curated PUMA catalog with current local availability — useful to see
which recommended models you still need to `ollama pull`.

## Analysis

### `puma wilcoxon`
Wilcoxon signed-rank pairwise comparison of two runs (non-parametric statistical
validation). Reports the W statistic, two-sided p-value, significance marker, and
effect size.

```bash
puma wilcoxon <run_id_a> <run_id_b> --metric f1_macro --alpha 0.05
```

### `puma bias-analysis`
Bias analysis from perturbed runs already in the database (disparity, flip rates,
directional comparison).

### `puma generate-plots`
Generate consolidated plots from runs in the database (`png`/`pdf`/`svg`).

## Database & cache

### `puma db`
Manage the PUMA database schema (Alembic-driven migrations).

### `puma cache`
Manage the inference cache.

### `puma dashboard`
Launch the Streamlit dashboard for interactive visualization of runs and metrics.

```bash
puma dashboard   # then open http://localhost:8501
```

## Community & sharing

### `puma auth`
Manage PUMA Community credentials (GitHub, Hugging Face, Zenodo, …). Tokens are
stored with mode `0600`; values are always masked in output.

| Subcommand | Description |
|---|---|
| `puma auth login <service>` | Prompt for a token and store it securely. |
| `puma auth status` | Show which services have a credential configured (masked). |
| `puma auth logout <service>` | Remove the stored token (with confirmation). |

### `puma share-results`
Share a PUMA run with the PUMA Community — either a local dry-run package or a
real pull request against `pumacp/puma-community`.

```bash
puma share-results --dry-run --run-id <run_id> --yes   # local, no network
puma share-results --run-id <run_id>                   # open a PR (needs auth)
```

### `puma community`
Browse, pull, verify, and validate PUMA Community submissions, and inspect the
local publication surface.

| Subcommand | Description |
|---|---|
| `puma community browse` | List submissions in `pumacp/puma-community`, newest-first. |
| `puma community pull` | Download submissions and consolidate to a chosen format. |
| `puma community validate <file>` | Validate submission JSON files against the schema. |
| `puma community verify-hash <submission> --predictions <jsonl>` | Recompute the predictions hash locally and compare to the declared value. |
| `puma community status` | Show local status (auth, last submission, configured channels). |
| `puma community channels` | List the distribution channels (mirrors + notifiers) and their local config. |

## Exit codes

Commands follow a consistent convention: `0` on success, `1` on an operational
failure (unreachable service, no matching data), and `2` on a usage or
validation error. `puma doctor` exits `1` if any health check fails;
`puma community verify-hash` exits `1` on a hash mismatch and `2` on a read error.
