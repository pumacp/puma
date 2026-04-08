#!/bin/bash
set -e

echo "=========================================="
echo "  PUMA Benchmark - Reset Results"
echo "=========================================="
echo ""

docker exec puma_evaluator python src/cleanup.py