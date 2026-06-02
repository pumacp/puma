# Publication workflow

## Overview

Publication bundles a reproducible PUMA benchmark result into a **submission
package** suitable for sharing with the PUMA Community public registry. The
package pairs a `submission.json` (run metadata, hardware profile, metrics,
sustainability, and an integrity hash) with a `predictions.jsonl` (the
per-sample predictions the hash is computed over), so any reviewer can
independently re-verify the result.

## Prerequisites

PUMA runs primarily in **Docker containers** (`puma_runner`, `puma_ollama`)
defined in the project's `docker-compose.yml`. The containers ship with all
required Python dependencies, the Ollama runtime, and the pre-pulled model
weights for the supported benchmark configurations. **If you run PUMA via the
standard Docker workflow you do not need to install anything on your host** — a
container shell already has `puma`, Ollama, and CodeCarbon available:

```bash
docker compose up -d                         # start puma_runner + puma_ollama
docker compose exec puma_runner puma doctor  # verify the environment
```

The only input you choose is a run-spec — the demo uses
`specs/runs/demo_publication.yaml` (a small, demo-only triage subset); the
canonical baseline is `specs/runs/baseline_triage.yaml`.

### Local installation (advanced)

To run PUMA outside Docker, install it from source and run Ollama yourself:

```bash
pip install -e .
ollama pull qwen2.5:3b
```

This is the secondary path; the Docker workflow above is the supported default.

## Run the demo

```bash
bash scripts/publication_demo.sh
```

This runs `puma doctor`, executes the spec, builds the submission with
`puma share-results --dry-run` (no network), and verifies it locally. Override
`PUMA_DEMO_OUT` (output dir) or `PUMA_DEMO_SPEC` (run-spec) as needed.

## Output package contents

| File | Contents |
|---|---|
| `submission.json` | schema v1 submission: `submitter`, `puma_version`, `run_metadata`, `hardware_profile`, `metrics`, `sustainability`, `integrity` (incl. `predictions_summary_hash`). |
| `predictions.jsonl` | one JSON object per line — the canonical D27 columns (`instance_id`, `predicted_label`, `predicted_value`, `prompt_hash`), in `instance_id` order. The integrity hash is computed over exactly this file. |

## Local verification

```bash
puma community verify-hash submission.json --predictions predictions.jsonl
```

- **Passes (exit 0)** when the hash recomputed from `predictions.jsonl` matches
  the `integrity.predictions_summary_hash` declared in `submission.json`.
- **Fails (exit 1)** on a hash mismatch (the predictions file does not match the
  declared result).
- **Errors (exit 2)** when the submission is unreadable or has no declared hash.

## Submitting to the Community

!!! note "Coming with the public registry (S12.13)"
    Manual submission instructions will be added once the PUMA Community public
    registry is live. The local `verify-hash` result is canonical for now. Note
    that **D23** (Verifier hash 2-field alignment + `sha256:` prefix) is deferred
    to the post-v4.0.0 schema-decision sprint, so the local `verify-hash` output
    may not match the live Verifier byte-for-byte until D23 is resolved; `--remote`
    treats a local match as authoritative and warns when the Verifier disagrees.

## Status quick-check

Two read-only commands summarise the local publication surface:

```bash
puma community status     # auth + last local submission + configured channel count
puma community channels   # the distribution channels, with local-config marks
```

Example `puma community status` (no credentials, nothing configured):

```text
╭──────────── PUMA Community status ────────────╮
│  Field            Value                        │
│  Authenticated    ✗ not logged in (run `puma   │
│                   auth login`)                 │
│  Last submission  —                            │
│  Channels         0/5 channels configured      │
╰────────────────────────────────────────────────╯
```

`puma community channels` renders each channel with a `Configured?` column that
shows `✓` when the channel's env var is present locally and `—` otherwise. Both
commands exit `0`, make no network calls, and honour `--theme`.

> The `Authenticated` row reflects whether a GitHub token is present in the local
> credential store (`puma auth login github`); it does **not** resolve your GitHub
> username, which would require a network call.

## Known caveats

- **D29** — for *estimation* runs the `predictions_summary_hash` can differ
  run-to-run even on identical code (the model emits the same numeric value in
  different string forms). Triage hashes are stable; the metric (MAE) stays
  bit-exact within a session.
- **D31** — the estimation MAE baseline drifts across Ollama restarts
  (environment, not code). Treat the MAE reference as runtime-dependent.
- **F2** — cold-vs-warm reproducibility: bit-exact in a warm runtime; small
  drift (≤0.006 on F1) cold-vs-warm.
