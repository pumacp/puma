.PHONY: lint test smoke install install-dev clean

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

fmt:
	ruff format src/ tests/
	ruff check --fix src/ tests/

typecheck:
	mypy src/puma/metrics src/puma/runtime src/puma/preflight || true

test:
	pytest tests/unit/ tests/integration/ -v

smoke:
	pytest tests/smoke/ -v -m smoke || pytest tests/unit/ -v -m unit

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
