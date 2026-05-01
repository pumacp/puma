COMPOSE = docker compose
RUNNER  = $(COMPOSE) run --rm puma_runner

.PHONY: build lint fmt typecheck test smoke up down clean uninstall reinstall

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

uninstall:
	@echo "[PUMA] Stopping and removing all containers, volumes, and networks..."
	$(COMPOSE) down --remove-orphans --volumes
	@echo "[PUMA] Removing PUMA Docker images..."
	-docker images --filter "reference=puma-*" --format "{{.ID}}" | xargs -r docker rmi -f 2>/dev/null
	-docker rmi -f puma-puma_runner puma-puma_dashboard puma-evaluator 2>/dev/null || true
	@echo "[PUMA] Removing local generated data..."
	-docker run --rm -v "$(PWD)/results:/results" -v "$(PWD)/logs:/logs" busybox sh -c "rm -rf /results/* /logs/*" 2>/dev/null || true
	rm -rf results/ logs/ emissions.csv config/runtime_profile.yaml 2>/dev/null || \
	  sudo rm -rf results/ logs/ emissions.csv config/runtime_profile.yaml
	@# Remove GPU env vars written by start_puma.sh; keep any user-set vars
	@if [ -f .env ]; then grep -v "^PUMA_GPU_" .env > .env.tmp && mv .env.tmp .env || rm -f .env.tmp; fi
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "[PUMA] Uninstall complete. Repository files preserved."

reinstall: uninstall
	@echo "[PUMA] Relaunching PUMA from scratch..."
	bash start_puma.sh
