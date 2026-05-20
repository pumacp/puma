# Quick Start

This page assumes you have completed [Installation](Installation) and have at
least one model pulled into Ollama. It walks you from a fresh stack to your
first set of metrics in under five minutes.

## Run your first benchmark

```bash
docker compose run --rm puma_runner puma run \
  --scenario triage_jira \
  --model qwen2.5:3b \
  --strategy zero_shot \
  --instances 10
```

What each flag means:

- `--scenario triage_jira` — picks the multi-class issue-triage task on the
  Jira Social Repository dataset.
- `--model qwen2.5:3b` — the Ollama tag of the model under test.
- `--strategy zero_shot` — the prompting strategy (no in-context examples).
- `--instances 10` — how many issues from the dataset to evaluate. Ten is
  enough to verify everything works; production sweeps use 100–500.

The command prints progress, writes raw predictions to SQLite, and emits a
final summary with F1-macro, latency, and CodeCarbon emissions.

## View results

```bash
docker compose run --rm puma_runner puma list-runs
```

This shows every run logged in the local database with its scenario, model,
strategy, key metric, and run ID. Use the run ID with `puma compare` to put
two runs side by side, or pass it to `puma share-results` to submit it to
PUMA Community.

## Launch the dashboard

```bash
docker compose up -d puma_dashboard
```

Then open `http://localhost:8501` in your browser. The dashboard exposes
eight views — overview, accuracy, calibration, efficiency, robustness,
fairness, sustainability, and a Community submissions panel.

## Next steps

- Read [Architecture](Architecture) to understand how PUMA's six layers fit
  together.
- Read [Running Benchmarks](Running-Benchmarks) for the full `puma run` flag
  reference and the strategy catalog.
- Read [Publishing Results](Publishing-Results) once you have a result you'd
  like to share with the community.
