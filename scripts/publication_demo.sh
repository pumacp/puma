#!/usr/bin/env bash
set -euo pipefail

# PUMA live-publication demo (S12.12 / E5)
# Exercises the end-to-end flow: doctor -> run -> share-results --dry-run ->
# verify-hash, producing a submission package for maintainer review (PAUSE 3)
# BEFORE any external Community publication. Strictly local and side-effect free:
# share-results runs with --dry-run (no network), verify-hash is local-only.
#
# Composes existing subcommands only; it modifies none of them.
#
# Env overrides:
#   PUMA_DEMO_OUT   output dir for the package        (default: /tmp/puma_publication_demo)
#   PUMA_DEMO_SPEC  run-spec to benchmark             (default: specs/runs/demo_publication.yaml)
#                   substitute specs/runs/baseline_triage.yaml for the full canonical baseline.

DEMO_OUT="${PUMA_DEMO_OUT:-/tmp/puma_publication_demo}"
SPEC="${PUMA_DEMO_SPEC:-specs/runs/demo_publication.yaml}"

mkdir -p "$DEMO_OUT"
# Start clean so the submission/predictions globs below are unambiguous.
rm -f "$DEMO_OUT"/*.json "$DEMO_OUT"/*.jsonl

echo "[1/4] puma doctor"
puma doctor

echo "[2/4] puma run $SPEC"
puma --quiet run "$SPEC" | tee "$DEMO_OUT/run.out"
RUN_ID="$(grep 'Run complete:' "$DEMO_OUT/run.out" | tail -1 | sed 's/.*Run complete:[[:space:]]*//' | tr -d '[:space:]')"
if [[ -z "$RUN_ID" ]]; then
  echo "ERROR: could not capture run_id from 'puma run' output" >&2
  exit 1
fi
echo "    run_id=$RUN_ID"

echo "[3/4] puma share-results --dry-run --run-id $RUN_ID --yes  (-> $DEMO_OUT)"
# share-results --dry-run writes <submission_id>.json + <submission_id>.predictions.jsonl
# into PUMA_DRY_RUN_DIR (no network). Normalize the names for review/verification.
PUMA_DRY_RUN_DIR="$DEMO_OUT" PUMA_DRY_RUN_OVERWRITE=1 \
  puma share-results --dry-run --run-id "$RUN_ID" --yes
SUB="$(ls -t "$DEMO_OUT"/*.json | head -1)"
PREDS="${SUB%.json}.predictions.jsonl"
mv "$SUB" "$DEMO_OUT/submission.json"
mv "$PREDS" "$DEMO_OUT/predictions.jsonl"

echo "[4/4] puma community verify-hash $DEMO_OUT/submission.json"
puma community verify-hash "$DEMO_OUT/submission.json" \
  --predictions "$DEMO_OUT/predictions.jsonl"

echo ""
echo "✓ Demo complete. Package at: $DEMO_OUT"
echo "  - submission.json"
echo "  - predictions.jsonl"
echo ""
echo "PAUSE 3: review the package BEFORE publishing externally."
