#!/bin/bash
set -e

echo "=========================================="
echo "  Puma Benchmark - Auto-detección GPU/CPU"
echo "=========================================="
echo ""

# Cargar variables del .env si existe
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Función para verificar NVIDIA GPU
check_nvidia_gpu() {
    if command -v nvidia-smi &> /dev/null; then
        return 0
    fi
    return 1
}

# Función para verificar Docker GPU support
check_docker_gpu() {
    if docker info 2>/dev/null | grep -q "nvidia"; then
        return 0
    fi
    return 1
}

# Función para crear docker-compose.yml según el modo
create_docker_compose() {
    local mode=$1
    
    if [ "$mode" = "gpu" ]; then
        cat > docker-compose.yml << 'EOF'
services:
  ollama:
    image: ollama/ollama:latest
    container_name: puma_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
      - OLLAMA_NUM_PARALLEL=${OLLAMA_NUM_PARALLEL:-2}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    networks:
      - puma_network
    healthcheck:
      test: ["CMD-SHELL", "ollama list || exit 0"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 30s

  evaluator:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: puma_evaluator
    volumes:
      - .:/app
    environment:
      - OLLAMA_HOST=${OLLAMA_HOST:-http://ollama:11434}
      - LLM_MODEL=${LLM_MODEL:-qwen2.5:3b}
      - TRIAGE_TARGET_F1=${TRIAGE_TARGET_F1:-0.55}
      - TRIAGE_NUM_ISSUES=${TRIAGE_NUM_ISSUES:-200}
      - TRIAGE_TEMPERATURE=${TRIAGE_TEMPERATURE:-0.0}
      - TRIAGE_SEED=${TRIAGE_SEED:-42}
      - TRIAGE_NUM_PREDICT=${TRIAGE_NUM_PREDICT:-10}
      - ESTIMATION_TARGET_MAE=${ESTIMATION_TARGET_MAE:-3.0}
      - ESTIMATION_PROJECT=${ESTIMATION_PROJECT:-MESOS}
      - ESTIMATION_NUM_ITEMS=${ESTIMATION_NUM_ITEMS:-0}
      - ESTIMATION_TEMPERATURE=${ESTIMATION_TEMPERATURE:-0.0}
      - ESTIMATION_SEED=${ESTIMATION_SEED:-42}
      - ESTIMATION_NUM_PREDICT=${ESTIMATION_NUM_PREDICT:-50}
      - EVALUATION_TIMEOUT=${EVALUATION_TIMEOUT:-0}
      - PYTHONUNBUFFERED=1
      - NVIDIA_VISIBLE_DEVICES=all
    depends_on:
      ollama:
        condition: service_healthy
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    networks:
      - puma_network

volumes:
  ollama_data:

networks:
  puma_network:
    driver: bridge
EOF
    else
        cat > docker-compose.yml << 'EOF'
services:
  ollama:
    image: ollama/ollama:latest
    container_name: puma_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
      - OLLAMA_NUM_PARALLEL=${OLLAMA_NUM_PARALLEL:-1}
    networks:
      - puma_network
    healthcheck:
      test: ["CMD-SHELL", "ollama list || exit 0"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 30s

  evaluator:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: puma_evaluator
    volumes:
      - .:/app
    environment:
      - OLLAMA_HOST=${OLLAMA_HOST:-http://ollama:11434}
      - LLM_MODEL=${LLM_MODEL:-qwen2.5:3b}
      - TRIAGE_TARGET_F1=${TRIAGE_TARGET_F1:-0.55}
      - TRIAGE_NUM_ISSUES=${TRIAGE_NUM_ISSUES:-200}
      - TRIAGE_TEMPERATURE=${TRIAGE_TEMPERATURE:-0.0}
      - TRIAGE_SEED=${TRIAGE_SEED:-42}
      - TRIAGE_NUM_PREDICT=${TRIAGE_NUM_PREDICT:-10}
      - ESTIMATION_TARGET_MAE=${ESTIMATION_TARGET_MAE:-3.0}
      - ESTIMATION_PROJECT=${ESTIMATION_PROJECT:-MESOS}
      - ESTIMATION_NUM_ITEMS=${ESTIMATION_NUM_ITEMS:-0}
      - ESTIMATION_TEMPERATURE=${ESTIMATION_TEMPERATURE:-0.0}
      - ESTIMATION_SEED=${ESTIMATION_SEED:-42}
      - ESTIMATION_NUM_PREDICT=${ESTIMATION_NUM_PREDICT:-50}
      - EVALUATION_TIMEOUT=${EVALUATION_TIMEOUT:-0}
      - PYTHONUNBUFFERED=1
    depends_on:
      ollama:
        condition: service_healthy
    networks:
      - puma_network

volumes:
  ollama_data:

networks:
  puma_network:
    driver: bridge
EOF
    fi
}

# Determinar el modo basado en GPU_MODE del .env
MODE="cpu"
GPU_MODE_CONFIG="${GPU_MODE:-true}"

echo "Configuración GPU_MODE: $GPU_MODE_CONFIG"
echo ""

case "$GPU_MODE_CONFIG" in
    true|TRUE|1)
        echo ">>> GPU_MODE=true - Intentando usar GPU NVIDIA..."
        if check_nvidia_gpu && check_docker_gpu; then
            echo ">>> NVIDIA GPU detectada en el sistema"
            echo ">>> Docker GPU support disponible"
            MODE="gpu"
        else
            echo ">>> GPU no disponible, usando modo CPU como fallback"
            MODE="cpu"
        fi
        ;;
    false|FALSE|0)
        echo ">>> GPU_MODE=false - Usando modo CPU (forzado)"
        MODE="cpu"
        ;;
    auto|AUTO)
        echo ">>> GPU_MODE=auto - Detectando GPU automáticamente"
        if check_nvidia_gpu && check_docker_gpu; then
            echo ">>> NVIDIA GPU detectada en el sistema"
            echo ">>> Docker GPU support disponible"
            MODE="gpu"
        else
            echo ">>> No se detectó GPU NVIDIA o Docker GPU support"
            MODE="cpu"
        fi
        ;;
    *)
        echo ">>> GPU_MODE='$GPU_MODE_CONFIG' no reconocido"
        echo ">>> Opciones válidas: false, true, auto"
        echo ">>> Intentando modo GPU por defecto..."
        if check_nvidia_gpu && check_docker_gpu; then
            MODE="gpu"
        else
            MODE="cpu"
        fi
        ;;
