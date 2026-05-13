# PUMA — Project Understanding and Management with Agents

![PUMA Logo](https://raw.githubusercontent.com/pumacp/puma/main/assets/img/PUMA.png)

> **PUMA — Project Understanding and Management with Agents**
>
> *Can language models manage ICT projects? An empirical benchmark of local LLM agents for issue triage and effort estimation in ICT projects.*

PUMA is a research-driven platform that benchmarks autonomous AI agents on practical project management tasks. This repository contains the **evaluation platform**: orchestrator, scenarios, metrics, sustainability tracking, dashboard, and reproducible specifications. All inference runs locally via [Ollama](https://ollama.ai) — no external API calls, no data leaves your machine.

![Tests](https://img.shields.io/badge/tests-318%20passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Docker](https://img.shields.io/badge/runs%20on-Docker-2496ED)
![Version](https://img.shields.io/badge/version-v2.3.0-blue)

## Related resources

- 📚 [PUMA Research Vault](https://github.com/pumacp/puma-vault) — Unified knowledge management for the PUMA project
- 🌐 [Vault Published](https://pumacp.github.io/puma-vault/) — Published knowledge garden
- 📦 [Releases](https://github.com/pumacp/puma/releases) — All published versions
- 📋 [Project Index](INDEX.md) — Phase status, releases, debt tracking
- 🏗️ [Project Overview](docs/overview.md) — Architecture, scenarios, model catalog

## Status

| Item | Value |
|------|-------|
| Current release | [v2.3.0](https://github.com/pumacp/puma/releases/tag/v2.3.0) |
| Tests | 318 passing |
| Coverage | 58% |
| CI | ✓ green on main + develop |
| Phases A, B, C, D, E | ✓ All complete |
| Debt | 15 resolved; 7 open (0 critical, 5 medium, 2 low) |

> **PUMA is an independent benchmarking framework, fully self-contained, designed specifically for evaluating local LLMs on Project Management Office (PMO) tasks. All evaluation methodology, scenarios, and metrics are developed and maintained independently as part of this work.**

---

## Requirements

| Requirement | Minimum |
|-------------|---------|
| Docker Engine | 24+ |
| Docker Compose | v2 |
| RAM | 8 GB (16 GB recommended) |
| Disk | 10 GB free (for models + data) |
| GPU | Optional — NVIDIA/AMD/Apple Silicon |

> No Python installation needed on the host. Everything runs inside Docker.

---

## Quickstart

```bash
# Clone and provision (downloads models, datasets, applies DB schema)
git clone <repo-url> && cd puma
./start_puma.sh

# Enable the project's commit-msg hook (strips Co-Authored-By trailers)
git config core.hooksPath .githooks

# Run a benchmark (dry-run — no Ollama needed)
docker compose run --rm puma_runner puma run specs/runs/smoke_triage.yaml --dry-run

# Run a live benchmark (requires Ollama + model)
docker compose run --rm puma_runner puma run specs/runs/smoke_triage.yaml

# Open the dashboard
open http://localhost:8501
```

For host-only pre-commit setup and the cross-container development
workflow, see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). For the
reference hardware specification (RTX 2060 Mobile, 6 GB VRAM) and
reproducibility scope, see [docs/HARDWARE.md](docs/HARDWARE.md).

---

## CLI Reference

All commands run inside the `puma_runner` container:

```bash
docker compose run --rm puma_runner puma <command>
```

Or use the shorthand after `./start_puma.sh`:

```bash
alias puma='docker compose run --rm puma_runner puma'
```

### `puma preflight`

Detect hardware, select an execution profile, and check provisioning readiness.

```bash
puma preflight
puma preflight --profile cpu-standard     # override auto-detection
puma preflight --no-write-config          # skip writing config/runtime_profile.yaml
```

Profiles: `cpu-lite`, `cpu-standard`, `gpu-entry`, `gpu-mid`, `gpu-high`, `auto`.

---

### `puma models`

List or pull models from the catalog.

```bash
puma models list                   # show all catalog models with size and compatible profiles
puma models pull qwen2.5:3b        # pull a specific model via Ollama
```

---

### `puma datasets`

Verify dataset integrity and show statistics.

```bash
puma datasets verify               # check checksums and row counts for all datasets
```

---

### `puma run`

Execute a benchmark defined by a run-spec YAML.

```bash
puma run specs/runs/smoke_triage.yaml
puma run specs/runs/smoke_triage.yaml --dry-run          # skip Ollama, test pipeline
puma run specs/runs/smoke_triage.yaml --ollama-host http://puma_ollama:11434
puma run specs/runs/smoke_triage.yaml --db data/puma.db
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | false | Build prompts and persist results without calling Ollama |
| `--ollama-host` | `http://localhost:11434` | Ollama API base URL (env: `OLLAMA_HOST`) |
| `--db` | `data/puma.db` | SQLite database path |

---

### `puma compare`

Compare metrics across two or more runs.

```bash
puma compare run_id_1 run_id_2
puma compare run_id_1 run_id_2 --output comparison.json
puma compare run_id_1 run_id_2 run_id_3
```

Outputs a Markdown table and, for exactly two runs, shows `run2 − run1` differences per metric.

---

### `puma report`

Generate a Markdown report for a completed run.

```bash
puma report <run_id>
puma report <run_id> --format pdf          # convert via Pandoc (if installed)
puma report <run_id> --db data/puma.db
```

The report is written to `results/<run_id>/report.md` and includes: executive summary, metrics table, per-model breakdown, perturbation analysis, sustainability section, and latency percentiles.

---

### `puma dashboard`

Launch the interactive Streamlit dashboard.

```bash
puma dashboard
puma dashboard --port 8502
```

The dashboard is also available as a persistent Docker service:

```bash
docker compose up -d puma_dashboard
open http://localhost:8501
```

---

### `puma db`

Manage the SQLite database schema.

```bash
puma db migrate               # create or update tables
puma db status                # show database file size
```

---

### `puma cache`

Manage the inference response cache.

```bash
puma cache stats              # show entry count and cache size
puma cache clear              # delete all cached responses
```

---

### `puma validate-baseline`

Reproducibility guard for CI: runs the canonical baseline spec and
exits 0 only if F1-macro is within tolerance of the expected value.

```bash
puma validate-baseline                                        # uses defaults
puma validate-baseline --expected-f1 0.5867 --tolerance 0.01
puma validate-baseline --spec specs/runs/baseline_triage.yaml
```

Defaults: `--spec specs/runs/baseline_triage.yaml`,
`--expected-f1 0.5867`, `--tolerance 0.01`. Exit code is non-zero on
drift; useful as a release gate before tagging.

---

## Run-Spec Format

Every benchmark is fully described by a YAML run-spec. Example:

```yaml
id: my_benchmark_v1
description: "Triage with few-shot and typo perturbations"
scenario: triage_jira           # triage_jira | estimation_tawos | prioritization_jira
sample_size: 50
models:
  - qwen2.5:3b
  - qwen2.5:1.5b
adaptation:
  strategy:
    - zero-shot
    - few-shot-3
inference:
  temperature: 0.0
  seed: 42
  max_tokens: 256
  logprobs: false
perturbations:
  - typos_5pct                  # also: case_upper, case_lower, truncate_50pct, tech_noise
metrics:
  - f1_macro
sustainability:
  codecarbon: false
repeat: 1
```

Run it:

```bash
puma run my_benchmark_v1.yaml --dry-run    # validate pipeline
puma run my_benchmark_v1.yaml              # live run
```

---

## Scenarios

| Scenario | Task | Dataset | Primary Metric |
|----------|------|---------|----------------|
| `triage_jira` | Assign priority (Critical/Major/Minor/Trivial) to a Jira issue | Jira balanced (200 issues) | F1 macro |
| `estimation_tawos` | Estimate story points (Fibonacci) for a user story | TAWOS (9 020 items) | MAE |
| `prioritization_jira` | Given two issues A/B, which has higher priority? | Jira pairwise | Accuracy |

---

## Models

The catalog (`config/models_catalog.yaml`) is the single source of
truth for `(model → hardware profile)` compatibility. `puma models
list` prints the live catalog; the table below summarises the v2.1.0
state.

| Model | Params (B) | GGUF (GB) | Compatible profiles | Notes |
|-------|-----------:|----------:|---------------------|-------|
| `qwen2.5:0.5b` | 0.5 | 0.4 | cpu-lite, cpu-standard, gpu-entry, gpu-mid, gpu-high | |
| `qwen2.5:1.5b` | 1.5 | 1.0 | cpu-standard, gpu-entry, gpu-mid, gpu-high | |
| `qwen2.5:3b` | 3.0 | 1.9 | gpu-entry, gpu-mid, gpu-high | **canonical baseline model** |
| `qwen2.5:7b` | 7.0 | 4.7 | cpu-lite, cpu-standard, gpu-entry, gpu-mid, gpu-high | |
| `qwen2.5:14b` | 14.0 | 9.0 | gpu-mid, gpu-high | |
| `gemma3:1b` | 1.0 | 0.8 | cpu-standard, gpu-entry, gpu-mid, gpu-high | |
| `gemma3:4b` | 4.0 | 3.3 | gpu-entry, gpu-mid, gpu-high | |
| `gemma3:12b` | 12.0 | 8.1 | gpu-high | `timeout_s=1800` (B.3 evidence) |
| `gemma4:e2b` | 2.0 effective / 7.2 full | 7.2 | cpu-standard, gpu-mid, gpu-high | MoE; **excluded from gpu-entry (D18)**: Ollama detokenizer breaks under CPU offload on structured prompts |
| `gemma4:e4b` | 4.0 effective | 4.0 (est.) | gpu-mid, gpu-high | MoE; gpu-entry exclusion by analogy with e2b |
| `gemma4:26b-a4b` | 26.0 total / 4.0 active | 16.0 (est.) | gpu-high | MoE |
| `llama3.1:8b` | 8.0 | 4.9 | gpu-entry, gpu-mid, gpu-high | |
| `mistral:7b` | 7.0 | 4.4 | gpu-entry, gpu-mid, gpu-high | |
| `deepseek-r1:7b` | 7.0 | 4.7 | gpu-entry, gpu-mid, gpu-high | reasoning model (`<think>` blocks); `timeout_s=300` |
| `deepseek-r1:14b` | 14.0 | 9.0 | gpu-mid, gpu-high | reasoning model |

Profile detection runs automatically via `puma preflight`. Override
with `--profile <name>`.

---

## Baseline & Results

**Canonical baseline:** `qwen2.5:3b` + `contextual-anchoring` + `seed=42`
+ `temperature=0.0` on `triage_jira` with 200 instances yields
**F1-macro = 0.5867 ± 0.01** on the reference hardware. Reproducible
end-to-end via `puma validate-baseline`. The spec lives at
`specs/runs/baseline_triage.yaml`; the tolerance is verified in CI.

**Multi-model evaluation:** 9 models compatible with `gpu-entry`
evaluated across the 3 PMO scenarios at N=100 instances per cell
(2,700 inferences; ~67.5 Wh / 11.75 g CO₂ total compute budget). Best
performers vary by task; small models (1B–3B) are competitive with
larger ones on several PMO scenarios. Full comparative analysis,
per-scenario tables, sustainability efficiency, and the
"60.5 % wasted compute" finding (gemma4 family on `gpu-entry`,
resolved as debt D18) in
[docs/results/phase_b_analysis.md](docs/results/phase_b_analysis.md).
Plots are reproducible via `scripts/generate_phase_b_plots.py`.

**Statistical analysis (v2.2.0):** calibration via Expected Calibration
Error (Guo et al. 2017) — the canonical baseline shows ECE=0.39 against
its 200 logprob-enabled predictions, surfacing significant
miscalibration typical of out-of-the-box LLMs. Pairwise model
comparison via the Wilcoxon signed-rank test (Demšar 2006); see
[docs/results/wilcoxon_demo.md](docs/results/wilcoxon_demo.md). Three
seeds {42, 123, 456} confirm bit-exact reproducibility under
temperature=0.0
([docs/results/multi_seed_baseline.md](docs/results/multi_seed_baseline.md)).

**Bias evaluation (v2.2.0):** the `triage_jira` corpus contains 0 %
gendered terms, so a textbook gender_swap would be a no-op. Sprint 5
adopts the **signal-injection** methodology of Caliskan et al. (2017)
and Bolukbasi et al. (2016): identity prefixes (`John Smith reported:`
vs `Mary Smith reported:`) are prepended to instances and the
prediction flips counted. qwen2.5:3b exhibits ~3× less directional
gender bias than qwen2.5:1.5b at the same prediction-flip rate; both
models are robust to register variation (`register_shift_informal`).
Full report in
[docs/results/bias_evaluation.md](docs/results/bias_evaluation.md).

---

## Prompting Strategies

| Strategy | Key | Description |
|----------|-----|-------------|
| Zero-shot | `zero-shot` | Direct question, no examples |
| Zero-shot CoT | `zero-shot-cot` | Ask model to think step-by-step |
| One-shot | `one-shot` | Single example |
| Few-shot (k=3) | `few-shot-3` | Three stratified examples |
| Few-shot (k=5) | `few-shot-5` | Five stratified examples |
| Few-shot (k=8) | `few-shot-8` | Eight stratified examples |
| Chain-of-Thought few-shot | `cot-few-shot` | Few-shot with CoT rationales |
| RCOIF | `rcoif` | Role + Context + Output + Instruction + Format |
| Contextual Anchoring | `contextual-anchoring` | Grounds prediction to project context |
| Self-Consistency | `self-consistency` | Multiple samples + majority vote (requires temperature > 0) |
| EGI | `egi` | Example-Guided Inference |

---

## Dashboard Views

Open `http://localhost:8501` after `docker compose up -d puma_dashboard`.
PUMA-themed sidebar with logo and a runtime dark-mode toggle.

| View | Description |
|------|-------------|
| **Overview** | Cohort cards (total runs, total CO₂, kWh, avg ECE, avg F1, avg latency.p95) plus per-run expanders with model / F1 / ECE / CO₂ / parse-fail. Sidebar filters applied. |
| **Model Comparison** | Mean±std aggregation over seeds, run × metric heatmap, and inline Wilcoxon signed-rank results when `docs/results/wilcoxon_demo.md` is present. |
| **Reliability** | Per-model ECE and reliability diagram computed from real logprob-derived confidences (Guo et al. 2017). Falls back to a message when no logprob runs exist. |
| **Robustness** | Disparity / flip-rate table and bar chart for every perturbation in the cohort. |
| **Fairness** | Gender-prefix injection bias (Caliskan et al. 2017) — disparity vs baseline plus directional male-vs-female comparison. |
| **Sustainability Frontier** | Pareto scatter: F1 vs CO₂ (g) using the `emissions` table populated by CodeCarbon (Sprint 2 D15). |
| **Instance Drill-down** | Per-prediction inspection: gold/parsed labels, outcome filter (correct / incorrect / parse failure), confidence, top-K logprobs, raw response, prompt hash. |

---

## Development

```bash
make build    # build the puma_runner Docker image
make lint     # ruff check + format check (src/puma/ and tests/)
make test     # run unit + integration tests inside Docker
make smoke    # smoke tests (AppTest, no Ollama required)
```

All dev tooling runs inside the container. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Roadmap

Trabajo identificado para releases posteriores a v2.3.0:

- **Cross-strategy comparison at scale** — pairwise comparisons
  across `zero-shot`, `few-shot-{3,5,8}`, and CoT variants on the
  same model cohort, with the new Wilcoxon driver applied.
- **Hardware tier extension** — re-run the B.3 sweep on `gpu-mid` to
  empirically validate `gemma3:12b`, the `gemma4` family, and 14B
  reasoning models with adequate VRAM (resolves D16 verification).
- **TAWOS SHA-256 end-to-end** — checksum-verified fetch path for the
  upstream TAWOS dump (D14) and the bash regeneration test (Gate D
  criterion 3).
- **Multi-backend GPU detection** — AMD ROCm and Apple Metal
  detection alongside the existing NVIDIA path in
  `puma.preflight.detect`.
- **`triage_jira` ticket-text persistence (D22)** — populate
  `instances.input_text` so the Dashboard Instance Drill-down can
  show the original ticket description rather than the empty-text
  placeholder.

Closed in v2.3.0 (no longer in roadmap):

- ✓ Phase C polish (Sprint 6 → `app.py` 803→168 LOC refactor +
  10 polish improvements + guided tour, all five Gate-C criteria met)

Closed in v2.2.0:

- ✓ ECE / calibration metrics completion (Sprint 3 → Reliability view)
- ✓ Multi-seed validation (Sprint 3 → bit-exact under T=0.0)
- ✓ Bias perturbation suite (Sprint 5 → `gender_swap_prefix`,
  `register_shift`, `fairness.perturbation_disparity`)
- ✓ Phase C — Dashboard core (Sprint 4 → 5 functional views)

Detailed debt inventory in
[docs/known_debt.md](docs/known_debt.md).

---

## Documentation

| Document | Contents |
|----------|---------|
| [docs/architecture.md](docs/architecture.md) | Data flow, package map, Docker services, design decisions |
| [docs/user_guide.md](docs/user_guide.md) | Step-by-step guide: provision → run → compare → report → dashboard |
| [docs/metrics_reference.md](docs/metrics_reference.md) | Formula for every metric (classification, regression, calibration, efficiency) |
| [docs/scenarios_reference.md](docs/scenarios_reference.md) | Scenario specs, parse logic, gold label definition |
| [docs/adding_models.md](docs/adding_models.md) | How to add a model to the catalog |
| [docs/adding_scenarios.md](docs/adding_scenarios.md) | How to implement a new benchmark scenario |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common problems and fixes |
| [docs/HARDWARE.md](docs/HARDWARE.md) | Reference hardware spec, profile detection, thermal/VRAM observations, CodeCarbon accuracy, reproducibility scope |
| [docs/results/phase_b_analysis.md](docs/results/phase_b_analysis.md) | Comparative analysis of the 9 models × 3 PMO scenarios sweep |
| [docs/results/multi_seed_baseline.md](docs/results/multi_seed_baseline.md) | Bit-exact reproducibility across seeds {42, 123, 456} (Sprint 3) |
| [docs/results/wilcoxon_demo.md](docs/results/wilcoxon_demo.md) | Wilcoxon signed-rank pairwise comparison empirical demo (Sprint 3) |
| [docs/results/bias_evaluation.md](docs/results/bias_evaluation.md) | Bias evaluation empirical findings (Sprint 5) |
| [docs/known_debt.md](docs/known_debt.md) | Open and resolved technical debt with diagnostic write-ups |
| [docs/RELEASES/v2.3.0.md](docs/RELEASES/v2.3.0.md) | v2.3.0 release notes |
| [docs/RELEASES/v2.2.0.md](docs/RELEASES/v2.2.0.md) | v2.2.0 release notes |
| [docs/RELEASES/v2.1.0.md](docs/RELEASES/v2.1.0.md) | v2.1.0 release notes |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Code conventions, commit format, PR process |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Host-only pre-commit setup, hooks |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
