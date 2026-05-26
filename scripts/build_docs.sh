#!/usr/bin/env bash
set -euo pipefail
mkdocs build --strict --clean --site-dir site/
echo "✓ Docs build successful (output: site/)"
