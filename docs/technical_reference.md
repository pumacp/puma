# Technical reference

This page is the consolidated technical entry point to PUMA at the
v4.0.0 readiness milestone. It is written for evaluators, future
maintainers, and integrators who need a single comprehensive
reference covering the architecture, configuration surface, JSON
Schema, storage layer, CLI surface, metric families, methodologies,
glossary, decisions log, strengths, known limitations, risks, and
roadmap.

For day-to-day workflow guidance see
[`development-workflow.md`](development-workflow.md); for the user
landing page see [`index.md`](index.md); for the full CLI
manual see [`cli_reference.md`](cli_reference.md); for the security
posture see [`security.md`](security.md); for sustainability
methodology see [`sustainability.md`](sustainability.md); for the
open debt tracker see [`known_debt.md`](known_debt.md).

This page does not duplicate those references — it consolidates,
cross-links, and contextualises them.

---

## 1. Overview

PUMA is a local-first benchmarking framework for open-weight language
models on three ICT Project Management tasks: issue **triage**,
story-point **estimation**, and pairwise backlog **prioritization**.
Every run is deterministic (`seed=42`, `temperature=0.0`), every
result is integrity-checked (SHA-256 over the canonical predictions
tuple), and every run is sustainability-aware (CodeCarbon energy +
CO₂). The platform runs entirely on the contributor's machine — no
external API calls are made during inference.

Navigate this page top-down for a guided tour; jump to §9 (Glossary)
for term definitions, §10 (Decisions log) for the architectural
timeline, §12 (Known limitations) for outstanding debt, or §15
(References) for cross-links.

---

## 2. Architecture (the 6-layer model)

PUMA is structured as six cooperating layers. Each layer has a
narrow responsibility and a small public surface; the orchestrator
binds them into a benchmark run.

```
┌─────────────────────────────────────────────────────────────────┐
│  6. Dashboard + Reporting + CLI                                  │
│     Streamlit dashboard (9 views), report rendering, Typer CLI   │
├─────────────────────────────────────────────────────────────────┤
│  5. Storage + Orchestrator                                       │
│     SQLite ORM (Run, Instance, Prediction, Metric, Emission,     │
│     ProfileSnapshot), bi-temporal columns, run lifecycle         │
├─────────────────────────────────────────────────────────────────┤
│  4. Runtime + Metrics + Sustainability                           │
│     Ollama HTTP loop (httpx + logprobs), 7 metric families,      │
│     CodeCarbon energy + CO₂ tracking                             │
├─────────────────────────────────────────────────────────────────┤
│  3. Adaptation + Perturbations                                   │
│     Prompt-strategy application (zero-shot, few-shot-3 / 6,      │
│     chain-of-thought, RCOIF, contextual-anchoring, ...),         │
│     optional input perturbations for robustness                  │
├─────────────────────────────────────────────────────────────────┤
│  2. Datasets + Scenarios                                         │
│     Corpus loading, instance enumeration, Jinja2 prompt-template │
│     binding, scenario-specific parsers                           │
├─────────────────────────────────────────────────────────────────┤
│  1. Preflight                                                    │
│     Hardware detection, profile selection, Ollama reachability,  │
│     model availability, dataset integrity                        │
└─────────────────────────────────────────────────────────────────┘
```

Layer-by-layer:

- **1. Preflight** (`src/puma/preflight/`) — detects the host (CPU,
  RAM, GPU, Apple Silicon variant), selects the matching execution
  profile, verifies the Ollama daemon is reachable, and confirms
  the requested model is present locally. The selected profile is
  recorded as a `ProfileSnapshot` row in the run.
- **2. Datasets + Scenarios** (`src/puma/datasets/`,
  `src/puma/scenarios/`) — loads the corpus rows for the requested
  scenario (`triage_jira`, `effort_tawos`, `prioritization_jira`),
  enumerates instances with their gold labels, and binds the
  scenario-appropriate Jinja2 prompt template.
- **3. Adaptation + Perturbations** (`src/puma/adaptation/`,
  `src/puma/perturbations/`) — applies the prompting strategy
  (zero-shot, few-shot, chain-of-thought, RCOIF,
  contextual-anchoring, ...) and any robustness perturbations to the
  rendered prompt.
- **4. Runtime + Metrics + Sustainability** (`src/puma/runtime/`,
  `src/puma/metrics/`, `src/puma/sustainability/`) — drives the
  Ollama HTTP loop over `httpx`, optionally captures logprobs,
  computes the seven metric families on completion, and tracks
  energy + CO₂ via CodeCarbon if requested.
- **5. Storage + Orchestrator** (`src/puma/storage/`,
  `src/puma/orchestrator/`) — persists every row to SQLite via
  SQLAlchemy ORM models with bi-temporal columns
  (`computed_at` / `recorded_at` / `started_at` / `finished_at`),
  and binds the layers into the run lifecycle.
- **6. Dashboard + Reporting + CLI** (`src/puma/dashboard/`,
  `src/puma/reporting/`, `src/puma/cli.py`) — surfaces results
  through a seven-view Streamlit dashboard (including the
  S12.16 Multi-model comparison view), Markdown / PDF report
  rendering, and the Typer-based `puma` CLI.

