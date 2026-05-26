# Publication workflow

## Overview

Publication bundles a reproducible PUMA benchmark result into a **submission
package** suitable for sharing with the PUMA Community public registry. The
package pairs a `submission.json` (run metadata, hardware profile, metrics,
sustainability, and an integrity hash) with a `predictions.jsonl` (the
per-sample predictions the hash is computed over), so any reviewer can
independently re-verify the result.

## Prerequisites

- PUMA installed (`pip install -e .`).
- Ollama running with the chosen model pulled (e.g. `ollama pull qwen2.5:3b`).
- CodeCarbon available (ships with PUMA) for the sustainability section.
- A run-spec — the demo uses `specs/runs/demo_publication.yaml` (a small,
  demo-only triage subset); the canonical baseline is
  `specs/runs/baseline_triage.yaml`.

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

## Channels

Once a submission is accepted into the PUMA Community public repository
(`github.com/pumacp/puma-community`), GitHub Actions workflows there mirror it to
external archives and announce it. PUMA does not call these services itself — it
only surfaces them so you can see what a published submission feeds into.

| Channel | Kind | Workflow (puma-community) | Local env var |
|---|---|---|---|
| Hugging Face Datasets | mirror | `mirror-huggingface.yml` | `HF_TOKEN` |
| Zenodo | mirror | `mirror-zenodo.yml` | `ZENODO_TOKEN` |
| Kaggle | mirror | `mirror-kaggle.yml` | `KAGGLE_KEY` |
| Discord | notification | `notify-discord.yml` | `DISCORD_WEBHOOK` |
| Telegram | notification | `notify-telegram.yml` | `TELEGRAM_BOT_TOKEN` |

The workflows and their secrets live in the puma-community repository; see its
[For-Maintainers wiki page](https://github.com/pumacp/puma-community/wiki/For-Maintainers)
for the maintainer-side configuration. The env vars above are read locally only
to report configuration state (next section) — PUMA never transmits them.

## Status quick-check

Two read-only commands summarise the local publication surface:

```bash
puma community status     # auth + last local submission + configured channel count
puma community channels   # the channel table above, with local-config marks
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

## Configuring channels locally

To drive a channel from your own environment (for example, to test a mirror
before it runs in CI), export the corresponding variable:

```bash
export HF_TOKEN=...            # Hugging Face mirror
export ZENODO_TOKEN=...        # Zenodo mirror
export KAGGLE_KEY=...          # Kaggle mirror
export DISCORD_WEBHOOK=...     # Discord notification
export TELEGRAM_BOT_TOKEN=...  # Telegram notification
```

!!! warning "Secrets live in the environment only"
    Set these as environment variables (or repository secrets in
    puma-community). **Never commit a token to the repository.** PUMA reads the
    variables solely to report configuration state in `puma community status` /
    `channels`; it does not store or transmit them.

## Known caveats

- **D29** — for *estimation* runs the `predictions_summary_hash` can differ
  run-to-run even on identical code (the model emits the same numeric value in
  different string forms). Triage hashes are stable; the metric (MAE) stays
  bit-exact within a session.
- **D31** — the estimation MAE baseline drifts across Ollama restarts
  (environment, not code). Treat the MAE reference as runtime-dependent.
- **F2** — cold-vs-warm reproducibility: bit-exact in a warm runtime; small
  drift (≤0.006 on F1) cold-vs-warm.
