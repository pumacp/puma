#!/usr/bin/env bash
# PUMA entry point — detects hardware, selects profile, starts services.
# Usage: ./start_puma.sh [--profile auto|cpu-lite|cpu-standard|gpu-entry|gpu-mid|gpu-high]
#                        [--skip-models] [--skip-datasets] [--smoke-only]
#                        [--observability] [--verbose]

set -euo pipefail

PROFILE="auto"
SKIP_MODELS=false
SKIP_DATASETS=false
SMOKE_ONLY=false
OBSERVABILITY=false
VERBOSE=false

# Parse flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile) PROFILE="$2"; shift 2 ;;
        --skip-models) SKIP_MODELS=true; shift ;;
        --skip-datasets) SKIP_DATASETS=true; shift ;;
        --smoke-only) SMOKE_ONLY=true; shift ;;
        --observability) OBSERVABILITY=true; shift ;;
        --verbose) VERBOSE=true; set -x; shift ;;
        *) echo "Unknown flag: $1"; exit 1 ;;
    esac
done

# Load .env if present
if [[ -f .env ]]; then
    set -a; source .env; set +a
fi

LOGDIR="logs"
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/startup_$(date +%Y%m%d_%H%M%S).log"

log() { echo "[PUMA] $*" | tee -a "$LOGFILE"; }
die() { echo "[PUMA ERROR] $*" | tee -a "$LOGFILE"; exit 1; }

log "============================================================"
log " PUMA — Starting up"
log "============================================================"

# ── Step 1: Preflight ────────────────────────────────────────────
log "Step 1/5 — Preflight: hardware detection"

# Run preflight inside the evaluator container (Python 3.11 environment)
docker exec puma_evaluator python -m puma.cli preflight --profile "$PROFILE" 2>&1 | tee -a "$LOGFILE" || {
    log "Preflight failed — see $LOGFILE"
    # If container not yet running, run preflight on host Python if available
    if command -v python3 &>/dev/null; then
        PYTHONPATH="src" python3 -m puma.cli preflight --profile "$PROFILE" 2>&1 | tee -a "$LOGFILE" || true
    fi
}

# Read the selected profile from the written YAML
SELECTED_PROFILE="cpu-standard"
if [[ -f config/runtime_profile.yaml ]]; then
    SELECTED_PROFILE=$(python3 -c "import yaml,sys; d=yaml.safe_load(open('config/runtime_profile.yaml')); print(d['profile'])" 2>/dev/null || echo "cpu-standard")
fi
log "Selected profile: $SELECTED_PROFILE"

# ── Step 2: Provisioning ─────────────────────────────────────────
log "Step 2/5 — Provisioning: starting Docker services"

GPU_COMPOSE_ARGS=""
if [[ "$SELECTED_PROFILE" == gpu-* ]]; then
    GPU_COMPOSE_ARGS="--gpus all"
    log "GPU profile detected — enabling GPU passthrough"
fi

# Ensure Ollama service is up
if ! docker ps --format '{{.Names}}' | grep -q '^puma_ollama$'; then
    log "Starting puma_ollama..."
    docker compose up -d ollama 2>&1 | tee -a "$LOGFILE"
fi

# Wait for Ollama to be healthy
log "Waiting for Ollama to be healthy..."
for i in $(seq 1 20); do
    if docker exec puma_ollama ollama list &>/dev/null; then
        log "Ollama is ready"
        break
    fi
    sleep 3
    [[ $i -eq 20 ]] && die "Ollama did not become healthy after 60 seconds"
done

# ── Step 3: Models ───────────────────────────────────────────────
if [[ "$SKIP_MODELS" == false ]]; then
    log "Step 3/5 — Pulling models for profile: $SELECTED_PROFILE"
    MODELS=$(python3 -c "
import yaml
d = yaml.safe_load(open('config/runtime_profile.yaml'))
print(' '.join(d.get('models', [])))
" 2>/dev/null || echo "qwen2.5:3b")

    for MODEL in $MODELS; do
        log "Pulling $MODEL..."
        docker exec puma_ollama ollama pull "$MODEL" 2>&1 | tee -a "$LOGFILE" || log "WARNING: Failed to pull $MODEL"
    done
else
    log "Step 3/5 — Skipping model downloads (--skip-models)"
fi

# ── Step 4: Datasets ─────────────────────────────────────────────
if [[ "$SKIP_DATASETS" == false ]]; then
    log "Step 4/5 — Verifying datasets"
    docker exec puma_evaluator python -c "
import sys; sys.path.insert(0,'src')
from pathlib import Path
ok = True
for f in ['data/jira_balanced_200.csv', 'data/tawos_clean.csv']:
    if Path(f).exists():
        print(f'  OK: {f}')
    else:
        print(f'  MISSING: {f}')
        ok = False
sys.exit(0 if ok else 1)
" 2>&1 | tee -a "$LOGFILE" || log "WARNING: Some dataset files are missing"
else
    log "Step 4/5 — Skipping dataset verification (--skip-datasets)"
fi

# ── Step 5: Smoke test or full start ─────────────────────────────
if [[ "$SMOKE_ONLY" == true ]]; then
    log "Step 5/5 — Smoke test"
    docker exec puma_evaluator python -c "
import sys; sys.path.insert(0,'src')
from puma.preflight import detect_capabilities
caps = detect_capabilities()
print(f'  RAM: {caps.ram_total_gb:.1f} GB')
print(f'  GPU: {caps.gpu_name or \"none\"}')
print('  Smoke test PASSED')
" 2>&1 | tee -a "$LOGFILE" && log "Smoke test complete" || die "Smoke test failed"
else
    log "Step 5/5 — Starting remaining services"
    docker compose up -d 2>&1 | tee -a "$LOGFILE"
fi

# ── Summary ──────────────────────────────────────────────────────
log ""
log "============================================================"
log " PUMA is ready"
log "  Profile   : $SELECTED_PROFILE"
log "  Dashboard : http://localhost:8501 (when Phase 6 deployed)"
log "  Next steps:"
log "    puma run specs/runs/smoke_triage.yaml"
log "    puma dashboard"
log "    puma report <run_id>"
log "  Log: $LOGFILE"
log "============================================================"