The layers are read-only from below: layer 4 never writes to layer 3,
layer 5 never inspects layer 4's runtime state, and the dashboard
never triggers inference (it reads persisted SQLite rows only).

---

## 3. Configuration reference

### 3.1 `specs/runs/*.yaml` — the run-spec format

A run-spec is a single declarative YAML file that fully describes a
benchmark run. Every shipped baseline lives in `specs/runs/`; this
directory is **locked** (touching a canonical baseline shifts its
reference metrics).

Minimal example:

```yaml
id: smoke_triage_v1
description: "Smoke run: 10 triage instances on qwen2.5:3b."
scenario: triage_jira
sample_size: 10
models:
  - qwen2.5:3b
adaptation:
  strategy: [zero-shot]
inference:
  temperature: 0.0
  seed: 42
metrics: [f1_macro]
```

Advanced example (the canonical triage baseline):

```yaml
id: baseline_triage_v1
description: "Canonical baseline: triage_jira × qwen2.5:3b × contextual-anchoring × no perturbations × 200 instances. Reference F1-macro = 0.5867 ± 0.01."
scenario: triage_jira
sample_size: 200
models:
  - qwen2.5:3b
adaptation:
  strategy: [contextual-anchoring]
  cot: [false]
inference:
  temperature: 0.0
  seed: 42
  max_tokens: 256
  logprobs: false
perturbations: []
metrics:
  - f1_macro
  - latency_p95
sustainability:
  codecarbon: true
repeat: 1
```

Fields:

| Field | Type | Required | Default | Semantics |
|---|---|---|---|---|
| `id` | string | yes | — | Stable identifier; combined with the spec hash and start timestamp to form the run_id. |
| `description` | string | yes | — | Human-readable one-liner; surfaces in reports. |
| `scenario` | enum | yes | — | One of `triage_jira`, `effort_tawos` / `estimation_tawos`, `prioritization_jira`. |
| `sample_size` | int | yes | — | Number of instances to load from the scenario corpus (random per `seed`). |
| `models` | list[string] | yes | — | Ollama tags to evaluate (e.g. `qwen2.5:3b`, `llama3:8b`). |
| `adaptation.strategy` | list[string] | yes | — | One or more prompting strategies (e.g. `zero-shot`, `few-shot-3`, `cot`, `rcoif`, `contextual-anchoring`). |
| `adaptation.cot` | list[bool] | no | `[false]` | Per-strategy CoT toggle. |
| `inference.temperature` | float | yes | `0.0` | Sampling temperature. Pinned to `0.0` for canonical baselines. |
| `inference.seed` | int | yes | `42` | RNG seed. Pinned to `42` for canonical baselines. |
| `inference.max_tokens` | int | no | model default | Max generation length. |
| `inference.logprobs` | bool | no | `false` | Capture per-token logprobs for calibration metrics. |
| `perturbations` | list[string] | no | `[]` | Optional robustness perturbations (e.g. gendered-prefix substitution). |
| `metrics` | list[string] | yes | — | Metrics to compute (`f1_macro`, `mae`, `mdae`, `accuracy`, `ece`, `latency_p50`, `latency_p95`, `confusion_matrix`, ...). |
| `sustainability.codecarbon` | bool | no | `false` | Enable CodeCarbon energy + CO₂ tracking for the run. |
| `repeat` | int | no | `1` | Number of independent re-runs of the spec (for stability metrics). |
| `profile_required` | string | no | — | Optional hardware-profile gate (e.g. `gpu-entry`); the run aborts if the detected profile does not match. Required by `puma share-results` to populate the submission's `hardware_profile.profile_id`. |

### 3.2 `config/profiles.yaml` — hardware profile definitions

Each profile entry under `profiles.<name>` declares the hardware
floor PUMA requires before allowing the scenarios listed under that
profile. The file is **locked** (changes affect which models a host
is allowed to run and can shift reproducibility envelopes).

Standard profiles (5):

| Profile | Min RAM | GPU | Min VRAM | Scenarios enabled |
|---|---|---|---|---|
| `cpu-lite` | 8 GB | no | — | triage_jira |
| `cpu-standard` | 16 GB | no | — | triage_jira, estimation_tawos |
| `gpu-entry` | 16 GB | yes | 6 GB | triage_jira, estimation_tawos, prioritization_jira |
| `gpu-mid` | 16 GB | yes | 12 GB | triage_jira, estimation_tawos, prioritization_jira |
| `gpu-high` | 32 GB | yes | 24 GB | triage_jira, estimation_tawos, prioritization_jira |

Apple Silicon profiles (10): `apple-silicon-m3`, `apple-silicon-m3-pro`,
`apple-silicon-m3-max`, `apple-silicon-m4`, `apple-silicon-m4-pro`,
`apple-silicon-m4-max`, `apple-silicon-m5`, `apple-silicon-m5-pro`,
`apple-silicon-m5-max`, `apple-silicon-m5-ultra`. All Apple Silicon
entries are currently `empirical_validation: pending` (PUMA has no
Mac hardware in its validation set as of v4.0.0 readiness).

Fields per profile:

