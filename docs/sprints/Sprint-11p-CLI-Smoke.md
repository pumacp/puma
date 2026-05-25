# Sprint 11' — Community CLI Smoke Proof

Smoke verification of the four `puma community` subcommands (`browse`, `pull`,
`verify-hash`, `validate`) implemented in Sprint 11'.2. Performed during
S11'.10.b as part of the Sprint closure.

**Context.** The Sprint 11'.10.a E2E demo attempt surfaced three integration
gaps (D24/D25/D26 in `docs/known_debt.md`) that prevent producing a real
shareable submission from canonical runner output. Pending those gaps being
resolved in a future Sprint, this smoke proof exercises the CLI against the
available placeholder fixture
(`puma-community/notebooks/sample_submission.json`, a zeros-placeholder) to
confirm that the CLI itself is operational and reports clearly.

**Fixture access note.** The placeholder fixture lives in the sibling
`puma-community` repository, outside the `puma_runner` container's `/app`
mount. For this smoke it was copied into the container with
`docker cp puma-community/notebooks/sample_submission.json
puma_runner:/tmp/sample_submission.json`; the commands below reference the
in-container path. This is a harness detail, not part of the CLI under test.

This is **not** a proof of end-to-end correctness — it is a proof that the CLI
is operational and reports clearly on the available (placeholder) input.

## Smoke 1: `puma community validate`

Command:
```
docker exec puma_runner puma community validate /tmp/sample_submission.json
```

Observed output:
```
OK    /tmp/sample_submission.json

1 validated, 1 valid, 0 invalid
```

Exit code: **0**

Interpretation: the placeholder fixture is schema-valid under the canonical
Pydantic validator. `validate` parses it, runs the validator, and reports a
clean result. (Run without `--strict`; the fixture's filename does not match
its all-zeros `submission_id`, so `--strict` would additionally flag the
filename↔id mismatch — expected for a placeholder, not exercised here.)

## Smoke 2: `puma community verify-hash`

Command:
```
docker exec puma_runner puma community verify-hash /tmp/sample_submission.json
```

Observed output:
```
Predictions JSONL not found. Pass --predictions PATH or place
sample_submission.predictions.jsonl next to the submission.
```

Exit code: **2**

Interpretation: the placeholder fixture has no companion predictions JSONL, so
`verify-hash` cannot recompute a hash to compare. It correctly detects the
missing input and exits 2 (input error) with an actionable message **before**
attempting any comparison — it does not reach the declared-vs-computed step.
(The fixture's declared `predictions_summary_hash` is an all-zeros placeholder
and `raw_predictions_url` is `null`, so even with a predictions file the local
hash would not match; but that path is not reached here.)

## Smoke 3: `puma community browse --help`

(No remote access exercised; only confirms the command is registered and
`--help` is parseable.)

Output excerpt:
```
 Usage: puma community browse [OPTIONS]

 List submissions in pumacp/puma-community, filtered and sorted newest-first.

 Options:
   --scenario   TEXT     Filter by scenario substring.
   --model      TEXT     Filter by model substring.
   --last-n     INTEGER  Keep the N most recent.
   --since      TEXT     ISO 8601 date, e.g. 2026-05-01.
   --json                Emit JSON instead of a table.
   --anonymous           Skip the stored PAT (60 req/h).
   --help                Show this message and exit.
```

## Smoke 4: `puma community pull --help`

(No remote access exercised; only confirms the command is registered.)

Output excerpt:
```
 Usage: puma community pull [OPTIONS]

 Download submissions (optionally filtered) and consolidate to the chosen format.

 Options:
   --output   PATH     Output directory. [default: data/community/cache]
   --format   TEXT     jsonl | parquet | csv | raw. [default: jsonl]
   --filter   TEXT     e.g. "scenario=triage_jira AND model_tag=qwen2.5:3b".
   --limit    INTEGER  Keep at most N after filtering.
   --anonymous         Skip the stored PAT (60 req/h).
   --help              Show this message and exit.
```

## Conclusion

The four community CLI subcommands are operational and registered under
`puma community`. On the placeholder fixture:

- `validate` reports the submission as schema-valid (exit 0).
- `verify-hash` correctly refuses on missing predictions input (exit 2), with
  a clear, actionable message — rather than producing a misleading result.
- `browse` and `pull` expose their documented option surfaces.

The CLI is fit for purpose once the upstream gaps D24/D25/D26 are resolved and
real submissions can be produced from the canonical runner. The gap is in the
runner → `share-results` integration (see `docs/known_debt.md`), not in the
community CLI itself.
