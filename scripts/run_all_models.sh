#!/usr/bin/env bash
# PUMA full benchmark — runs all models defined for the current hardware profile.
# Reads config/runtime_profile.yaml to determine which models and scenarios apply.
# Each model is pulled before evaluation and removed afterwards to minimise VRAM/RAM usage.
#
# Usage (from project root):
#   bash scripts/run_all_models.sh [--dry-run] [--strategies STRATS] [--keep-models]
#
# Options:
#   --dry-run           Build prompts without calling Ollama (validation only)
#   --strategies LIST   Comma-separated strategies to test (default: zero-shot,few-shot-3)
#   --keep-models       Do not remove models from Ollama after each run

set -euo pipefail

COMPOSE="docker compose"
RUNNER="$COMPOSE run --rm puma_runner"
DRY_RUN=false
STRATEGIES="zero-shot,few-shot-3"
KEEP_MODELS=false
RESULTS_DIR="results"
# Spec files must be inside the project tree so the container can read them via .:/app
TMPDIR_SPECS="$RESULTS_DIR/_tmp_specs"
mkdir -p "$TMPDIR_SPECS"

trap 'rm -rf "$TMPDIR_SPECS"' EXIT

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)     DRY_RUN=true; shift ;;
        --strategies)  STRATEGIES="$2"; shift 2 ;;
        --keep-models) KEEP_MODELS=true; shift ;;
        *) echo "Unknown flag: $1"; exit 1 ;;
    esac
done

mkdir -p "$RESULTS_DIR"
LOG="$RESULTS_DIR/benchmark_$(date +%Y%m%d_%H%M%S).log"

log()  { echo "$*" | tee -a "$LOG"; }
warn() { echo "[WARN] $*" | tee -a "$LOG"; }

log "==================================================================="
log " PUMA Benchmark — $(date)"
log "==================================================================="

# ── Read hardware profile ──────────────────────────────────────────────

PROFILE="cpu-standard"
PROFILE_MODELS=""
PROFILE_SCENARIOS=""

if [[ -f config/runtime_profile.yaml ]]; then
    PROFILE=$(python3 -c "
import yaml
d = yaml.safe_load(open('config/runtime_profile.yaml'))
print(d.get('profile', 'cpu-standard'))
" 2>/dev/null || echo "cpu-standard")

    PROFILE_MODELS=$(python3 -c "
import yaml
d = yaml.safe_load(open('config/runtime_profile.yaml'))
print(' '.join(d.get('models', ['qwen2.5:3b'])))
" 2>/dev/null || echo "qwen2.5:3b")

    PROFILE_SCENARIOS=$(python3 -c "
import yaml
d = yaml.safe_load(open('config/runtime_profile.yaml'))
print(' '.join(d.get('scenarios', ['triage_jira'])))
" 2>/dev/null || echo "triage_jira")
else
    PROFILE_MODELS="qwen2.5:3b"
    PROFILE_SCENARIOS="triage_jira"
    warn "config/runtime_profile.yaml not found — using defaults"
fi

# Build YAML list for strategies
STRATEGY_YAML=$(python3 -c "
for s in '$STRATEGIES'.split(','):
    print(f'  - {s.strip()}')
")

# Sample sizes and primary metrics per scenario
declare -A SAMPLE_SIZES=([triage_jira]=50 [estimation_tawos]=30 [prioritization_jira]=30)
declare -A PRIMARY_METRICS=([triage_jira]="f1_macro" [estimation_tawos]="mae" [prioritization_jira]="ndcg_at_10")

log "Profile   : $PROFILE"
log "Models    : $PROFILE_MODELS"
log "Scenarios : $PROFILE_SCENARIOS"
log "Strategies: $STRATEGIES"
[[ "$DRY_RUN" == true ]] && log "Mode      : DRY RUN (no Ollama calls)" || log "Mode      : LIVE"
log "==================================================================="

# ── Helper: generate a run-spec YAML ──────────────────────────────────

generate_spec() {
    local model="$1" scenario="$2" spec_file="$3"
    local model_id sample_size metric

    model_id=$(echo "$model" | tr ':/' '_')
    sample_size=${SAMPLE_SIZES[$scenario]:-20}
    metric=${PRIMARY_METRICS[$scenario]:-accuracy}

    cat > "$spec_file" <<YAML
id: benchmark_${scenario}_${model_id}
description: "Benchmark: ${scenario} x ${model} (profile: ${PROFILE})"
scenario: ${scenario}
sample_size: ${sample_size}
models:
  - ${model}
adaptation:
  strategy:
${STRATEGY_YAML}
  cot: [false]
inference:
  temperature: 0.0
  seed: 42
  logprobs: false
  max_tokens: 256
metrics:
  - ${metric}
  - latency_p95
sustainability:
  codecarbon: false
repeat: 1
YAML
}

# ── Main loop ──────────────────────────────────────────────────────────

TOTAL=0
SUCCESS=0
FAILED=0

for MODEL in $PROFILE_MODELS; do
    MODEL_ID=$(echo "$MODEL" | tr ':/' '_')
    log ""
    log "==================================================================="
    log "MODEL: $MODEL  [$(date)]"
    log "==================================================================="

    # Pull model
    if [[ "$DRY_RUN" == false ]]; then
        log "--- Pulling $MODEL ---"
        $COMPOSE exec puma_ollama ollama pull "$MODEL" 2>&1 | tee -a "$LOG" \
            || { warn "Failed to pull $MODEL — skipping."; continue; }
    fi

    for SCENARIO in $PROFILE_SCENARIOS; do
        SPEC_FILE="$TMPDIR_SPECS/bench_${MODEL_ID}_${SCENARIO}.yaml"
        generate_spec "$MODEL" "$SCENARIO" "$SPEC_FILE"

        log ""
        log "--- Scenario: $SCENARIO ---"
        TOTAL=$((TOTAL + 1))

        DRY_FLAG=""
        [[ "$DRY_RUN" == true ]] && DRY_FLAG="--dry-run"

        RUN_OUTPUT=$($RUNNER puma run "$SPEC_FILE" $DRY_FLAG 2>&1 | tee -a "$LOG" || true)
        RUN_ID=$(echo "$RUN_OUTPUT" | grep "Run complete:" | awk '{print $NF}' || true)

        if [[ -n "$RUN_ID" && -f "$RESULTS_DIR/$RUN_ID/metrics.json" ]]; then
            DEST="$RESULTS_DIR/benchmark_${MODEL_ID}_${SCENARIO}.json"
            cp "$RESULTS_DIR/$RUN_ID/metrics.json" "$DEST"
            log "Saved → $DEST"
            SUCCESS=$((SUCCESS + 1))
        else
            warn "Metrics not found for $MODEL × $SCENARIO"
            FAILED=$((FAILED + 1))
        fi
    done

    # Remove model to free VRAM/RAM
    if [[ "$DRY_RUN" == false && "$KEEP_MODELS" == false ]]; then
        log "--- Removing $MODEL ---"
        $COMPOSE exec puma_ollama ollama rm "$MODEL" 2>&1 | tee -a "$LOG" || true
    fi

    log "=== DONE: $MODEL ==="
done

log ""
log "==================================================================="
log " BENCHMARK COMPLETE — $(date)"
log "  Total : $TOTAL"
log "  OK    : $SUCCESS"
log "  Failed: $FAILED"
log "  Log   : $LOG"
log "==================================================================="

echo ""
echo "Result files:"
ls "$RESULTS_DIR"/benchmark_*.json 2>/dev/null | sed 's/^/  /' || echo "  (none)"