| Field | Type | Required | Semantics |
|---|---|---|---|
| `description` | string | yes | Human-readable summary. |
| `requirements.min_ram_gb` | int | yes | Minimum host RAM. |
| `requirements.gpu_required` | bool | yes | Whether a discrete GPU is required. |
| `requirements.min_vram_gb` | int | when `gpu_required: true` | Minimum GPU VRAM. |
| `requirements.min_disk_gb` | int | yes | Minimum free disk for the model cache. |
| `requirements.apple_silicon_required` | bool | Apple-only | Gates the profile to macOS arm64. |
| `requirements.chip_brand_match` | string | Apple-only | Exact `sysctl -n machdep.cpu.brand_string` match (e.g. `"Apple M4 Pro"`). |
| `requirements.min_unified_memory_gb` | int | Apple-only | Lower bound of the chip variant's unified memory. |
| `scenarios` | list[string] | yes | Scenarios enabled on this profile. |
| `empirical_validation` | enum | Apple-only | `pending` until measured on the hardware. |
| `runtime_mode_recommended` | string | Apple-only | E.g. `native` for Metal acceleration. |

### 3.3 `config/models_catalog.yaml` — model catalog entries

Top-level keys: `catalog_version` (string), `catalog_changelog_path`
(string), `models` (list). The file is **locked** — see
`docs/CATALOG_HISTORY.md` for the version trail.

Per-entry fields:

| Field | Type | Required | Semantics |
|---|---|---|---|
| `ollama_tag` | string | yes | Exact tag for `ollama pull` (e.g. `qwen2.5:3b`). |
| `params_b` | float | yes | Parameter count in billions. |
| `gguf_size_gb` | float | yes | Approximate disk size of the GGUF file. |
| `context_window` | int | yes | Maximum context length in tokens. |
| `logprobs_supported` | bool | yes | Whether the model returns per-token logprobs (needed for calibration metrics). |
| `profiles_compatible` | list[string] | yes | Hardware profiles that can run this model without OOM. |
| `timeout_s` | int | yes | Per-instance Ollama call timeout. |
| `notes` | string | no | Free-text rationale surfaced as the rationale column in `puma models recommended`. |

The current `catalog_version` is `2.7.0`. Models currently catalogued
include qwen2.5 (0.5b / 1.5b / 3b / 7b), llama3 family, mistral
family, deepseek-r1, and the gemma family — see the file for the
canonical list.

---

## 4. JSON Schema reference (`schema_data/submission.v1.json`)

Every PUMA Community submission validates against the immutable
**v1.0.0** JSON Schema at
`src/puma/community/schema_data/submission.v1.json`. The schema is
JSON Schema Draft 2020-12 and is **locked** (the P3 constraint —
any drift is detected at submission time).

### 4.1 Root payload

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema_version` | string | const | `"1.0.0"` (default). |
| `submission_id` | string | optional | UUID format. |
| `submitted_at` | string | optional | `date-time` format. |
| `submitter` | object | yes | `$ref: #/$defs/Submitter`. |
| `puma_version` | string | yes | Semver pattern `^\d+\.\d+\.\d+(-[a-zA-Z0-9\.]+)?$`. |
| `run_metadata` | object | yes | `$ref: #/$defs/RunMetadata`. |
| `hardware_profile` | object | yes | `$ref: #/$defs/HardwareProfile`. |
| `metrics` | object | yes | `$ref: #/$defs/Metrics`. |
| `sustainability` | object | yes | `$ref: #/$defs/Sustainability`. |
| `integrity` | object | yes | `$ref: #/$defs/Integrity`. |
| `raw_predictions_url` | string \| null | optional | URI, max 2083 chars. |
| `notes` | string \| null | optional | Max 2000 chars. |

### 4.2 `$defs/Submitter`

Fields: `name_or_alias` (string, 3–64 chars, `^[A-Za-z0-9_\-\.]+$`),
`affiliation` (string \| null, max 128), `contact` (string \| null,
max 128), `consent_public_release` (bool, required),
`consent_redistribution` (bool, required), `consent_research_use`
(bool, required), `license` (const `"CC-BY-4.0"`).

### 4.3 `$defs/RunMetadata`

Fields: `scenario` (enum: `triage_jira` | `effort_tawos` |
`prioritization_jira`), `model` (string, max 128), `strategy` (enum:
`zero_shot` | `zero_shot_cot` | `few_shot_3` | `few_shot_6` |
`cot_few_shot` | `rcoif` | `contextual_anchoring` | `egi` |
`self_consistency`), `n_instances` (int 1–100000), `seed` (int,
default 42), `temperature` (float 0.0–2.0), `ollama_version`
(string, max 64), `started_at` / `completed_at` (date-time),
`latency_ms_total` / `latency_ms_p50` / `latency_ms_p95` (int ≥ 0).

### 4.4 `$defs/HardwareProfile`

Fields: `profile_id` (string, max 64), `cpu_model` (string, max
128), `cpu_cores` (int 1–512), `ram_gb` (int 1–4096), `gpu_model`
(string \| null, max 128), `gpu_vram_gb` (int \| null, 0–512), `os`
(string, max 128). Required: `profile_id`, `cpu_model`, `cpu_cores`,
`ram_gb`, `os`.

