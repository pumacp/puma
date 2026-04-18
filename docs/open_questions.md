# Open Questions

Design decisions taken without explicit consultation during implementation.
Reviewed and consolidated into `docs/design_decisions.md` at phase close.

## Phase 2

**Q4: TAWOS.sql 4.3 GB runtime parsing**
The db/TAWOS.sql from SOLAR-group/TAWOS is 4.3 GB with 1004 INSERT INTO `Issue` batches. Runtime parsing in Python is impractical (estimated >10 min for the character-by-character approach). Decision: use `data/tawos_clean.csv` as the canonical runtime artifact (9020 rows, pre-processed by the existing `src/data_prep.py`). The SQL is kept in db/ as a source-of-truth reference; a one-time conversion script can regenerate the CSV. Registered as design decision for Phase 7 docs.

**Q5: OllamaClient sync vs async**
Both sync (`generate_sync`) and async (`generate`) variants implemented. Sync is used in Phase 2/3/5 orchestration to avoid event-loop complexity with the Ollama SDK. Async variant available for future parallel batch execution.

## Phase 0

**Q1: Response parsing fallback policy**
When a model does not follow the requested format (e.g., returns "The priority is Critical because..."), the current parser uses a substring match. If no known label is found, returns `None` (excluded from metrics). Alternative considered: assign class "unknown" and penalize F1. Decision: keep `None`/exclude for now; flagged for F3 when the full adaptation layer handles retries.

**Q2: pytest.ini vs pyproject.toml config precedence**
The Docker container has an older pytest that prefers `pytest.ini` over `pyproject.toml [tool.pytest]`. Both exist. The `pytest.ini` is kept as-is to avoid breaking the existing test runner; `pyproject.toml` carries the canonical config for when the container is rebuilt with newer tooling.

**Q3: System prompt language**
MVP used Spanish prompts. Migrated modules use English prompts (per "all documentation and code in English" rule). The Spanish prompts are preserved in legacy `src/evaluate_*.py` wrappers until Phase 3 when Jinja prompt templates replace them.
