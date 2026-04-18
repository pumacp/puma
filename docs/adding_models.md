# Adding a Model to the Catalog

## 1. Pull the model via Ollama

```bash
ollama pull <model_tag>
# e.g.  ollama pull llama3.2:3b
```

Or via the CLI (inside Docker):

```bash
docker compose run --rm puma_runner puma models pull llama3.2:3b
```

## 2. Register in `config/models_catalog.yaml`

Add an entry under `models:`:

```yaml
- ollama_tag: llama3.2:3b
  params_b: 3
  gguf_size_gb: 2.0
  profiles_compatible:
    - cpu-lite
    - cpu-standard
    - gpu-entry
  context_window: 8192
  languages: [en]
  notes: "Meta Llama 3.2 3B instruct"
```

| Field | Description |
|-------|-------------|
| `ollama_tag` | Exact tag used with `ollama pull` |
| `params_b` | Parameter count in billions |
| `gguf_size_gb` | Approximate disk size |
| `profiles_compatible` | Hardware profiles that can run it (see `config/runtime_profile.yaml`) |
| `context_window` | Maximum context in tokens |
| `languages` | ISO 639-1 codes |

## 3. Create a run-spec

```yaml
id: smoke_llama3_triage
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

## 4. Verify

```bash
puma run specs/runs/smoke_llama3_triage.yaml --dry-run
```

Dry-run exercises the full pipeline without calling Ollama. Remove `--dry-run` for a live run.

## 5. (Optional) Add prompt templates

If the model requires a specific prompt format, add Jinja templates in:

```
specs/prompts/<scenario>/zero_shot.jinja
```

The `{{ title }}`, `{{ description }}`, `{{ examples }}` variables are injected by `Strategy.build_prompt()`.