### 4.5 `$defs/Metrics`

Fields: `f1_macro` (float 0.0–1.0 \| null), `f1_per_class` (object
\| null), `mae` (float ≥ 0 \| null), `mdae` (float ≥ 0 \| null),
`accuracy` (float 0.0–1.0 \| null), `confusion_matrix` (int[][] \|
null), `ece` (float 0.0–1.0 \| null). At least one of f1_macro /
mae / accuracy must be present.

### 4.6 `$defs/Sustainability`

Fields: `codecarbon_version` (string, max 32), `co2_grams_total`
(float ≥ 0), `energy_kwh_total` (float ≥ 0), `tracking_mode` (enum:
`machine` | `process`), `country_iso` (string, exactly 3 uppercase
letters). All required.

### 4.7 `$defs/Integrity`

Fields: `predictions_summary_hash` (string, SHA-256 hex: 64
lowercase hex chars), `payload_signature` (string \| null, max 512),
`verification_status` (enum: `unverified` | `self-attested` |
`community-verified`, default `self-attested`). Required:
`predictions_summary_hash`.

### 4.8 Minimal valid example

```json
{
  "submitter": {
    "name_or_alias": "alice42",
    "consent_public_release": true,
    "consent_redistribution": true,
    "consent_research_use": true
  },
  "puma_version": "4.0.0",
  "run_metadata": {
    "scenario": "triage_jira", "model": "qwen2.5:3b",
    "strategy": "contextual_anchoring", "n_instances": 200,
    "temperature": 0.0, "ollama_version": "0.5.1",
    "started_at":"2026-05-30T10:00:00Z","completed_at":"2026-05-30T10:18:00Z",
    "latency_ms_total": 1080000, "latency_ms_p50": 4900, "latency_ms_p95": 7800
  },
  "hardware_profile": {
    "profile_id": "gpu-entry", "cpu_model": "AMD Ryzen 7 5800X",
    "cpu_cores": 16, "ram_gb": 32, "os": "Linux 6.8"
  },
  "metrics": {"f1_macro": 0.5894},
  "sustainability": {
    "codecarbon_version": "2.7.0", "co2_grams_total": 12.4,
    "energy_kwh_total": 0.031, "tracking_mode": "process",
    "country_iso": "ESP"
  },
  "integrity": {
    "predictions_summary_hash": "9f8c1d2e3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d"
  }
}
```

---

## 5. Storage / ORM reference (`src/puma/storage/models.py`)

PUMA persists run state in a single SQLite database (default
`data/puma.db`). The schema is defined by SQLAlchemy 2.x
declarative ORM models in `src/puma/storage/models.py`; Alembic
manages migrations. The schema is intentionally **append-only** for
audit purposes — once a row is written it is not mutated.

| Model | Table | Primary key | Purpose |
|---|---|---|---|
| `Run` | `runs` | `run_id` (string, 64 chars) | One row per benchmark run. |
| `Instance` | `instances` | `instance_id` (string, 64 chars) | One row per dataset row, shared across runs. |
| `Prediction` | `predictions` | `pred_id` (int, autoincrement) | One row per (run, instance, model, strategy) tuple. |
| `Metric` | `metrics` | `metric_id` (int, autoincrement) | One row per (run, metric_name, scope, model, strategy, subgroup). |
| `Emission` | `emissions` | `emission_id` (int, autoincrement) | One row per CodeCarbon measurement for a run. |
| `ProfileSnapshot` | `profile_snapshots` | `snapshot_id` (int, autoincrement); unique on `run_id` | One row per run capturing the host profile. |

### 5.1 `Run`

Columns: `run_id` (PK), `spec_hash` (string, 16), `spec_yaml` (text
\| null), `profile` (string, 32 \| null), `started_at` (UTC
datetime, server-default `now()`), `finished_at` (datetime \|
null), `status` (string, default `"running"`; one of `running` /
`done` / `error`). Relationships: `predictions`, `metrics`,
`emissions`, `profile_snapshot` (one-to-one).

### 5.2 `Instance`

Columns: `instance_id` (PK), `dataset` (string, 32), `source_id`
(string, 128), `input_text` (text), `gold_label` (string, 128).
Unique constraint: `(dataset, source_id)`. Relationships:
`predictions`.

### 5.3 `Prediction`

Columns: `pred_id` (PK), `run_id` (FK), `instance_id` (FK), `model`
(string, 64), `strategy` (string, 32), `prompt_hash` (string, 16),
`raw_response` (text), `parsed_label` (string, 128 \| null),
`confidence` (float \| null), `logprobs_json` (text \| null),
`latency_ms` (float \| null), `tokens_in` (int \| null),
`tokens_out` (int \| null), `perturbation` (string, 64 \| null),
`seed` (int, default 42).

### 5.4 `Metric`

Columns: `metric_id` (PK), `run_id` (FK), `scope` (string, 32; one
of `global` / `per_model` / `per_group`), `model` (string, 64 \|
null), `strategy` (string, 32 \| null), `metric_name` (string, 64),
`value` (float), `subgroup` (string, 128 \| null), `computed_at`
(UTC datetime, server-default `now()`).

### 5.5 `Emission`

