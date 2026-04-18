# PUMA

**Platform for Understanding & Management with Agents** — local, reproducible benchmarking of open LLMs on project management tasks (triage, estimation, prioritization).

Full documentation: [index.md](index.md)

## Quickstart

```bash
# 1. Start PUMA (detects hardware, provisions Ollama, downloads models)
./start_puma.sh

# 2. Run a benchmark
puma run specs/runs/smoke_triage.yaml

# 3. Open the dashboard
puma dashboard   # http://localhost:8501
```

Runs entirely locally. No external API calls during inference. See [index.md](index.md) for architecture, scenarios, metrics, and model catalog.
