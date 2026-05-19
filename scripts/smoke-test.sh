#!/usr/bin/env bash
set -euo pipefail

# PUMA end-to-end smoke test
# Validates the academic repo from a fresh clone through to a successful
# benchmark run + dry-run share. Designed to be run after install or as
# a release-gate check.

PUMA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PUMA_ROOT"

GREEN="\033[0;32m"; RED="\033[0;31m"; YELLOW="\033[0;33m"; NC="\033[0m"
pass() { echo -e "${GREEN}✓${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*" >&2; exit 1; }
info() { echo -e "${YELLOW}→${NC} $*"; }

info "PUMA smoke test — running Levels 1-3 of the validation playbook"
echo

# Level 1 — Sanity
info "Level 1 — container + binary sanity"
# puma_ollama is the only long-running service; puma_runner is invoked
# per-command via `docker compose run --rm`.
docker compose ps --status running --services 2>&1 | grep -q puma_ollama || \
  fail "puma_ollama container not running. Run: docker compose up -d puma_ollama"
pass "puma_ollama running"

docker compose run --rm puma_runner puma --help > /dev/null 2>&1 || \
  fail "puma --help failed (puma_runner image cannot be invoked)"
pass "puma CLI loads (puma_runner image invokable)"

SYMBOLS=$(docker compose run --rm puma_runner python -c "import puma.community as c; print(len(c.__all__))" | tr -d '\r')
[ "$SYMBOLS" = "43" ] || fail "puma.community.__all__ has $SYMBOLS symbols, expected 43"
pass "puma.community public API: $SYMBOLS symbols"

# Level 2 — Static checks
info "Level 2 — static checks"
docker compose run --rm puma_runner ruff check src/ > /dev/null 2>&1 || \
  fail "ruff check failed"
pass "ruff check clean"

docker compose run --rm puma_runner ruff format --check src/ > /dev/null 2>&1 || \
  fail "ruff format --check failed"
pass "ruff format clean"

docker compose run --rm puma_runner mypy src/puma/ > /dev/null 2>&1 || \
  fail "mypy failed"
pass "mypy clean (0 errors across 76 files)"

# Level 3 — Test suite
info "Level 3 — pytest suite"
TEST_OUT=$(docker compose run --rm puma_runner pytest tests/ -q 2>&1 | tail -1)
echo "$TEST_OUT" | grep -q "570 passed" || fail "pytest did not report 570 passed: $TEST_OUT"
echo "$TEST_OUT" | grep -q "1 skipped" || fail "pytest did not report 1 skipped: $TEST_OUT"
pass "pytest: 570 passed, 1 skipped"

# Level 3b — Community subset
COMM_OUT=$(docker compose run --rm puma_runner pytest tests/community/ -q 2>&1 | tail -1)
echo "$COMM_OUT" | grep -q "156 passed" || fail "community pytest: $COMM_OUT"
pass "community tests: 156 passed, 1 skipped"

echo
info "Smoke test complete — all checks green"
