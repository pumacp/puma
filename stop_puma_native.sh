#!/usr/bin/env bash
# stop_puma_native.sh — stop the native macOS Ollama server started by
# `./start_puma.sh --native`. Added in v2.6.0.
#
# On Linux this is a no-op (exits 0 with a brief note).

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "[INFO] Not on macOS; nothing to do."
    exit 0
fi

if pgrep -f "ollama serve" >/dev/null 2>&1; then
    echo "[INFO] Stopping native Ollama server..."
    pkill -f "ollama serve" || true
    sleep 2
    if pgrep -f "ollama serve" >/dev/null 2>&1; then
        echo "[WARN] Ollama still running; sending SIGKILL."
        pkill -9 -f "ollama serve" || true
    fi
    echo "[OK] Native Ollama stopped."
else
    echo "[INFO] No native Ollama process found; nothing to stop."
fi

echo ""
echo "To deactivate the Python venv started by start_puma.sh --native:"
echo "    deactivate"