esac

echo ""
echo "MODO SELECCIONADO: $(echo $MODE | tr '[:lower:]' '[:upper:]')"
if [ "$MODE" = "gpu" ]; then
    echo "  - Velocidad: ~1-2s por inferencia"
    echo "  - VRAM necesaria: ~8GB"
    nvidia-smi --query-gpu=name,memory.total --format=csv 2>/dev/null | head -2 || true
else
    echo "  - Velocidad: ~5-15s por inferencia"
    echo "  - RAM necesaria: ~8GB"
fi

echo ""
echo "=========================================="
echo "  Configurando Docker Compose..."
echo "=========================================="

# Crear docker-compose.yml según el modo
create_docker_compose $MODE

echo ""
echo "=========================================="
echo "  Construyendo contenedores..."
echo "=========================================="

# Construir contenedor evaluator
docker-compose build --no-cache

echo ""
echo "=========================================="
echo "  Iniciando servicios..."
echo "=========================================="

# Levantar servicios
docker-compose up -d

echo ""
echo "=========================================="
echo "  Estado de contenedores"
echo "=========================================="
docker-compose ps

echo ""
echo "=========================================="
echo "  Servicios iniciados correctamente"
echo "=========================================="
echo ""
echo "  Ollama: http://localhost:11434"
echo "  Evaluator: Contenedor activo"
echo ""
echo "  Para ejecutar evaluaciones:"
echo "    docker exec puma_evaluator python src/evaluate_triage.py"
echo "    docker exec puma_evaluator python src/evaluate_estimation.py MESOS"
echo ""
echo "  Para ejecutar pruebas:"
echo "    docker exec puma_evaluator pytest tests/"
echo ""