Columns: `emission_id` (PK), `run_id` (FK), `kwh` (float \| null),
`co2_kg` (float \| null), `duration_s` (float \| null),
`cpu_energy` (float \| null), `gpu_energy` (float \| null),
`ram_energy` (float \| null), `recorded_at` (UTC datetime,
server-default `now()`).

### 5.6 `ProfileSnapshot`

Columns: `snapshot_id` (PK), `run_id` (FK, unique), `os` (string,
64 \| null), `cpu` (string, 128 \| null), `ram_gb` (float \| null),
`gpu` (string, 128 \| null), `vram_gb` (float \| null),
`ollama_version` (string, 32 \| null), `puma_version` (string, 32
\| null), `extra` (JSON \| null).

Note on bi-temporality: PUMA does not implement a strict bi-temporal
schema (valid-time + transaction-time) — instead it uses per-row
timestamps (`started_at`, `finished_at`, `computed_at`,
`recorded_at`) plus the append-only convention to give an
auditable single-time history.

---

## 6. Metric families

PUMA's metric surface spans seven families. The metric **name**
column below is the exact string used in run-spec `metrics:` lists
and in the `Metric.metric_name` column.

| Family | Example metric names | Notes |
|---|---|---|
| **Accuracy** | `f1_macro`, `f1_weighted`, `accuracy`, `per_class.<label>.f1`, `confusion_matrix` | Primary triage signal: F1-macro. |
| **Calibration** | `ece` (expected calibration error), reliability diagram data | Requires `inference.logprobs: true`. |
| **Efficiency** | `latency.p50`, `latency.p95`, `latency.p99`, `latency.mean`, `tokens_in`, `tokens_out` | Per-instance and aggregated. |
| **Stability** | Cross-repeat variance (when `repeat > 1`); cold-vs-warm delta tracked separately (F2 in `known_debt.md`). | |
| **Robustness** | Per-perturbation metric delta (e.g. gendered-prefix substitution flip rate). | Requires `perturbations:`. |
| **Fairness** | Per-subgroup `f1_macro` / `mae` / disparity; output by `puma bias-analysis`. | |
| **Sustainability** | `co2_kg`, `kwh`, `cpu_energy`, `gpu_energy`, `ram_energy`, `duration_s`. | Captured by CodeCarbon when `sustainability.codecarbon: true`. |

Canonical reference values at the v4.0.0 readiness milestone:

| Scenario | Model | Strategy | Metric | Reference value |
|---|---|---|---|---|
| triage_jira | qwen2.5:3b | contextual-anchoring | f1_macro | 0.5894 (± 0.01) |
| estimation_tawos | qwen2.5:3b | contextual-anchoring | mae | 5.7150 (D31 drift tracked; current ~2.91 on May 10 DB) |

See `puma validate-baseline` for the runtime check that compares
the current spec's metrics against the reference value.

---

## 7. CLI surface (overview)

Full reference: [`cli_reference.md`](cli_reference.md). The table
below is a navigational overview; every cell in the **Command**
column links to the full documentation of that command (or its
sub-group) on the CLI reference page.

| Command | Purpose | Primary args |
|---|---|---|
| `puma run` | Execute a benchmark run-spec. | `<spec_path>` |
| `puma compare` | Compare metrics across two runs. | `<run_id_a> <run_id_b>` |
| `puma validate-baseline` | Verify a canonical metric against its reference. | `<spec_path>` |
| `puma report` | Generate a Markdown / PDF run report. | `<run_id>` |
| `puma list-runs` | Tabular listing of runs in the DB. | — |
| `puma doctor` | Read-only environment health checks. | — |
| `puma env` | Print resolved PUMA environment (paths, theme, profile). | — |
| `puma preflight` | Detect hardware and select an execution profile. | — |
| `puma datasets` | Verify dataset integrity and show statistics. | — |
| `puma prepare-datasets` | Prepare the canonical datasets (jira_balanced_200, TAWOS, prioritization). | — |
| `puma models list` | Tags pulled locally in Ollama (read-only). | — |
| `puma models show <name>` | Per-model details from `/api/show`. | `<name>` |
| `puma models recommended` | Curated catalog with local availability. | — |
| `puma wilcoxon` | Wilcoxon signed-rank pairwise comparison of two runs. | `<run_id_a> <run_id_b>` |
| `puma bias-analysis` | Bias analysis from perturbed runs in the DB. | — |
| `puma generate-plots` | Consolidated plots (png/pdf/svg). | — |
| `puma db` | Manage the DB schema (Alembic-driven migrations). | sub-group |
| `puma cache` | Manage the inference cache. | sub-group |
| `puma dashboard` | Launch the Streamlit dashboard (Multi-model view included since S12.16). | — |
| `puma auth` | Manage PUMA Community credentials. | sub-group |
| `puma share-results` | Share a run with the Community (local dry-run or PR). | `--run-id` |
| `puma community` | Browse, pull, verify, and validate Community submissions. | sub-group |

Exit codes follow a consistent convention: `0` success, `1`
operational failure, `2` usage / validation error.

---

## 8. Methodologies in use

PUMA's research and engineering posture is grounded in a small set
of established methodologies. The notes below are pointers; full
methodological discussion belongs in the project's separate
research artifacts.

