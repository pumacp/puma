#!/usr/bin/env bash
# Serve the MkDocs site locally with live reload for previewing docs changes.
# Usage: bash scripts/serve_docs.sh [extra mkdocs serve args]
set -euo pipefail
exec mkdocs serve -a 127.0.0.1:8000 "$@"
