#!/usr/bin/env bash
# start_puma.sh — provision and start PUMA on a clean machine.
# Requirements: docker, docker compose (v2), internet access.
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
START_TIME=$(date +%s)

while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)       PROFILE="$2"; shift 2 ;;
        --skip-models)   SKIP_MODELS=true; shift ;;
        --skip-datasets) SKIP_DATASETS=true; shift ;;
        --smoke-only)    SMOKE_ONLY=true; shift ;;
        --observability) OBSERVABILITY=true; shift ;;
        --verbose)       VERBOSE=true; set -x; shift ;;
        *) echo "Unknown flag: $1"; exit 1 ;;
    esac
done

[[ -f .env ]] && { set -a; source .env; set +a; }

LOGDIR="logs"
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/startup_$(date +%Y%m%d_%H%M%S).log"

log()  { echo "[PUMA] $*" | tee -a "$LOGFILE"; }
die()  { echo "[PUMA ERROR] $*" | tee -a "$LOGFILE"; exit 1; }
warn() { echo "[PUMA WARN] $*" | tee -a "$LOGFILE"; }

log "============================================================"
log " PUMA v2.0.0 — Local LLM Benchmark"
log "============================================================"

# ── Step 0: Detect GPU on host and export for containers ─────────

export PUMA_GPU_NAME=""
export PUMA_GPU_VRAM_GB=""
export PUMA_GPU_BACKEND="none"

if command -v nvidia-smi &>/dev/null; then
    _GPU_LINE=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1 || true)
    if [[ -n "$_GPU_LINE" ]]; then
        PUMA_GPU_NAME=$(echo "$_GPU_LINE" | cut -d',' -f1 | xargs)
        _VRAM_MIB=$(echo "$_GPU_LINE" | cut -d',' -f2 | tr -dc '0-9.')
        PUMA_GPU_VRAM_GB=$(python3 -c "print(round($_VRAM_MIB/1024, 1))" 2>/dev/null || echo "")
        PUMA_GPU_BACKEND="nvidia"
    fi
fi

# Persist GPU vars to .env so every subsequent `docker compose run` picks them up
{
    grep -v "^PUMA_GPU_" .env 2>/dev/null || true
    echo "PUMA_GPU_NAME=$PUMA_GPU_NAME"
    echo "PUMA_GPU_VRAM_GB=$PUMA_GPU_VRAM_GB"
    echo "PUMA_GPU_BACKEND=$PUMA_GPU_BACKEND"
} > .env.tmp && mv .env.tmp .env

# ── Step 1: Check Docker ──────────────────────────────────────────

command -v docker &>/dev/null || die "Docker is not installed. See https://docs.docker.com/get-docker/"
docker compose version &>/dev/null || die "Docker Compose v2 is required."
log "Step 1/6 — Docker OK ($(docker --version | head -1))"
if [[ "$PUMA_GPU_BACKEND" != "none" ]]; then
    log "  GPU detected on host: $PUMA_GPU_NAME (${PUMA_GPU_VRAM_GB} GB VRAM) — will be passed to containers"
else
    log "  No GPU detected on host — CPU-only mode"
fi

# ── Step 2: Build image ───────────────────────────────────────────

log "Step 2/6 — Building puma_runner image..."
docker compose build puma_runner 2>&1 | tee -a "$LOGFILE"

# ── Step 3: Preflight ────────────────────────────────────────────

log "Step 3/6 — Preflight: hardware detection"
docker compose run --rm --no-deps puma_runner \
    puma preflight --profile "$PROFILE" 2>&1 | tee -a "$LOGFILE" || warn "Preflight reported warnings"

SELECTED_PROFILE="cpu-standard"
if [[ -f config/runtime_profile.yaml ]]; then
    SELECTED_PROFILE=$(python3 -c \
        "import yaml; d=yaml.safe_load(open('config/runtime_profile.yaml')); print(d.get('profile','cpu-standard'))" \
        2>/dev/null || echo "cpu-standard")
fi
log "  Selected profile: $SELECTED_PROFILE"

