#!/usr/bin/env bash
# Prints a human-readable summary of the produced demo package for maintainer review (PAUSE 3).
# No `pipefail`: `json.tool | head` legitimately closes the pipe early (SIGPIPE),
# which is not an error for a display-only helper.
set -eu
DEMO_OUT="${PUMA_DEMO_OUT:-/tmp/puma_publication_demo}"

echo "=== submission.json ==="
python3 -m json.tool "$DEMO_OUT/submission.json" | head -50
echo ""
echo "=== predictions.jsonl (first 3 + last 1 lines) ==="
head -3 "$DEMO_OUT/predictions.jsonl"
echo "…"
tail -1 "$DEMO_OUT/predictions.jsonl"
echo ""
echo "=== integrity ==="
puma community verify-hash "$DEMO_OUT/submission.json" --predictions "$DEMO_OUT/predictions.jsonl"
echo ""
echo "Total predictions: $(wc -l < "$DEMO_OUT/predictions.jsonl")"
echo "submission.json size: $(wc -c < "$DEMO_OUT/submission.json") bytes"
echo "predictions.jsonl size: $(wc -c < "$DEMO_OUT/predictions.jsonl") bytes"
