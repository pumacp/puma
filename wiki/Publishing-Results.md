# Publishing Your Results

PUMA can publish run results to [PUMA Community](https://github.com/pumacp/puma-community),
a public federation hub where users of the PUMA benchmarking tool share their
verified results. Publishing is opt-in, anonymous by default, and entirely
PR-based — no central server, no account except GitHub itself.

## Why publish

- **Reproducibility for the field.** Local LLM benchmarks are intrinsically
  hardware-dependent. The same model on different machines yields slightly
  different latency, energy, and occasionally different outputs. Sharing
  results across hardware diversifies the empirical record.
- **Cross-team comparisons.** Once your run is in the public archive, anyone
  comparing the same model and scenario can cite your numbers, replicate them,
  and contrast them with their own.
- **Community knowledge base.** Each submission becomes part of a queryable
  dataset of verified PUMA runs. Researchers and practitioners can identify
  which models genuinely shine, on which scenarios, under which budgets.

## What gets published

A submission contains:

- The scenario name and instance count.
- The model tag and prompting strategy.
- The hardware profile (`cpu-lite`, `gpu-entry`, etc.) — **not** your specific
  CPU model or hostname.
- All metric families: accuracy, calibration, efficiency, stability,
  robustness, fairness, sustainability.
- The PUMA version that produced the run.
- A self-chosen submitter alias (a free-form string, can be a pseudonym).
- A SHA-256 hash over the predictions summary for cryptographic integrity.

No raw prompts, no raw model responses, no environment variables, no file
system paths, and no PII. The local validator scans the submission for
patterns that look like email addresses, IPs, GitHub tokens, and absolute
paths before it ever leaves your machine.

## How to publish

1. **Create a GitHub Personal Access Token (PAT).** Use the fine-grained PAT
   creator at `https://github.com/settings/tokens?type=beta`. Repository
   access: `pumacp/puma-community`. Permissions: `Pull requests: Read and write`,
   `Contents: Read and write`, `Metadata: Read`.
2. **Authenticate locally:**
   ```bash
   docker compose run --rm puma_runner puma auth login
   ```
   Paste the PAT when prompted. It is stored under `~/.puma/credentials.toml`
   with `0600` permissions.
3. **Dry-run first:**
   ```bash
   docker compose run --rm puma_runner puma share-results \
     --dry-run --run-id <your_run_id>
   ```
   This builds the submission JSON locally without publishing. Inspect it
   under `data/community/submissions/`.
4. **Publish:**
   ```bash
   docker compose run --rm puma_runner puma share-results --run-id <your_run_id>
   ```

## What happens next

The PR is automatically validated against `schema/submission.v1.json`.
Integrity is verified by recomputing the SHA-256 hash. If both checks pass,
the auto-merge workflow merges your PR within a few minutes and the
PUMA Community badges refresh to reflect the new submission.

## Anonymity

See the [Anonymity and Privacy](https://github.com/pumacp/puma-community/wiki/Anonymity-And-Privacy)
page on PUMA Community for the full list of what is and is not transmitted,
plus the procedure for withdrawing a submission after publication.