- **Design Science Research (DSR)** — the platform itself is the
  designed artifact; baselines and the federated submission hub are
  the evaluation instruments.
- **Spec-Driven Development (SDD)** — every benchmark run is fully
  described by a versioned YAML spec under `specs/runs/`; PRs follow
  the conventional-commits format documented in
  [`development-workflow.md`](development-workflow.md).
- **Keshav Three-Pass method** — used for the systematic literature
  review backing the chosen scenarios and metric families.
- **PRISMA 2020** — applied to the systematic-review process.
- **Wilcoxon signed-rank test** — non-parametric statistical
  validation of pairwise model comparisons, available as
  `puma wilcoxon`.
- **Tool-agnostic contribution discipline** — commit attribution
  policy is enforced by `.githooks/commit-msg` (strips
  `Co-authored-by:`, `Signed-off-by: …<AI tool>`, and `Generated-by:`
  trailers) and by the repo-wide brand-scanner test
  (`tests/integration/test_agent_agnostic_remote.py`). See
  [`development-workflow.md`](development-workflow.md) §13 and
  [`security.md`](security.md) §10.
- **APA 7th edition** — citation format used in the project's
  research artifacts.

For the sustainability methodology specifically (CodeCarbon, the
energy-and-CO₂ measurement model, country grid factors) see
[`sustainability.md`](sustainability.md).

---

## 9. Glossary

Alphabetised. Cross-links are to the canonical reference for each
term elsewhere in the documentation.

