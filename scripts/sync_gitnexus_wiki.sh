#!/usr/bin/env bash
# PUMA — sync the GitNexus-generated module reference to the GitHub repository wiki.
#
# Usage: bash scripts/sync_gitnexus_wiki.sh
#
# Prerequisites:
#   - docs/architecture/ exists (populated by `gitnexus wiki` and committed here)
#   - You have push access to https://github.com/pumacp/puma.wiki.git
#
# This clones the wiki repo into a temp dir, copies the staged content in,
# commits, and pushes. It does NOT delete existing wiki pages that are not part
# of the staged content. Manual maintainer step — not run by CI.
set -euo pipefail

STAGE_DIR="docs/architecture"
WIKI_REPO="https://github.com/pumacp/puma.wiki.git"
TMP_DIR="$(mktemp -d)"

if [[ ! -d "$STAGE_DIR" ]]; then
  echo "✗ Staging dir $STAGE_DIR does not exist; run 'gitnexus wiki' first."
  exit 1
fi

git clone "$WIKI_REPO" "$TMP_DIR/wiki"
cp -r "$STAGE_DIR"/* "$TMP_DIR/wiki/"
cd "$TMP_DIR/wiki"
git add -A
if git diff --cached --quiet; then
  echo "✓ Wiki already up to date; nothing to push."
  exit 0
fi
git commit -m "docs(architecture): sync from GitNexus wiki ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
git push origin HEAD
echo "✓ Wiki synced: https://github.com/pumacp/puma/wiki"
