# First official PUMA Community submission

On 2026-05-31 the PUMA project recorded its inaugural production submission to
the PUMA Community leaderboard. This page documents that landmark end to end:
the exact identifiers, the path the submission actually took, how to reproduce
it, and the known infrastructure gaps that were deferred to a later sprint.

## What landed

The inaugural submission benchmarks a small local model on the triage task and
establishes the first reproducible data point on the public leaderboard.

| Field | Value |
|-------|-------|
| Model | `qwen2.5:3b` |
| Scenario | `triage_jira` |
| Strategy | `zero_shot` |
| Sample size | 200 |
| Seed | 42 |
| Temperature | 0.0 |
| F1-macro | 0.3898 |
| Accuracy | 0.465 |
| Latency p50 / p95 | 199 ms / 208 ms |
| Hardware profile | gpu-entry (12-core x86_64, 31 GB RAM, NVIDIA RTX 2060 6 GB, Linux) |
| Energy (CodeCarbon) | 0.116 g CO2, 0.000668 kWh, country ESP |
| PUMA version | 3.1.0 |
| Submitter alias | pumacp |
| Submitted at | 2026-05-31T09:16:01.064478Z |

### Submission identifiers

```
run_id:                    baseline_triage_zero_shot_s12_n1__83ec5feaa8df4844__20260531T091417
submission_id:             1d88e49b-5b49-46b9-a8a6-df7bdd5bf80b
predictions_summary_hash:  f60423ca6a6e9b033f0f89ac5a5a127d889a6e2627fc07c480c44bfdf53857ec
merge_sha:                 111cee36af2b9657ee702846727951f32af44462
merged_at:                 2026-05-31T12:43:48Z
```

The `predictions_summary_hash` is a 64-character hex digest computed
deterministically from the per-item predictions. Anyone can recompute it from
the published artefact and confirm it matches, which is what makes the result
verifiable independent of any workflow status.

## The maintainer-driven submission path

This first submission did not flow through the automated `puma share-results`
PR-opening step. During the share phase the CLI generated the in-memory review
panel and then hung, never opening a pull request. To unblock the landmark, a
maintainer took the canonical JSON and JSONL artefacts emitted by
`puma share-results --dry-run` — the same artefacts the automated path would
have pushed — and submitted them by hand: fork, push, and an admin-bypass merge.

We document this honestly as the **maintainer-driven inaugural submission path**.
The data is canonical; only the delivery mechanism was manual. Future
submissions are expected to use `puma share-results` once the CLI hang is
investigated and fixed (tracked as deferred debt below).

### Propagation chain

Once the submission pull request merged, the downstream propagation chain ran:

1. **Submission PR merged** into `puma-community/main` at merge SHA `111cee36`.
2. **Hugging Face dataset mirror** — the submission JSON was mirrored to the
   community submissions dataset (file
   `submissions/1d88e49b-5b49-46b9-a8a6-df7bdd5bf80b.json`).
3. **update-badges workflow** — succeeded, refreshing the repository badges.
4. **Leaderboard Space** — the new row became visible on the public
   leaderboard Space after its cache window elapsed (LRU TTL roughly 5-15 min).

## F1 as the zero_shot floor anchor

The reported F1-macro of 0.3898 is the **floor anchor** for the `zero_shot`
strategy on `triage_jira`. It is the first reproducible zero-shot data point and
gives later strategies a fixed baseline to improve against.

This figure is **not** a regression against the higher contextual-anchoring
baseline. Those are different strategies with different prompting depths:
zero-shot supplies no in-context examples, so a lower score is expected and
correct. Comparing the two head to head would be a category error. The value of
this anchor is precisely that it pins the simplest strategy at a known,
recomputable level.

## Reproducibility

The submission is fully reproducible. The decisive parameters are fixed: seed 42
and temperature 0.0, sample size 200, on PUMA version 3.1.0. Re-running the same
scenario, strategy, and model against the same seed reproduces the predictions,
and recomputing the digest yields the same `predictions_summary_hash`
(`f60423ca...53857ec`). Because the automated integrity verifier workflow failed
on this run, the submission JSON carries an integrity verification status of
*self-attested*; verification nonetheless remains mathematically valid via
deterministic recomputation of the hash from the published predictions.

## Known workflow gaps (deferred to S12.19)

Three submission-side workflows did not run to green on this inaugural landing.
None affects the validity of the data; all are infrastructure issues deferred to
S12.19:

- **validate-submission** — failed at the "Prepare all required actions" step
  on a broken action reference (`actions-ecosystem/action-add-labels@v1.4.0`,
  which was never published); fix by pinning to `@v1.3.0` or a current commit
  SHA. Tracked as D38.
- **Verify submission integrity** — failed with
  `TypeError: Client.__init__() got an unexpected keyword argument 'hf_token'`,
  a `gradio_client` API drift (`hf_token=` should now be `token=`); this is why
  the inaugural submission carries `verification_status="self-attested"` rather
  than `"verified"`. Tracked as D39.
- **notify-discord** — failed for a missing webhook secret; deferred to the
  post-Sprint-12 backlog (not a code defect).

The `puma share-results` CLI hang that forced the manual path is tracked as
D40.

## Cross-repository link map

| Resource | Location |
|----------|----------|
| Submission pull request | https://github.com/pumacp/puma-community/pull/8 |
| Benchmark framework repository | https://github.com/pumacp/puma |
| Hugging Face submissions dataset | https://huggingface.co/datasets/pumaproject/puma-community-submissions |
| Hugging Face leaderboard Space | https://huggingface.co/spaces/pumaproject/puma-leaderboard |
| Mirrored artefact | `submissions/1d88e49b-5b49-46b9-a8a6-df7bdd5bf80b.json` |

See also the [publication workflow](publication_workflow.md) and the
[technical reference](technical_reference.md) for the full submission lifecycle.
