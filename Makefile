COMPOSE = docker compose
RUNNER  = $(COMPOSE) run --rm puma_runner

.PHONY: build lint fmt typecheck test smoke up down clean

build:
	$(COMPOSE) build puma_runner

lint:
	$(RUNNER) ruff check src/ tests/
	$(RUNNER) ruff format --check src/ tests/

fmt:
	$(RUNNER) ruff format src/ tests/
	$(RUNNER) ruff check --fix src/ tests/

typecheck:
	$(RUNNER) mypy src/puma/metrics src/puma/runtime src/puma/preflight || true

test:
	$(RUNNER) pytest tests/unit/ tests/integration/ -v

smoke:
	$(RUNNER) pytest tests/smoke/ -v -m smoke

up:
	$(COMPOSE) up -d puma_ollama puma_runner

down:
	$(COMPOSE) down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