# ── Step 4: Start services ────────────────────────────────────────

log "Step 4/6 — Starting services (Ollama + dashboard)..."
docker compose up -d puma_ollama puma_dashboard 2>&1 | tee -a "$LOGFILE"

log "  Waiting for Ollama to be ready..."
for i in $(seq 1 30); do
    if docker compose exec puma_ollama ollama list &>/dev/null 2>&1; then
        log "  Ollama ready."
        break
    fi
    sleep 2
    [[ $i -eq 30 ]] && warn "Ollama did not respond after 60s — continuing."
done

# ── Step 5: Models ───────────────────────────────────────────────

if [[ "$SKIP_MODELS" == false ]]; then
    log "Step 5/6 — Pulling models for profile: $SELECTED_PROFILE"

    # Read models from catalog for selected profile
    MODELS=$(python3 -c "
import yaml, sys
try:
    d = yaml.safe_load(open('config/models_catalog.yaml'))
    models = [m['ollama_tag'] for m in d['models']
              if '$SELECTED_PROFILE' in m.get('profiles_compatible', [])]
    # Limit to 2 smallest models for cpu profiles
    print(' '.join(models[:2]))
except Exception as e:
    print('qwen2.5:3b', file=sys.stderr)
    print('qwen2.5:3b')
" 2>/dev/null || echo "qwen2.5:3b")

    for MODEL in $MODELS; do
        log "  Pulling $MODEL..."
        docker compose exec puma_ollama ollama pull "$MODEL" 2>&1 | tee -a "$LOGFILE" \
            || warn "Failed to pull $MODEL — skipping."
    done
else
    log "Step 5/6 — Skipping model downloads (--skip-models)"
fi

# ── Step 6: Datasets + DB schema ─────────────────────────────────

if [[ "$SKIP_DATASETS" == false ]]; then
    log "Step 6/6 — Verifying / downloading datasets..."
    if ! docker compose run --rm --no-deps puma_runner puma datasets verify \
            2>&1 | tee -a "$LOGFILE"; then
        log "  Dataset missing — downloading..."
        docker compose run --rm --no-deps puma_runner \
            python scripts/download_datasets.py 2>&1 | tee -a "$LOGFILE" \
            || warn "Dataset download failed — manual intervention may be needed."
    fi
else
    log "Step 6/6 — Skipping dataset verification (--skip-datasets)"
fi

log "  Applying database schema..."
docker compose run --rm --no-deps puma_runner puma db migrate 2>&1 | tee -a "$LOGFILE"

# ── Optional smoke-only run ───────────────────────────────────────

if [[ "$SMOKE_ONLY" == true ]]; then
    log "Running dry-run smoke test..."
    docker compose run --rm --no-deps puma_runner \
        puma run specs/runs/smoke_triage.yaml --dry-run 2>&1 | tee -a "$LOGFILE" \
        && log "Smoke test PASSED" || die "Smoke test FAILED"
fi

# ── Optional observability overlay ────────────────────────────────

if [[ "$OBSERVABILITY" == true ]]; then
    if [[ -f docker/docker-compose.observability.yml ]]; then
        log "Starting observability services (Grafana)..."
        docker compose -f docker-compose.yml \
            -f docker/docker-compose.observability.yml up -d 2>&1 | tee -a "$LOGFILE"
    else
        warn "Observability overlay not found at docker/docker-compose.observability.yml"
    fi
fi

# ── Summary ──────────────────────────────────────────────────────

END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))

log ""
log "============================================================"
log " PUMA is ready (${ELAPSED}s elapsed)"
log "  Profile   : $SELECTED_PROFILE"
log "  Dashboard : http://localhost:8501"
log "  Ollama    : http://localhost:11434"
log ""
log "  Quick start:"
log "    docker compose run --rm puma_runner puma run specs/runs/smoke_triage.yaml"
log "    docker compose run --rm puma_runner puma report <run_id>"
log "    docker compose run --rm puma_runner puma compare <id1> <id2>"
log "  Log: $LOGFILE"
log "============================================================"
