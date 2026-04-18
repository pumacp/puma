# Adding a Model to the Catalog

This guide explains how to register a new Ollama-compatible model in PUMA so it can be selected in run-specs and listed by `puma models list`.

---

## Overview

Adding a model requires three steps:

1. Pull the model via Ollama so it is available for inference
2. Register it in `config/models_catalog.yaml`
3. Validate with a dry-run benchmark

---

## Step 1 — Pull the model

Pull inside the `puma_ollama` container (preferred — model goes into the shared volume):

```bash
docker compose run --rm puma_runner puma models pull llama3.2:3b
```

Or directly from the host if Ollama is installed:

```bash
ollama pull llama3.2:3b
```

Check it is available:

```bash
docker compose exec puma_ollama ollama list
```

---

## Step 2 — Register in `config/models_catalog.yaml`

Open `config/models_catalog.yaml` and add an entry under the `models:` key:

```yaml
models:
  # ... existing entries ...

  - ollama_tag: llama3.2:3b
    params_b: 3
    gguf_size_gb: 2.0
    profiles_compatible:
      - cpu-standard
      - gpu-entry
      - gpu-mid
    context_window: 128000
    languages: [en]
    notes: "Meta Llama 3.2 3B instruct — fast, small context window"
```

### Field reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ollama_tag` | string | yes | Exact tag for `ollama pull` (must match exactly) |
| `params_b` | float | yes | Parameter count in billions (e.g. `3` for 3B) |
| `gguf_size_gb` | float | yes | Approximate disk size of the GGUF file |
| `profiles_compatible` | list[str] | yes | Hardware profiles that can run this model without OOM |
| `context_window` | int | yes | Maximum context length in tokens |
| `languages` | list[str] | no | ISO 639-1 language codes the model supports well |
| `notes` | string | no | Free-text description shown in `puma models list` |

### Profile compatibility guidelines

| Profile | Max model size |
|---------|---------------|
| `cpu-lite` | ≤ 1.5B params / ≤ 1.0 GB |
| `cpu-standard` | ≤ 7B params / ≤ 5.0 GB |
| `gpu-entry` | ≤ 7B params / ≤ 5.0 GB VRAM |
| `gpu-mid` | ≤ 14B params / ≤ 10.0 GB VRAM |
| `gpu-high` | ≤ 32B+ params / ≤ 24.0 GB VRAM |

---

## Step 3 — Create a smoke run-spec

Create a file in `specs/runs/` to test the new model:

```yaml
id: smoke_llama3_triage
description: "Smoke run: llama3.2:3b × triage_jira × zero-shot"
scenario: triage_jira
sample_size: 10
models:
  - llama3.2:3b
adaptation:
  strategy: [zero-shot]
inference:
  temperature: 0.0
  seed: 42
metrics: [f1_macro]
```

---

## Step 4 — Validate

Run in dry-run mode first (no Ollama call, validates the full pipeline):

```bash
puma run specs/runs/smoke_llama3_triage.yaml --dry-run
```

Expected output:
```
Run complete: smoke_llama3_triage__<hash>__<ts>
Predictions: 10
  parse_failure_rate: 1.0000    ← expected in dry-run (response is "[dry-run]")
```

Then run live:

```bash
puma run specs/runs/smoke_llama3_triage.yaml
```

---

## Step 5 — (Optional) Add custom prompt templates

PUMA's default templates work with most instruction-tuned models. If the new model requires a specific chat format (e.g. `[INST]...[/INST]` for Mistral, `<|user|>...<|assistant|>` for Phi), create a model-specific template file:

```
specs/prompts/triage_jira/zero_shot.jinja       ← default (used by all models)
```

Available Jinja2 template variables:

| Variable | Description |
|----------|-------------|
| `{{ title }}` | Issue title |
| `{{ description }}` | Issue description / body |
| `{{ examples }}` | List of few-shot example dicts (empty for zero-shot) |
| `{{ labels }}` | List of valid output labels |

Model-specific template dispatch is not yet implemented (all models share templates). To specialise, create a separate strategy or fork the template file.

---

## Step 6 — Compare with existing models

After running the smoke benchmark, compare results against a baseline:

```bash
puma compare smoke_qwen25_3b__<hash>__<ts> smoke_llama3_triage__<hash>__<ts>
```

Or open the dashboard to see the heatmap:

```bash
open http://localhost:8501
```
