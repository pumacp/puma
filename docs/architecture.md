# PUMA Architecture

## 1. Data Flow

```
RunSpec (YAML)
    │
    ▼
Runner.__init__()
    ├── RunSpec.from_yaml()          Pydantic v2 validation + cross-validators
    ├── init_db()                    SQLAlchemy: create tables if not exist
    └── run_id = f"{spec.id}__{spec_hash}__{timestamp}"
    │
    ▼
Runner.run()
    │
    ├─ [DB] INSERT runs (status="running")
    │
    ├─ Runner._execute_inferences()
    │       │
    │       ├── Scenario.sample(n, seed)        DataFrame from CSV dataset
    │       ├── OllamaClient(host, timeout)     HTTP client (httpx)
    │       ├── InferenceCache(db_path)         SQLite prompt-hash → response
    │       │
    │       └── for model × strategy × row × perturbation:
    │               ├── _apply_perturbation()   typos / case / truncate / noise
    │               ├── Strategy.build_prompt() Jinja2 template render
    │               ├── [cache hit?] → return cached response
    │               ├── OllamaClient.generate_sync()   POST /api/generate
    │               └── Scenario.parse_response()  regex → label or None
    │
    ├─ Runner._compute_metrics()
    │       ├── classification_metrics()    F1, accuracy, confusion matrix
    │       ├── regression_metrics()        MAE, MDAE, RMSE, MAE by bin
    │       ├── percentiles()               latency p50/p95/p99
    │       └── parse_failure_rate
    │
    ├─ Runner._persist_predictions()
    │       └── [DB] INSERT instances + predictions
    │
    ├─ [DB] UPDATE runs (status="done")
    ├─ [DB] INSERT metrics (flat key → value rows)
    ├─ [DB] INSERT profile_snapshots
    │
    ├─ results/<run_id>/runspec.yaml     frozen spec
    └─ results/<run_id>/metrics.json    all computed metrics
```

## 2. Package Map

| Package | Module(s) | Key classes / functions |
|---------|-----------|------------------------|
| `puma.preflight` | `detect`, `profile`, `provisioning`, `report` | `detect_capabilities()`, `select_profile()`, `check_provisioning()` |
| `puma.runtime` | `client`, `cache` | `OllamaClient`, `InferenceCache` |
| `puma.datasets` | `jira`, `tawos`, `verify` | `load_jira()`, `load_tawos()`, `verify_jira()`, `print_verify_report()` |
| `puma.scenarios` | `triage_jira`, `estimation_tawos`, `prioritization_jira`, `base` | `Scenario` ABC, 3 concrete classes |
| `puma.adaptation` | `base`, `strategies`, `examples` | `Strategy` ABC, 11 strategy classes, `get_strategy()`, `select_examples()` |
| `puma.perturbations` | `text` | `typos()`, `case_change()`, `truncate()`, `tech_noise()`, `reorder_fields()` |
| `puma.metrics` | `accuracy`, `calibration`, `robustness`, `fairness`, `efficiency`, `stability` | `classification_metrics()`, `expected_calibration_error()`, `robustness_score()`, etc. |
| `puma.sustainability` | `codecarbon_wrapper` | `@track_emissions`, `emissions_summary()`, `gco2_per_f1_point()` |
| `puma.orchestrator` | `runspec`, `runner`, `compare` | `RunSpec`, `Runner`, `compare_runs()` |
| `puma.storage` | `models`, `db` | `Run`, `Instance`, `Prediction`, `Metric`, `Emission`, `ProfileSnapshot`, `init_db()`, `session_scope()` |
| `puma.dashboard` | `app`, `components`, `data` | Streamlit 9-view app, `load_runs()`, `metrics_pivot()`, `metric_card()`, etc. |
| `puma.reporting` | `report` | `generate_report()`, `_convert_to_pdf()` |
| `puma.cli` | `cli` | Typer app: 15 commands + 5 command groups |

## 3. Docker Services

```
docker-compose.yml
│
├── puma_ollama          image: ollama/ollama:latest
│   ├── port: 11434:11434
│   ├── volume: ollama_models:/root/.ollama
│   └── network: puma_network
│
├── puma_runner          build: Dockerfile (python:3.11-slim + pip install)
│   ├── volume: .:/app  (live code mount)
│   ├── volume: puma_data:/app/data
│   ├── env: PYTHONPATH=/app/src, OLLAMA_HOST=http://puma_ollama:11434
│   └── network: puma_network
│
└── puma_dashboard       build: same Dockerfile
    ├── port: 8501:8501
    ├── volume: .:/app, puma_data:/app/data
    ├── command: streamlit run src/puma/dashboard/app.py ...
    └── network: puma_network
```

Shared volumes:
- `ollama_models` — Ollama model weights (persistent across container restarts)
- `puma_data` — SQLite databases and datasets (mounted at `/app/data`)

## 4. Database Schema

All tables use SQLAlchemy 2.0 declarative models (`src/puma/storage/models.py`).