- **Acrostic** — the FOLLOW THE WHITE PUMA block on
  [`README.md`](https://github.com/pumacp/puma/blob/develop/README.md)
  and [`docs/index.md`](index.md). Visual layout is intentionally
  relaxed (the immutability tests are
  `@pytest.mark.skip` since PR #47); see
  [`development-workflow.md`](development-workflow.md) §12.
- **Adaptation** — the prompt-strategy application stage in the
  6-layer architecture (§2.3 above).
- **Baseline** — a canonical run-spec with a published reference
  metric value; sanity-oracle target for `puma validate-baseline`.
- **Bandit** — Python SAST tool; runs in CI via
  `.github/workflows/bandit.yml` at HIGH-only threshold
  ([`security.md`](security.md) §7).
- **Bi-temporal** — append-only schema with per-row timestamps
  (`started_at`, `finished_at`, `computed_at`, `recorded_at`);
  PUMA's approximation of bi-temporality (§5).
- **CodeCarbon** — sustainability-instrumentation library; tracks
  energy + CO₂ for a run when `sustainability.codecarbon: true`.
- **Determinism** — `seed=42`, `temperature=0.0`, pinned model
  digest → byte-identical `predictions_summary_hash` across re-runs
  ([`security.md`](security.md) §3).
- **F1-macro** — primary triage classification metric (unweighted
  per-class F1 average).
- **gitleaks** — full-history secret scanner; runs in CI via
  `.github/workflows/gitleaks.yml`.
- **Hardware profile** — entry under `profiles.<name>` in
  `config/profiles.yaml`; controls which models the host can run
  and which scenarios are enabled (§3.2).
- **Inference** — Ollama-mediated LLM execution over `httpx`. PUMA
  never reaches a remote inference provider
  ([`security.md`](security.md) §4).
- **Instance** — a single dataset row (input + gold label); stored
  in the `instances` table.
- **MAE** — primary story-point estimation metric (mean absolute
  error in story-point units).
- **Ollama** — the local inference engine PUMA depends on. Not
  bundled in the published image; expected as a local daemon or a
  reachable service in the Compose flow.
- **OCI labels** — Open Container Initiative metadata on the
  published image (`org.opencontainers.image.title`, etc.); set in
  `Dockerfile.publish` and reinforced by `docker/metadata-action@v5`
  in `publish-docker.yml`.
- **Perturbation** — optional input variation applied in layer 3
  for robustness/fairness testing (e.g. gendered-prefix
  substitution).
- **pip-audit** — production-dependency CVE scanner; runs in CI via
  `.github/workflows/pip-audit.yml` against `requirements.txt`.
- **Predictions summary hash** — SHA-256 over the canonical
  (instance_id, prediction) tuple per run; the integrity signature
  shipped with every submission ([`security.md`](security.md) §5).
- **Preflight** — hardware and environment validation stage (§2.1).
- **Profile snapshot** — per-run capture of the host profile
  (`ProfileSnapshot` table, §5.6).
- **PUMA Community** — the federated submission hub at
  `pumacp/puma-community`; entry point for publishing benchmark
  results.
- **Run-spec** — a versioned YAML in `specs/runs/` that fully
  describes an experiment (§3.1).
- **RCOIF** — one of the prompting strategies in the adaptation
  layer.
- **Scenario** — a canonical experiment configuration; the three
  shipped scenarios are `triage_jira`, `effort_tawos`,
  `prioritization_jira`.
- **SDD** — Spec-Driven Development; the YAML-first approach to
  defining experiments.
- **Story point** — estimation-task target value (Fibonacci scale,
  typically 1–13 for the TAWOS corpus).
- **Strategy** — a prompting approach selected per run-spec
  (`zero-shot`, `few-shot-3`, `few-shot-5`, `few-shot-8`, `cot`, `rcoif`,
  `contextual-anchoring`, `egi`, `self-consistency`).
- **Sub-group** — Typer sub-command grouping in the CLI
  (`puma models`, `puma db`, `puma cache`, `puma auth`,
  `puma community`).
- **TAWOS** — the Tawosi Open-Source dataset used as the story-point
  estimation corpus.
- **Triage** — the issue-priority classification scenario
  (`triage_jira`).
- **Trivy** — container-image vulnerability scanner; runs in CI as
  part of `publish-docker.yml` and uploads SARIF to the GitHub
  Security tab.
- **Wilcoxon** — non-parametric signed-rank test for pairwise model
  comparison; surfaced as `puma wilcoxon`.

---

## 10. Architectural decisions timeline

Chronological summary of the key pivots that shaped PUMA's current
state. Each entry: date / sprint anchor, decision, one-sentence
rationale. Use the git log and `docs/known_debt.md` for the
canonical context per decision.

| Sprint / date | Decision | Rationale |
|---|---|---|
| Pre-S1 | Pivot from multi-agent orchestrator to **evaluation benchmark** | Right-sized the project to what could be rigorously evaluated within the available timeline and hardware. |
| S1 | Adopt **Ollama** as the canonical local inference engine | Single local API, no external accounts, GGUF model format, broad model catalogue. |
| S1 | **SQLite + SQLAlchemy ORM** for persistence | Zero-ops storage; bi-temporal-like append-only schema gives auditability without operational burden. |
| S1 | **6-layer architecture** (refactor from earlier 4-layer prototype) | Separated concerns sharply enough that layers could be tested and refactored independently. |
| S4 | **`schema_data/submission.v1.json`** finalised as immutable (P3 constraint) | Submissions need a stable contract for federated verification; immutability is the simplest enforceable invariant. |
| S5 | **PUMA Community** federated submission hub at `pumacp/puma-community` | Separate repo with path-restricted auto-merge keeps the main repo focused on the tool and the community repo focused on results. |
| S7 | **CodeCarbon** opt-in sustainability instrumentation | Local energy + CO₂ measurement without an outbound telemetry hop. |
| S10 | `Apple Silicon` profile family added | Anticipates Apple-hosted contributors; ten variants gated by `sysctl` chip-brand match. |
| Phase E | Public-Pages **sensitive-content separation** | Maintainer-only operational details (private endpoints, token-setup steps) removed from anything that lands on Pages. |
| Phase Z-2 | **Git history sanitization** (`git filter-repo` over the whole tree) | Removed AI-assistant `Co-authored-by:` trailers from every commit and tag; `.githooks/commit-msg` keeps future commits clean. |
| PR #47 | **Acrostic immutability tests relaxed** (`@pytest.mark.skip`) | Visual restructure of the README header into a categorized channel directory required the acrostic to move into a two-column table; the immutability assertion would have blocked the restructure. |
| S12.15 | **PyPI** (`puma-cp`) + **Docker** (`ghcr.io/pumacp/puma`) publishing workflows | Production install channels separate from the development Compose stack; multi-stage `Dockerfile.publish` runs as non-root. |
| S12.16 | **Multi-model dashboard view** | Side-by-side model comparison with delta metrics, bar charts, full table, fingerprint check — reads persisted SQLite only. |
| S12.17 | **D30 RESOLVED** — full mkdocs content sync (nav 6→24 pages) | Held-out pages repaired and re-entered the nav; stale `puma models` CLI references rewritten; `RELEASES/v3.1.0.md` sanitized. |
| S12-N4 | **Manual IDE contribution workflow** formalised | `docs/development-workflow.md` (16 sections, ~860 lines) became the canonical procedural reference; root `CONTRIBUTING.md` now points to it. |
| S12-N2 | **Security audit MVP** | `pip-audit` + `bandit` + `gitleaks` + `Trivy` added; `SECURITY.md` modernised for v4.0.0 readiness; comprehensive threat model in `docs/security.md`. |
| S12-N3 (this PR) | **Consolidated technical reference** | This page — single comprehensive entry point for evaluators, integrators, and future maintainers. |

---

## 11. Strengths

- **Local-first inference** — no outbound API calls during a
  benchmark run; PUMA cannot leak data it never sees.
- **Deterministic reproducibility** — `seed=42`, `temperature=0.0`,
  pinned model digest → byte-identical `predictions_summary_hash`
  across runs.
- **Sustainability instrumentation on every run** when opted-in —
  CO₂ and energy per run, per device.
- **Cryptographic integrity** on every submission — SHA-256 over
  the canonical predictions tuple.
- **Schema immutability** plus JSON Schema validation in the
  submission path → catches drift before publication.
- **Open data + open code** — MIT-licensed package, CC-BY-4.0 on
  submissions.
- **Federated submission hub** (`pumacp/puma-community`) separates
  the tool from its results.
- **Multi-model + multi-hardware support** — 5 standard profiles +
  10 Apple Silicon variants; the catalog grows by editing one YAML.
- **Comprehensive test surface** — `pytest` (`unit/`, `integration/`,
  `community/`), `mypy --strict` on `src/puma/`, `ruff` (check +
  format).
- **Defense in depth on contribution flow** — brand-scanner test,
  Spanish-detection audit, sensitive-content audit,
  `.githooks/commit-msg` trailer-strip, gitleaks full-history scan,
  bandit SAST, pip-audit CVE scan, Trivy on the published image.

---

## 12. Known limitations / debt

Tabular summary; full entries in
[`known_debt.md`](known_debt.md).

| ID | Title | Status |
|---|---|---|
| D3 | Ollama / CUDA determinism flags untuned | OPEN |
| D5 | Reproducibility docs (`HARDWARE.md` cross-references) | OPEN |
| D15 | CodeCarbon GPU detection inside container | OPEN |
| D18 | Gemma 4 family parser incompatibility on `gpu-entry` | OPEN |
| D23 | Server-side hash mis-shape for schema v1.0.0 | OPEN |
| D24 | `profile_required` not declared on canonical specs (`puma share-results` gap) | OPEN |
| D26 | (see `known_debt.md`) | OPEN |
| D27 | Predictions JSONL exporter missing in `share-results` | OPEN |
| D29 | (see `known_debt.md`) | OPEN |
| D31 | Estimation MAE baseline drift (post-runtime-restart) | OPEN |
| D32 | License-compatibility automation (deferred from S12-N2 MVP) | OPEN |
| D33 | SBOM CycloneDX generation (deferred from S12-N2 MVP) | OPEN |
| D34 | Mutation testing on `integrity.py` (deferred from S12-N2 MVP) | OPEN |
| D35 | Cross-platform install test (deferred from S12-N2 MVP) | OPEN |

Resolved items (e.g. D30 — mkdocs content sync, RESOLVED 2026-05-31)
live in the "Resolved technical debt" section of
[`known_debt.md`](known_debt.md).

---

## 13. Risks + mitigations

| Risk | Mitigation |
|---|---|
| Model availability drift (an Ollama tag changes silently). | Ollama manifest digest recorded in `ProfileSnapshot`; `puma validate-baseline` flags metric drift caused by an underlying digest change. |
| Dataset upstream changes (TAWOS / Jira corpus). | Datasets are version-pinned at preparation time; `puma datasets` verifies integrity against the checksum recorded at `prepare-datasets` time. |
| CI infrastructure changes (GitHub Actions ecosystem). | Workflows use pinned action versions where available (`actions/checkout@v4`, `docker/setup-buildx-action@v3`, etc.); a few use `@master` for fast-moving security tooling — see `.github/workflows/`. |
| Adoption friction for new contributors. | [`docs/development-workflow.md`](development-workflow.md) (16-section procedural reference), [`CONTRIBUTING.md`](https://github.com/pumacp/puma/blob/develop/CONTRIBUTING.md) (concise entry point), [`docs/index.md`](index.md) tutorials. |
| Reproducibility regression (a future PR breaks bit-identity). | Baseline sanity oracle (F1 ±0.01 of 0.5894) is checked in every documentation phase; metric-level drift surfaces via `puma validate-baseline`; the bandit / pip-audit gates catch regressions in the dependency tree. |
| Container image CVE post-publish. | `Trivy` scan blocks the publish step on HIGH/CRITICAL findings; SARIF posts to the GitHub Security tab even on success for low-severity surface tracking. |
| Schema drift on submissions. | `schema_data/submission.v1.json` is immutable (P3); JSON Schema validation runs in the `puma community validate` path before any submission can be opened. |

---

## 14. Roadmap pointer

Open work items are tracked in [`known_debt.md`](known_debt.md).
Near-term sprint anchors (post-S12-N3):

- **S12-N1** — first official PUMA Community submission landed
  end-to-end via `puma share-results` from a clean install.
- **S12.18** — `v4.0.0` release ceremony (PyPI publish, GHCR
  publish with the new Trivy gate, `v4.0.0` tag,
  `RELEASES/v4.0.0.md`, post-release sync of `main` from `develop`).
- **S12.19** — sprint closure: backlog grooming, post-sprint
  retrospective, candidate items for the post-Sprint-12 plan
  (D32–D35 + any new findings).
- **Post-Sprint-12** — license-compatibility automation (D32),
  CycloneDX SBOM (D33), mutation testing on `integrity.py` (D34),
  cross-platform install test (D35).

---

## 15. References

Canonical cross-links:

- [`docs/index.md`](index.md) — the landing page.
- [`docs/cli_reference.md`](cli_reference.md) — exhaustive CLI manual.
- [`docs/development-workflow.md`](development-workflow.md) —
  procedural contribution reference.
- [`docs/security.md`](security.md) — threat model and posture.
- [`docs/sustainability.md`](sustainability.md) — sustainability
  methodology.
- [`docs/known_debt.md`](known_debt.md) — canonical debt tracker.
- [`SECURITY.md`](https://github.com/pumacp/puma/blob/develop/SECURITY.md)
  — private vulnerability disclosure policy.
- [`CONTRIBUTING.md`](https://github.com/pumacp/puma/blob/develop/CONTRIBUTING.md)
  — concise contribution entry point.

---

Last reviewed: 2026-05-31 (S12-N3 consolidated technical reference).