```sql
-- One row per benchmark run
CREATE TABLE runs (
    run_id      TEXT PRIMARY KEY,   -- "{spec.id}__{hash}__{timestamp}"
    spec_hash   TEXT,               -- SHA-256[:16] of RunSpec (excluding description)
    spec_yaml   TEXT,               -- JSON-serialised RunSpec for replay
    profile     TEXT,               -- hardware profile used
    started_at  DATETIME,
    finished_at DATETIME,
    status      TEXT                -- running | done | error
);

-- Canonical dataset instances (deduplicated across runs)
CREATE TABLE instances (
    instance_id TEXT PRIMARY KEY,
    dataset     TEXT,               -- triage_jira | estimation_tawos | ...
    source_id   TEXT,               -- original ID from the dataset
    input_text  TEXT,               -- raw input (title + description)
    gold_label  TEXT,
    UNIQUE (dataset, source_id)
);

-- One row per model × strategy × instance × perturbation
CREATE TABLE predictions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT REFERENCES runs(run_id),
    instance_id   TEXT REFERENCES instances(instance_id),
    model         TEXT,
    strategy      TEXT,
    prompt_hash   TEXT,             -- SHA-256[:16] of the rendered prompt
    raw_response  TEXT,
    parsed_label  TEXT,             -- null if parse_response returned None
    latency_ms    REAL,
    tokens_in     INTEGER,
    tokens_out    INTEGER,
    perturbation  TEXT,             -- null = original; else perturbation name
    seed          INTEGER,
    recorded_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Flat metric rows (one per metric name per run)
CREATE TABLE metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT REFERENCES runs(run_id),
    scope       TEXT DEFAULT 'global',
    metric_name TEXT,               -- e.g. "f1_macro", "latency.p95"
    value       REAL,
    computed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- CodeCarbon emissions per run
CREATE TABLE emissions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT REFERENCES runs(run_id),
    kwh        REAL,
    co2_kg     REAL,
    duration_s REAL,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Hardware snapshot at run time
CREATE TABLE profile_snapshots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT REFERENCES runs(run_id),
    os             TEXT,
    cpu            TEXT,
    ram_gb         REAL,
    gpu            TEXT,
    vram_gb        REAL,
    ollama_version TEXT,
    puma_version   TEXT,
    snapshot_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 5. OllamaClient Contract

```python
@dataclass(frozen=True)
class TokenLogprob:
    token: str
    logprob: float
    top_logprobs: list["TokenLogprob"]

@dataclass(frozen=True)
class GenerationResult:
    model: str
    response: str
    logprobs: list[TokenLogprob]
    total_duration_ns: int
    load_duration_ns: int
    prompt_eval_count: int      # tokens in prompt
    eval_count: int             # tokens generated
    eval_duration_ns: int
    raw: dict                   # full Ollama JSON response

class OllamaClient:
    def generate_sync(self, model, prompt, *, temperature, seed,
                      max_tokens, logprobs, top_logprobs) -> GenerationResult: ...
    async def generate(self, ...) -> GenerationResult: ...
```

The client always sends `options: {"temperature": ..., "seed": ..., "num_predict": ...}` in the `/api/generate` payload. When `logprobs=True`, it adds `"logprobs": true, "top_logprobs": N`.

Retry policy: 3 attempts with exponential backoff on connection errors.

## 6. Inference Cache

`InferenceCache` stores `(model, prompt_hash, temperature, seed) → (response, tokens_in, tokens_out)` in `data/cache/inferences.db`. On a cache hit the Ollama call is skipped entirely.

```python
cache = InferenceCache(db_path=Path("data/cache/inferences.db"))
hit = cache.get(model, prompt_hash, temperature, seed)
if hit is None:
    result = client.generate_sync(...)
    cache.put(model, prompt_hash, temperature, seed, result)
```

## 7. Prompt Template System

Templates use Jinja2. Each scenario × strategy pair has its own `.jinja` file:

```
specs/prompts/
├── triage_jira/
│   ├── zero_shot.jinja
│   ├── zero_shot_cot.jinja
│   ├── few_shot.jinja
│   ├── cot_few_shot.jinja
│   ├── rcoif.jinja
│   ├── contextual_anchoring.jinja
│   └── egi.jinja
├── estimation_tawos/      (same 7 files)
└── prioritization_jira/   (same 7 files)
```

Available template variables:

| Variable | Type | Description |
|----------|------|-------------|
| `{{ title }}` | str | Issue title |
| `{{ description }}` | str | Issue description / body |
| `{{ examples }}` | list[dict] | Few-shot examples (empty for zero-shot) |
| `{{ gold_label }}` | str | Expected label (used in CoT rationale examples) |
| `{{ labels }}` | list[str] | Valid output labels for the scenario |

`Strategy.build_prompt(scenario, instance)` renders the template and returns the final prompt string.

## 8. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Spec-driven runs** | RunSpec YAML + fixed seed makes every run 100% reproducible |
| **Dry-run mode** | Full pipeline test without Ollama; used in all 206 unit tests |
| **PYTHONPATH=/app/src** | No editable install needed; volume-mount code works immediately |
| **Read-only dashboard** | Streamlit never writes to DB; preserves result integrity |
| **SQLite over Postgres** | Zero-infrastructure; single file; embeds in Docker volume |
| **Flat metrics table** | `(run_id, metric_name, value)` enables pivot and comparison without schema changes when new metrics are added |
| **session_scope() context manager** | Guarantees rollback on exception; prevents partial writes |
| **Sync OllamaClient in Runner** | Avoids event-loop complexity in the orchestration loop; async variant available for future parallel batching |
| **Parse failure = None** | Failed parses are excluded from metric computation but counted in `parse_failure_rate`; no "unknown" class pollution |
